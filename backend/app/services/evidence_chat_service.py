"""Evidence chat service — founder Q&A over a completed validation report.

Independent of chat_service.py by design, but as of PR 6 evidence chat is
tree-shaped and reuses the shared branching helpers in ``chat_tree_service``.
Messages carry ``turn_kind=EVIDENCE_CHAT`` and a real ``parent_message_id``;
the evidence thread's ``active_leaf_message_id`` tracks the active branch.

Branching model (mirrors refine chat, on a SEPARATE ChatThread row so the two
never collide):
  - first user message in a thread: ``parent_message_id = None``
  - assistant reply: ``parent_message_id = <user message id>``
  - follow-up user message: ``parent_message_id = <active leaf at send time>``
  - edit: new user message is a SIBLING of the edited one
  - regenerate: new assistant message is a SIBLING of the target assistant

Streaming (send/stream endpoint):
  - the HTTP handler persists the user message on the request session and
    commits BEFORE the SSE generator starts (so a mid-stream disconnect never
    loses the user's message);
  - the generator opens its OWN session via ``get_sessionmaker`` and owns the
    assistant persist + active-leaf update + LLMCall accounting for every
    terminal path (success / error / client-disconnect).

Per AGENTS.md: report/history content is untrusted data — it is wrapped in
tagged sections in the prompt (see app/llm/prompts/evidence_chat.py) and never
drives side effects. LLMCall cost logging happens inside llm_client.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import AsyncGenerator
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
from app.db.models.evidence_chat_feedback import EvidenceChatFeedback
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.db.session import get_sessionmaker
from app.llm.prompts.evidence_chat import (
    EVIDENCE_CHAT_SYSTEM_PROMPT,
    PROMPT_NAME_EVIDENCE_CHAT,
    build_evidence_chat_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import (
    Finding,
)
from app.schemas.validation_report import (
    ValidationReport as ValidationReportSchema,
)
from app.services.chat_tree_service import (
    get_active_branch,
    get_branch_up_to,
    get_leaf_of_branch,
    get_siblings,
    set_active_leaf,
)

_logger = get_logger(__name__)

# Plain-text reply, mirrors chat_service._PLAIN_CHAT_MAX_TOKENS.
_MAX_TOKENS = 1024
_TEMPERATURE = 0.7

_FALLBACK_TEXT = (
    "I couldn't generate a response for that. Please try rephrasing your question."
)

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


class EvidenceChatInvalidTarget(Exception):
    """Target message is not a valid evidence-chat target for this action.

    Mapped to HTTP 400 by the router: wrong role, wrong turn_kind, wrong thread,
    or (for regenerate) no parent user message to re-answer.
    """


@dataclass(frozen=True)
class EvidenceChatResult:
    user_message: ChatMessage
    assistant_message: ChatMessage
    thread_id: UUID


@dataclass(frozen=True)
class EvidenceChatEditResult:
    new_user_message: ChatMessage
    new_assistant_message: ChatMessage
    thread_id: UUID
    active_leaf_message_id: UUID
    sibling_info: dict[str, dict]


@dataclass(frozen=True)
class EvidenceActivateResult:
    thread_id: UUID
    active_leaf_message_id: UUID


@dataclass(frozen=True)
class EvidenceBranchMessages:
    thread_id: UUID | None
    active_leaf_message_id: UUID | None
    messages: list[ChatMessage]
    sibling_info: dict[str, dict]


@dataclass
class EvidenceStreamPrep:
    """Everything the SSE generator needs after the handler persists the user row."""

    experiment_id: UUID
    thread_id: UUID
    user_message_id: UUID
    user_prompt: str
    provider: str
    model: str


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
    # Legacy reports predate the scoring engine (overall_score=None,
    # section_scores=[]). Omit both entirely rather than emit "None/100" or an
    # empty header — same spirit as the distribution/regulatory/voices omissions.
    if report.overall_score is not None:
        lines.append(f"Overall score: {report.overall_score}/100")
    lines.append("")

    if report.section_scores:
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


def _build_user_prompt(
    experiment: Experiment,
    report: ValidationReportSchema,
    question_text: str,
    selection_text: str | None,
    selection_question_id: str | None,
    history_messages: list[ChatMessage],
    *,
    sources_block: str | None = None,
) -> str:
    skeleton = _build_report_skeleton(experiment, report)
    selected_context = _build_selected_context(
        report, question_text, selection_text, selection_question_id
    )
    history_str = _render_history(history_messages)
    return build_evidence_chat_user_prompt(
        report_skeleton=skeleton,
        selected_context=selected_context,
        chat_history=history_str,
        user_message=question_text,
        sources_block=sources_block,
    )


async def _load_owned_experiment_and_report(
    db: AsyncSession, user: User, experiment_id: UUID
) -> tuple[Experiment, ValidationReport]:
    """Load experiment + report after verifying ownership (404 semantics).

    Ownership failure is indistinguishable from a missing experiment (never leak
    existence).
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


async def _load_thread_message(
    db: AsyncSession, thread_id: UUID, message_id: UUID
) -> ChatMessage | None:
    """Load a message and confirm it belongs to the given thread (else None)."""
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one_or_none()
    if message is None or message.thread_id != thread_id:
        return None
    return message


async def _resolve_parent_message_id(
    db: AsyncSession,
    thread: ChatThread,
    parent_message_id: UUID | None,
) -> UUID | None:
    """Resolve the parent for a new user turn.

    None → the thread's current active leaf (or None for the first turn).
    Provided → validated to be an evidence-chat message in this thread.
    """
    if parent_message_id is None:
        return thread.active_leaf_message_id

    parent = await _load_thread_message(db, thread.id, parent_message_id)
    if parent is None or parent.turn_kind != ChatTurnKind.EVIDENCE_CHAT:
        raise EvidenceChatInvalidTarget(
            "parent_message_id is not a message in this evidence thread"
        )
    return parent.id


async def _sibling_info_for_branch(
    db: AsyncSession, branch: list[ChatMessage]
) -> dict[str, dict]:
    """Map message id → sibling position for active-branch nodes with siblings.

    Includes the ordered ``sibling_ids`` (oldest→newest) so the client can
    activate a specific sibling by id when the founder clicks ``<``/``>`` — the
    active-branch payload alone doesn't expose off-branch sibling ids.
    """
    info: dict[str, dict] = {}
    for msg in branch:
        siblings = await get_siblings(db, msg.id)
        if len(siblings) > 1:
            index = next(
                (i for i, s in enumerate(siblings) if s.id == msg.id), 0
            )
            info[str(msg.id)] = {
                "sibling_index": index,
                "sibling_count": len(siblings),
                "sibling_ids": [str(s.id) for s in siblings],
            }
    return info


async def send_evidence_chat_message(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
    selection_text: str | None = None,
    selection_question_id: str | None = None,
    parent_message_id: UUID | None = None,
    *,
    prompt_name: str | None = None,
    system_prompt: str | None = None,
    sources_block: str | None = None,
) -> EvidenceChatResult:
    """Send one evidence-chat turn (non-streaming) and persist both rows.

    Optional ``prompt_name`` / ``system_prompt`` / ``sources_block`` override
    phase-panel defaults (used by the universal-chat research sub-agent).
    Streaming and edit/regenerate paths are unchanged.

    The new user message hangs off ``parent_message_id`` (or the current active
    leaf when omitted); the assistant reply hangs off the user message and
    becomes the new active leaf.

    Raises:
        EvidenceChatNotFound: experiment not found/owned, or report missing.
        EvidenceChatInvalidTarget: parent_message_id invalid for this thread.
        ValueError: message empty after sanitization.
        LLM provider errors propagate (mapped to 502 by the router).
    """
    clean_message = _sanitize(message)
    if not clean_message:
        raise ValueError("message must not be empty")

    experiment, report_row = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    report = ValidationReportSchema.model_validate(report_row.raw_report)

    thread = await _resolve_evidence_thread(db, current_user, experiment)
    parent_id = await _resolve_parent_message_id(db, thread, parent_message_id)
    history = await get_branch_up_to(db, parent_id) if parent_id else []

    user_prompt = _build_user_prompt(
        experiment,
        report,
        clean_message,
        selection_text,
        selection_question_id,
        history,
        sources_block=sources_block,
    )

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=clean_message,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=parent_id,
    )
    db.add(user_msg)
    await db.flush()

    settings = get_settings()
    result = await llm_client.complete(
        db,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
        prompt_name=prompt_name or PROMPT_NAME_EVIDENCE_CHAT,
        system=system_prompt or EVIDENCE_CHAT_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
        experiment_id=experiment.id,
        phase="evidence_chat",
    )
    assistant_text = result.text.strip() or _FALLBACK_TEXT

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=user_msg.id,
    )
    db.add(assistant_msg)
    await db.flush()
    await set_active_leaf(db, thread.id, assistant_msg.id)
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


async def prepare_evidence_stream(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
    selection_text: str | None = None,
    selection_question_id: str | None = None,
    parent_message_id: UUID | None = None,
) -> EvidenceStreamPrep:
    """Handler-session phase of a streamed send: persist the user message + commit.

    Runs on the request-scoped session. The user message is committed here so a
    mid-stream client disconnect can never lose it. The thread's active leaf is
    pointed at the user message; the SSE generator advances it to the assistant
    reply on success.

    Raises:
        EvidenceChatNotFound / EvidenceChatInvalidTarget / ValueError as in send.
    """
    clean_message = _sanitize(message)
    if not clean_message:
        raise ValueError("message must not be empty")

    experiment, report_row = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    report = ValidationReportSchema.model_validate(report_row.raw_report)

    thread = await _resolve_evidence_thread(db, current_user, experiment)
    parent_id = await _resolve_parent_message_id(db, thread, parent_message_id)
    history = await get_branch_up_to(db, parent_id) if parent_id else []

    user_prompt = _build_user_prompt(
        experiment,
        report,
        clean_message,
        selection_text,
        selection_question_id,
        history,
    )

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=clean_message,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=parent_id,
    )
    db.add(user_msg)
    await db.flush()
    # Point the active leaf at the user message so it survives (and stays
    # visible) even if the stream fails before the assistant reply lands.
    await set_active_leaf(db, thread.id, user_msg.id)
    await db.commit()
    await db.refresh(user_msg)

    settings = get_settings()
    return EvidenceStreamPrep(
        experiment_id=experiment.id,
        thread_id=thread.id,
        user_message_id=user_msg.id,
        user_prompt=user_prompt,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
    )


def _sse(event: str, data: dict) -> str:
    """Format one SSE frame. ``data`` is JSON-encoded on a single ``data:`` line."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def format_sse_event(event: str, data: dict) -> str:
    """Public alias for SSE framing (universal chat stream endpoint)."""
    return _sse(event, data)


async def iter_llm_text_tokens(
    *,
    provider: str,
    model: str,
    system: str,
    user: str,
    usage: llm_client.StreamUsage,
    max_tokens: int = _MAX_TOKENS,
    temperature: float = _TEMPERATURE,
) -> AsyncGenerator[str, None]:
    """Yield plain LLM text tokens (no SSE framing).

    Shared by the evidence-chat SSE endpoint and the research sub-agent stream
    path. Caller owns ``usage`` and must call ``log_streamed_call`` on every
    terminal path.
    """
    async for piece in llm_client.complete_stream(
        provider=provider,  # type: ignore[arg-type]
        model=model,
        system=system,
        user=user,
        usage=usage,
        max_tokens=max_tokens,
        temperature=temperature,
    ):
        yield piece


async def stream_evidence_reply(
    prep: EvidenceStreamPrep,
) -> AsyncGenerator[str, None]:
    """Stream the assistant reply as SSE frames on a self-owned session.

    Yields ``token`` frames per chunk, then a ``done`` frame with ids +
    sibling_info on success, or an ``error`` frame on failure. On client
    disconnect (CancelledError / GeneratorExit) it records the LLMCall for cost
    accounting and re-raises without persisting an assistant row. The LLMCall is
    written on EVERY terminal path — success, error, and cancellation.
    """
    sessionmaker = get_sessionmaker()
    usage = llm_client.StreamUsage()

    async with sessionmaker() as gen_session:
        try:
            async for piece in iter_llm_text_tokens(
                provider=prep.provider,
                model=prep.model,
                system=EVIDENCE_CHAT_SYSTEM_PROMPT,
                user=prep.user_prompt,
                usage=usage,
            ):
                yield _sse("token", {"text": piece})
        except (asyncio.CancelledError, GeneratorExit):
            # Client disconnected mid-stream. Persist cost accounting, do NOT
            # persist a (partial) assistant message, produce no further output.
            await _log_stream_call_safely(gen_session, usage, prep)
            _logger.info(
                "evidence chat stream cancelled",
                experiment_id=str(prep.experiment_id),
                thread_id=str(prep.thread_id),
            )
            raise
        except Exception as exc:
            await _log_stream_call_safely(gen_session, usage, prep)
            _logger.warning(
                "evidence chat stream failed",
                experiment_id=str(prep.experiment_id),
                thread_id=str(prep.thread_id),
                error_type=type(exc).__name__,
            )
            yield _sse("error", {"message": "Evidence chat failed, please try again"})
            return

        # Success: persist assistant, advance active leaf, log cost, commit.
        assistant_text = usage.text.strip() or _FALLBACK_TEXT
        assistant_msg = ChatMessage(
            thread_id=prep.thread_id,
            role=ChatRole.ASSISTANT,
            content=assistant_text,
            experiment_id=prep.experiment_id,
            turn_kind=ChatTurnKind.EVIDENCE_CHAT,
            parent_message_id=prep.user_message_id,
        )
        gen_session.add(assistant_msg)
        await gen_session.flush()
        await set_active_leaf(gen_session, prep.thread_id, assistant_msg.id)
        await llm_client.log_streamed_call(
            gen_session,
            usage=usage,
            prompt_name=PROMPT_NAME_EVIDENCE_CHAT,
            experiment_id=prep.experiment_id,
            phase="evidence_chat",
        )
        await gen_session.commit()
        await gen_session.refresh(assistant_msg)

        branch = await get_active_branch(gen_session, prep.thread_id)
        sibling_info = await _sibling_info_for_branch(gen_session, branch)

        _logger.info(
            "evidence chat stream completed",
            experiment_id=str(prep.experiment_id),
            thread_id=str(prep.thread_id),
        )
        yield _sse(
            "done",
            {
                "assistant_message_id": str(assistant_msg.id),
                "user_message_id": str(prep.user_message_id),
                "thread_id": str(prep.thread_id),
                "sibling_info": sibling_info,
            },
        )


async def stream_research_evidence_tokens(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message: str,
    *,
    prompt_name: str,
    system_prompt: str,
    sources_block: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream evidence-thread tokens for the research sub-agent (no SSE framing).

    Persists the user row + commits before tokens; writes the assistant row and
    ``log_streamed_call`` only after a successful stream (same no-partial-
    assistant invariant as ``stream_evidence_reply``). Yields plain text pieces.
    On failure/cancel: logs cost, leaves no assistant row, re-raises.
    """
    clean_message = _sanitize(message)
    if not clean_message:
        raise ValueError("message must not be empty")

    experiment, report_row = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    report = ValidationReportSchema.model_validate(report_row.raw_report)

    thread = await _resolve_evidence_thread(db, current_user, experiment)
    parent_id = await _resolve_parent_message_id(db, thread, None)
    history = await get_branch_up_to(db, parent_id) if parent_id else []

    user_prompt = _build_user_prompt(
        experiment,
        report,
        clean_message,
        None,
        None,
        history,
        sources_block=sources_block,
    )

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=clean_message,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=parent_id,
    )
    db.add(user_msg)
    await db.flush()
    await set_active_leaf(db, thread.id, user_msg.id)
    await db.commit()

    settings = get_settings()
    usage = llm_client.StreamUsage()
    try:
        async for piece in iter_llm_text_tokens(
            provider=settings.refinement_provider,
            model=settings.refinement_model,
            system=system_prompt,
            user=user_prompt,
            usage=usage,
        ):
            yield piece
    except (asyncio.CancelledError, GeneratorExit):
        try:
            await llm_client.log_streamed_call(
                db,
                usage=usage,
                prompt_name=prompt_name,
                experiment_id=experiment.id,
                phase="evidence_chat",
            )
            await db.commit()
        except Exception as log_exc:
            with contextlib.suppress(Exception):
                await db.rollback()
            _logger.warning(
                "failed to log research subagent stream on cancel",
                error=str(log_exc),
            )
        raise
    except Exception:
        try:
            await llm_client.log_streamed_call(
                db,
                usage=usage,
                prompt_name=prompt_name,
                experiment_id=experiment.id,
                phase="evidence_chat",
            )
            await db.commit()
        except Exception as log_exc:
            with contextlib.suppress(Exception):
                await db.rollback()
            _logger.warning(
                "failed to log research subagent stream on error",
                error=str(log_exc),
            )
        raise

    assistant_text = usage.text.strip() or _FALLBACK_TEXT
    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=user_msg.id,
    )
    db.add(assistant_msg)
    await db.flush()
    await set_active_leaf(db, thread.id, assistant_msg.id)
    await llm_client.log_streamed_call(
        db,
        usage=usage,
        prompt_name=prompt_name,
        experiment_id=experiment.id,
        phase="evidence_chat",
    )
    await db.commit()

    _logger.info(
        "research evidence stream completed",
        experiment_id=str(experiment.id),
        thread_id=str(thread.id),
    )


async def _log_stream_call_safely(
    gen_session: AsyncSession,
    usage: llm_client.StreamUsage,
    prep: EvidenceStreamPrep,
) -> None:
    """Write the LLMCall row for a failed/cancelled stream; never mask the cause."""
    try:
        await llm_client.log_streamed_call(
            gen_session,
            usage=usage,
            prompt_name=PROMPT_NAME_EVIDENCE_CHAT,
            experiment_id=prep.experiment_id,
            phase="evidence_chat",
        )
        await gen_session.commit()
    except Exception as log_exc:
        with contextlib.suppress(Exception):
            await gen_session.rollback()
        _logger.warning(
            "failed to log streamed llm call on terminal path",
            error=str(log_exc),
        )


async def list_evidence_chat_messages(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
) -> EvidenceBranchMessages:
    """Return the active branch (root→leaf) + sibling info for the evidence thread.

    Empty thread → thread_id/active_leaf None, empty messages + sibling_info.

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
        return EvidenceBranchMessages(
            thread_id=None,
            active_leaf_message_id=None,
            messages=[],
            sibling_info={},
        )

    thread = await db.get(ChatThread, experiment.evidence_thread_id)
    active_leaf_id = thread.active_leaf_message_id if thread is not None else None
    branch = await get_active_branch(db, experiment.evidence_thread_id)
    sibling_info = await _sibling_info_for_branch(db, branch)

    return EvidenceBranchMessages(
        thread_id=experiment.evidence_thread_id,
        active_leaf_message_id=active_leaf_id,
        messages=branch,
        sibling_info=sibling_info,
    )


async def regenerate_evidence_chat_message(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    assistant_message_id: UUID,
    selection_text: str | None = None,
    selection_question_id: str | None = None,
) -> EvidenceChatResult:
    """Regenerate an assistant reply as a NEW SIBLING (branch-aware).

    The original assistant message and its subtree are preserved. A fresh reply
    is inserted with the same ``parent_message_id`` (the parent user message) and
    becomes the new active leaf.

    Raises:
        EvidenceChatNotFound: experiment/report/thread/message not found or not
            owned (404).
        EvidenceChatInvalidTarget: target is not an assistant evidence-chat
            message, or it has no parent user message (400).
        LLM provider errors propagate (mapped to 502); the turn rolls back.
    """
    experiment, report_row = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    if experiment.evidence_thread_id is None:
        raise EvidenceChatNotFound("Evidence thread not found")

    assistant = await _load_thread_message(
        db, experiment.evidence_thread_id, assistant_message_id
    )
    if assistant is None:
        raise EvidenceChatNotFound("Message not found")
    if (
        assistant.role != ChatRole.ASSISTANT
        or assistant.turn_kind != ChatTurnKind.EVIDENCE_CHAT
    ):
        raise EvidenceChatInvalidTarget(
            "Target is not an assistant evidence-chat message"
        )

    parent_user_id = assistant.parent_message_id
    parent_user = (
        await _load_thread_message(db, experiment.evidence_thread_id, parent_user_id)
        if parent_user_id is not None
        else None
    )
    if parent_user is None or parent_user.role != ChatRole.USER:
        raise EvidenceChatInvalidTarget("No parent user message found")

    report = ValidationReportSchema.model_validate(report_row.raw_report)
    # Context is the branch UP TO the parent user message's parent — i.e.
    # everything before the question we're re-answering.
    history = (
        await get_branch_up_to(db, parent_user.parent_message_id)
        if parent_user.parent_message_id is not None
        else []
    )
    user_prompt = _build_user_prompt(
        experiment,
        report,
        parent_user.content,
        selection_text,
        selection_question_id,
        history,
    )

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
    assistant_text = result.text.strip() or _FALLBACK_TEXT

    new_assistant = ChatMessage(
        thread_id=experiment.evidence_thread_id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=parent_user.id,
    )
    db.add(new_assistant)
    await db.flush()
    await set_active_leaf(db, experiment.evidence_thread_id, new_assistant.id)
    await db.commit()
    await db.refresh(new_assistant)
    await db.refresh(parent_user)

    _logger.info(
        "evidence chat regenerated",
        experiment_id=str(experiment.id),
        thread_id=str(experiment.evidence_thread_id),
        used_selection=bool(selection_text and selection_text.strip()),
    )

    return EvidenceChatResult(
        user_message=parent_user,
        assistant_message=new_assistant,
        thread_id=experiment.evidence_thread_id,
    )


async def edit_evidence_chat_message(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    user_message_id: UUID,
    content: str,
    selection_text: str | None = None,
    selection_question_id: str | None = None,
) -> EvidenceChatEditResult:
    """Edit a user message by branching: create a SIBLING with new content.

    The original user message and its subtree are preserved. A new user message
    is created with the same ``parent_message_id``, an assistant reply is
    generated as its child, and the active leaf moves to the new assistant.

    Raises:
        EvidenceChatNotFound: experiment/report/thread/message not found (404).
        EvidenceChatInvalidTarget: target is not a user evidence-chat message.
        ValueError: content empty after sanitization.
        LLM provider errors propagate (mapped to 502); the turn rolls back.
    """
    clean_content = _sanitize(content)
    if not clean_content:
        raise ValueError("content must not be empty")

    experiment, report_row = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    if experiment.evidence_thread_id is None:
        raise EvidenceChatNotFound("Evidence thread not found")

    original = await _load_thread_message(
        db, experiment.evidence_thread_id, user_message_id
    )
    if original is None:
        raise EvidenceChatNotFound("Message not found")
    if (
        original.role != ChatRole.USER
        or original.turn_kind != ChatTurnKind.EVIDENCE_CHAT
    ):
        raise EvidenceChatInvalidTarget("Target is not a user evidence-chat message")

    report = ValidationReportSchema.model_validate(report_row.raw_report)
    history = (
        await get_branch_up_to(db, original.parent_message_id)
        if original.parent_message_id is not None
        else []
    )
    user_prompt = _build_user_prompt(
        experiment,
        report,
        clean_content,
        selection_text,
        selection_question_id,
        history,
    )

    new_user = ChatMessage(
        thread_id=experiment.evidence_thread_id,
        role=ChatRole.USER,
        content=clean_content,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=original.parent_message_id,
    )
    db.add(new_user)
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
    assistant_text = result.text.strip() or _FALLBACK_TEXT

    new_assistant = ChatMessage(
        thread_id=experiment.evidence_thread_id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
        parent_message_id=new_user.id,
    )
    db.add(new_assistant)
    await db.flush()
    await set_active_leaf(db, experiment.evidence_thread_id, new_assistant.id)
    await db.commit()
    await db.refresh(new_user)
    await db.refresh(new_assistant)

    branch = await get_active_branch(db, experiment.evidence_thread_id)
    sibling_info = await _sibling_info_for_branch(db, branch)

    _logger.info(
        "evidence chat edited",
        experiment_id=str(experiment.id),
        thread_id=str(experiment.evidence_thread_id),
    )

    return EvidenceChatEditResult(
        new_user_message=new_user,
        new_assistant_message=new_assistant,
        thread_id=experiment.evidence_thread_id,
        active_leaf_message_id=new_assistant.id,
        sibling_info=sibling_info,
    )


async def activate_evidence_chat_branch(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message_id: UUID,
) -> EvidenceActivateResult:
    """Switch the active branch to the one containing ``message_id``.

    The target may be an interior node; we walk forward to the actual leaf of
    its branch (latest child at each step) and set THAT as the active leaf. This
    matches the Claude UX: clicking a sibling rehydrates its full downstream
    conversation.

    Raises:
        EvidenceChatNotFound: experiment/thread/message not found or not owned.
        EvidenceChatInvalidTarget: message is not in this evidence thread.
    """
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise EvidenceChatNotFound("Experiment not found")
    if experiment.evidence_thread_id is None:
        raise EvidenceChatNotFound("Evidence thread not found")

    target = await _load_thread_message(
        db, experiment.evidence_thread_id, message_id
    )
    if target is None:
        raise EvidenceChatNotFound("Message not found")
    if target.turn_kind != ChatTurnKind.EVIDENCE_CHAT:
        raise EvidenceChatInvalidTarget("Target is not an evidence-chat message")

    leaf = await get_leaf_of_branch(db, target.id)
    await set_active_leaf(db, experiment.evidence_thread_id, leaf.id)
    await db.commit()

    _logger.info(
        "evidence chat branch activated",
        experiment_id=str(experiment.id),
        thread_id=str(experiment.evidence_thread_id),
    )

    return EvidenceActivateResult(
        thread_id=experiment.evidence_thread_id,
        active_leaf_message_id=leaf.id,
    )


async def upsert_evidence_chat_feedback(
    db: AsyncSession,
    current_user: User,
    experiment_id: UUID,
    message_id: UUID,
    verdict: str,
) -> EvidenceChatFeedback:
    """Record (or update) the founder's thumbs verdict for an assistant message.

    One verdict per message (UNIQUE on message_id) — a second click upserts.

    Raises:
        EvidenceChatNotFound: experiment/report/thread/message not found or not
            owned (404).
        EvidenceChatInvalidTarget: message is not an assistant evidence-chat
            message (400).
    """
    experiment, _ = await _load_owned_experiment_and_report(
        db, current_user, experiment_id
    )
    if experiment.evidence_thread_id is None:
        raise EvidenceChatNotFound("Evidence thread not found")

    message = await _load_thread_message(
        db, experiment.evidence_thread_id, message_id
    )
    if message is None:
        raise EvidenceChatNotFound("Message not found")
    if (
        message.role != ChatRole.ASSISTANT
        or message.turn_kind != ChatTurnKind.EVIDENCE_CHAT
    ):
        raise EvidenceChatInvalidTarget(
            "Feedback target must be an assistant evidence-chat message"
        )

    existing_result = await db.execute(
        select(EvidenceChatFeedback).where(
            EvidenceChatFeedback.message_id == message_id
        )
    )
    row = existing_result.scalar_one_or_none()
    if row is not None:
        row.verdict = verdict
        row.user_id = current_user.id
    else:
        row = EvidenceChatFeedback(
            message_id=message_id,
            user_id=current_user.id,
            verdict=verdict,
        )
        db.add(row)
    await db.flush()
    await db.commit()
    await db.refresh(row)
    return row
