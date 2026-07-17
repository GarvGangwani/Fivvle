"""Evidence chat service — founder Q&A over a completed validation report.

Independent of chat_service.py by design (per PR 3 scope): evidence chat is a
flat thread (no branching, no tree helpers). Messages carry
``turn_kind=EVIDENCE_CHAT`` and ``parent_message_id=None``. History is a plain
linear query, never mixed with refinement/discussion turns.

Flow (send):
  1. Load + ownership-check the experiment and its ValidationReport (404 on miss).
  2. Resolve or create the evidence thread (create-on-first-message).
  3. Load prior evidence-chat history (this thread, EVIDENCE_CHAT only).
  4. Build the LLM context: report skeleton + selected context (selection or
     keyword-matched findings) + truncated history.
  5. Persist the user message, call the LLM, persist the assistant message.

Per AGENTS.md: report/history content is untrusted data — it is wrapped in
tagged sections in the prompt (see app/llm/prompts/evidence_chat.py) and never
drives side effects. LLMCall cost logging happens inside llm_client.complete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.llm.prompts.evidence_chat import (
    EVIDENCE_CHAT_SYSTEM_PROMPT,
    PROMPT_NAME_EVIDENCE_CHAT,
    build_evidence_chat_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import (
    Finding,
    ValidationReport as ValidationReportSchema,
)

_logger = get_logger(__name__)

# Plain-text reply, mirrors chat_service._PLAIN_CHAT_MAX_TOKENS.
_MAX_TOKENS = 1024
_TEMPERATURE = 0.7

# Keyword-match config.
_CONTEXT_TOP_K = 3
_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}

# ~3k-token proxy. Drop oldest full user+assistant pairs until under budget.
_HISTORY_CHAR_BUDGET = 12000

# Small hardcoded stopword set — no dependency (per PR 3 constraints).
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
        "from", "as", "that", "this", "these", "those", "it", "its", "if",
        "than", "then", "my", "our", "we", "i", "you",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class EvidenceChatNotFound(Exception):
    """Experiment not found / not owned, or its validation report is missing.

    Mapped to HTTP 404 by the router — never reveal existence for another user
    (AGENTS.md "Authentication and authorization").
    """


@dataclass(frozen=True)
class EvidenceChatResult:
    user_message: ChatMessage
    assistant_message: ChatMessage
    thread_id: UUID


def _sanitize(text: str) -> str:
    """Strip NUL bytes (Postgres text columns reject them) and surrounding space."""
    return text.replace("\x00", "").strip()


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def _project_name(experiment: Experiment) -> str:
    raw = experiment.refined_idea_current or experiment.refined_idea
    if isinstance(raw, dict):
        pn = raw.get("project_name")
        if isinstance(pn, str) and pn.strip():
            return pn.strip()
    if experiment.name and experiment.name.strip():
        return experiment.name.strip()
    return "Untitled"


def _compress_refined_idea(experiment: Experiment) -> str:
    """~200-token rendering of the refined idea for the skeleton, or "" if absent."""
    raw = experiment.refined_idea_current or experiment.refined_idea
    if not raw:
        return ""
    try:
        idea = RefinedIdea.model_validate(raw)
    except ValidationError:
        return ""
    lines = [
        f"Product: {idea.refined_one_liner}",
        f"Audience: {idea.target_audience}",
        f"Value: {idea.value_proposition}",
    ]
    if idea.risks:
        lines.append("Top risks:")
        lines.extend(f"- {risk}" for risk in idea.risks[:3])
    return "\n".join(lines)


def _render_finding(question_id: str, finding: Finding) -> str:
    return (
        f"[{question_id}] confidence={finding.confidence}\n"
        f"Claim: {finding.claim}\n"
        f"Evidence: {finding.evidence_summary}"
    )


def _build_report_skeleton(
    experiment: Experiment, report: ValidationReportSchema
) -> str:
    lines: list[str] = []
    idea = _compress_refined_idea(experiment)
    if idea:
        lines.append(idea)
        lines.append("")

    lines.append(f"Overall recommendation: {report.overall_recommendation}")
    lines.append(f"Overall score: {report.overall_score}/100")
    lines.append("")

    lines.append("Section scores:")
    # Preserve stored order — do NOT sort.
    for section in report.section_scores:
        lines.append(f"- {section.label}: {section.score}/100")
    lines.append("")

    lines.append("Research questions:")
    for qf in report.questions_and_findings:
        lines.append(f"- {qf.question_id}: {qf.question}")
    lines.append("")

    lines.append("Research limitations:")
    lines.append(report.research_limitations)
    return "\n".join(lines)


def _keyword_match_findings(
    report: ValidationReportSchema, message: str
) -> list[tuple[str, Finding]]:
    """Top-K findings by non-stopword token overlap with ``message``.

    Ties: higher confidence wins (high > medium > low), then earlier
    question_id alphabetically, then stored order — fully deterministic.
    """
    message_tokens = set(_tokenize(message))
    scored: list[tuple[int, int, str, int, Finding]] = []
    idx = 0
    for qf in report.questions_and_findings:
        for finding in qf.findings:
            finding_tokens = set(
                _tokenize(f"{finding.claim} {finding.evidence_summary}")
            )
            overlap = len(message_tokens & finding_tokens)
            if overlap > 0:
                scored.append(
                    (
                        overlap,
                        _CONFIDENCE_RANK.get(finding.confidence, 0),
                        qf.question_id,
                        idx,
                        finding,
                    )
                )
            idx += 1

    scored.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))
    return [(question_id, finding) for _, _, question_id, _, finding in scored[:_CONTEXT_TOP_K]]


def _build_selected_context(
    report: ValidationReportSchema,
    message: str,
    selection_text: str | None,
    selection_question_id: str | None,
) -> str:
    if selection_text and selection_text.strip():
        parts = [f"<selection>\n{selection_text.strip()}\n</selection>"]
        if selection_question_id:
            qf = next(
                (
                    q
                    for q in report.questions_and_findings
                    if q.question_id == selection_question_id
                ),
                None,
            )
            if qf is not None:
                parts.append(f"Enclosing question {qf.question_id}: {qf.question}")
                if qf.evidence_gap:
                    parts.append(f"Evidence gap: {qf.evidence_gap}")
                parts.extend(_render_finding(qf.question_id, f) for f in qf.findings)
        return "\n\n".join(parts)

    matches = _keyword_match_findings(report, message)
    if not matches:
        return ""
    return "\n\n".join(_render_finding(qid, finding) for qid, finding in matches)


def _render_history(messages: list[ChatMessage]) -> str:
    """Render prior evidence-chat turns, keeping newest full pairs under budget."""
    pairs: list[tuple[ChatMessage, ChatMessage | None]] = []
    i = 0
    while i < len(messages):
        current = messages[i]
        if (
            current.role == ChatRole.USER
            and i + 1 < len(messages)
            and messages[i + 1].role == ChatRole.ASSISTANT
        ):
            pairs.append((current, messages[i + 1]))
            i += 2
        else:
            pairs.append((current, None))
            i += 1

    blocks: list[str] = []
    for user_msg, assistant_msg in pairs:
        block = f"Founder: {user_msg.content}"
        if assistant_msg is not None:
            block += f"\nAssistant: {assistant_msg.content}"
        blocks.append(block)

    kept: list[str] = []
    total = 0
    for block in reversed(blocks):
        addition = len(block) + (2 if kept else 0)
        if kept and total + addition > _HISTORY_CHAR_BUDGET:
            break
        total += addition
        kept.append(block)
    kept.reverse()
    return "\n\n".join(kept)


async def _load_owned_experiment_and_report(
    db: AsyncSession, user: User, experiment_id: UUID
) -> tuple[Experiment, ValidationReport]:
    """Load experiment + report after verifying ownership (404 semantics).

    Mirrors experiments router._load_owned_validation_report but also returns
    the experiment (needed for the skeleton + thread link). Ownership failure
    is indistinguishable from a missing experiment (never leak existence).
    """
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user.id:
        raise EvidenceChatNotFound("Experiment not found")

    report_result = await db.execute(
        select(ValidationReport).where(
            ValidationReport.experiment_id == experiment_id
        )
    )
    report = report_result.scalar_one_or_none()
    if report is None:
        raise EvidenceChatNotFound("Validation report not found")
    return experiment, report


async def _load_evidence_history(
    db: AsyncSession, thread_id: UUID
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.thread_id == thread_id,
            ChatMessage.turn_kind == ChatTurnKind.EVIDENCE_CHAT,
        )
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


async def _resolve_evidence_thread(
    db: AsyncSession, user: User, experiment: Experiment
) -> ChatThread:
    if experiment.evidence_thread_id is not None:
        result = await db.execute(
            select(ChatThread).where(ChatThread.id == experiment.evidence_thread_id)
        )
        thread = result.scalar_one_or_none()
        if thread is not None and thread.user_id == user.id:
            return thread

    thread = ChatThread(
        user_id=user.id,
        title=f"Evidence chat: {_project_name(experiment)}",
    )
    db.add(thread)
    await db.flush()
    experiment.evidence_thread_id = thread.id
    await db.flush()
    return thread


async def send_evidence_chat_message(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
    selection_text: str | None = None,
    selection_question_id: str | None = None,
) -> EvidenceChatResult:
    """Send one evidence-chat turn and return the persisted user + assistant rows.

    Raises:
        EvidenceChatNotFound: experiment not found/owned, or report missing.
        ValueError: message empty after sanitization.
        LLM provider errors from llm_client.complete propagate to the caller
        (mapped to 502 by the router); the uncommitted turn rolls back.
    """
    clean_message = _sanitize(message)
    if not clean_message:
        raise ValueError("message must not be empty")

    experiment, report_row = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    report = ValidationReportSchema.model_validate(report_row.raw_report)

    thread = await _resolve_evidence_thread(db, current_user, experiment)
    history = await _load_evidence_history(db, thread.id)

    skeleton = _build_report_skeleton(experiment, report)
    selected_context = _build_selected_context(
        report, clean_message, selection_text, selection_question_id
    )
    history_str = _render_history(history)

    user_prompt = build_evidence_chat_user_prompt(
        report_skeleton=skeleton,
        selected_context=selected_context,
        chat_history=history_str,
        user_message=clean_message,
    )

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=clean_message,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=None,
    )
    db.add(user_msg)
    await db.flush()

    settings = get_settings()
    result = await llm_client.complete(
        db,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
        prompt_name=PROMPT_NAME_EVIDENCE_CHAT,
        system=EVIDENCE_CHAT_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        experiment_id=experiment.id,
        phase="evidence_chat",
    )
    assistant_text = result.text.strip() or (
        "I couldn't generate a response for that. Please try rephrasing your question."
    )

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=None,
    )
    db.add(assistant_msg)
    await db.flush()
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    _logger.info(
        "evidence chat turn completed",
        experiment_id=str(experiment.id),
        thread_id=str(thread.id),
        used_selection=bool(selection_text and selection_text.strip()),
        history_turns=len(history),
    )

    return EvidenceChatResult(
        user_message=user_msg,
        assistant_message=assistant_msg,
        thread_id=thread.id,
    )


async def list_evidence_chat_messages(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
) -> tuple[UUID | None, list[ChatMessage]]:
    """Return (thread_id, messages) for the evidence thread; ([]/None) if none yet.

    Raises:
        EvidenceChatNotFound: experiment not found / not owned.
    """
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise EvidenceChatNotFound("Experiment not found")

    if experiment.evidence_thread_id is None:
        return None, []

    messages = await _load_evidence_history(db, experiment.evidence_thread_id)
    return experiment.evidence_thread_id, messages
