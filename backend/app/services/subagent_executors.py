"""Sub-agent executors for the universal-chat tool loop (Phase 2).

``ask_refine_agent`` and ``ask_research_agent`` call the existing refine /
evidence chat services so rail and phase-panel share the same threads.
Mapped results are typed dicts persisted as ``tool_payload.result``.
"""

from __future__ import annotations

import copy
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.llm.client as llm_client
from app.db.enums import ChatRole
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.dispatchers.protocol import ResearchDispatcher
from app.llm.prompts.mcq_resolver import (
    MCQ_RESOLVER_SYSTEM_PROMPT,
    PROMPT_NAME_MCQ_RESOLVER,
    build_mcq_resolver_user_prompt,
)
from app.llm.prompts.refine_subagent import (
    PROMPT_NAME_REFINE_SUBAGENT,
    REFINE_SUBAGENT_SYSTEM_PROMPT,
    build_refine_subagent_user_prompt,
)
from app.llm.prompts.research_subagent import (
    PROMPT_NAME_RESEARCH_SUBAGENT,
    RESEARCH_SUBAGENT_SYSTEM_PROMPT,
    format_sources_block,
)
from app.logging_config import get_logger
from app.schemas.mcq_resolver import McqIndexResolution
from app.schemas.refinement import ClarifyingQuestion
from app.services import chat_service
from app.services.chat_tree_service import get_active_branch
from app.services.evidence_chat_service import (
    send_evidence_chat_message,
    stream_research_evidence_tokens,
)

_logger = get_logger(__name__)

# Match evidence_chat_service streaming defaults.
_RESEARCH_STREAM_FALLBACK = (
    "I couldn't generate a response for that. Please try rephrasing your question."
)

# Rail research cites primary sources as [cite:sN] (not full URLs / [ref:]).
_CITE_SOURCE_ID_RE = re.compile(r"\[cite:\s*(s\d+)\]", re.IGNORECASE)

_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "The founder's question or request to forward to the sub-agent."
            ),
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

_MCQ_RESOLVER_PROVIDER: llm_client.ProviderName = "kimi"
_MCQ_RESOLVER_MODEL = "kimi-k2.6"
_MCQ_RESOLVER_MAX_TOKENS = 256
_MCQ_RESOLVER_TEMPERATURE = 0.2


class _NoopResearchDispatcher:
    """Refine turns no longer auto-dispatch research; satisfy the Protocol."""

    async def dispatch(self, experiment_id: UUID) -> None:
        _ = experiment_id


@dataclass(frozen=True)
class _PendingMcq:
    message_id: UUID
    question: str
    options: tuple[str, ...]
    selection_mode: str


def refine_agent_input_schema() -> dict[str, Any]:
    return copy.deepcopy(_QUERY_SCHEMA)


def research_agent_input_schema() -> dict[str, Any]:
    return copy.deepcopy(_QUERY_SCHEMA)


def _extract_query(args: dict[str, Any]) -> str | None:
    raw = args.get("query")
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    return cleaned or None


def _parse_pending_mcq_from_assistant(
    clarifying_questions: list[Any] | None,
    message_id: UUID,
) -> _PendingMcq | None:
    """First clarifying question with ≥2 options (matches frontend pickActiveMCQ)."""
    if not clarifying_questions:
        return None
    for raw in clarifying_questions:
        try:
            if isinstance(raw, ClarifyingQuestion):
                q = raw
            elif isinstance(raw, dict):
                q = ClarifyingQuestion.model_validate(raw)
            else:
                continue
        except Exception:  # noqa: BLE001 — skip malformed history rows
            continue
        if len(q.options) < 2:
            continue
        return _PendingMcq(
            message_id=message_id,
            question=q.question,
            options=tuple(q.options),
            selection_mode=q.selection_mode,
        )
    return None


async def _fetch_pending_mcq(
    db: AsyncSession,
    experiment: Experiment,
) -> _PendingMcq | None:
    if experiment.thread_id is None:
        return None
    branch = await get_active_branch(db, experiment.thread_id)
    if not branch:
        return None
    last = branch[-1]
    if last.role != ChatRole.ASSISTANT:
        return None
    return _parse_pending_mcq_from_assistant(last.clarifying_questions, last.id)


def _sanitize_selected_indices(
    indices: list[int],
    *,
    option_count: int,
    selection_mode: str,
) -> list[int]:
    valid = sorted({i for i in indices if isinstance(i, int) and 0 <= i < option_count})
    if selection_mode == "single" and len(valid) > 1:
        return valid[:1]
    return valid


async def _resolve_mcq_indices(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    pending: _PendingMcq,
    founder_message: str,
) -> list[int]:
    """Map founder prose → option indices. Empty = ambiguous / no match."""
    try:
        draft, _meta = await llm_client.complete_structured(
            db,
            provider=_MCQ_RESOLVER_PROVIDER,
            model=_MCQ_RESOLVER_MODEL,
            prompt_name=PROMPT_NAME_MCQ_RESOLVER,
            system=MCQ_RESOLVER_SYSTEM_PROMPT,
            user=build_mcq_resolver_user_prompt(
                question=pending.question,
                options=list(pending.options),
                selection_mode=pending.selection_mode,
                founder_message=founder_message,
            ),
            response_model=McqIndexResolution,
            max_tokens=_MCQ_RESOLVER_MAX_TOKENS,
            temperature=_MCQ_RESOLVER_TEMPERATURE,
            max_retries=2,
            experiment_id=experiment_id,
            phase="mcq_resolver",
        )
    except Exception as exc:  # noqa: BLE001 — soft-fail to normal refine turn
        _logger.warning(
            "mcq resolver failed; falling through to refine turn",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        return []

    return _sanitize_selected_indices(
        list(draft.selected_indices),
        option_count=len(pending.options),
        selection_mode=pending.selection_mode,
    )


def _combined_mcq_answer_text(pending: _PendingMcq, indices: list[int]) -> str:
    labels = [pending.options[i] for i in indices]
    return " · ".join(labels)


def _parse_structured_mcq_answer(
    raw: Any,
) -> tuple[list[int], UUID] | None:
    """Extract click-path indices + answered question id from injected args."""
    if not isinstance(raw, dict):
        return None
    indices_raw = raw.get("selected_option_indices")
    qid_raw = raw.get("answered_question_id") or raw.get(
        "answered_question_from_message_id"
    )
    if not isinstance(indices_raw, list) or qid_raw is None:
        return None
    indices: list[int] = []
    for item in indices_raw:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            indices.append(item)
        elif isinstance(item, str) and item.strip().lstrip("-").isdigit():
            indices.append(int(item.strip()))
    if not indices:
        return None
    try:
        answered_id = qid_raw if isinstance(qid_raw, UUID) else UUID(str(qid_raw))
    except (TypeError, ValueError):
        return None
    return indices, answered_id


def _outbound_mcq_fields(
    clarifying: list[Any] | None,
    message_id: UUID,
) -> dict[str, Any]:
    """Surface pending MCQ for inline rail rendering (empty when none)."""
    pending = _parse_pending_mcq_from_assistant(clarifying, message_id)
    if pending is None:
        return {"has_pending_mcq": False}
    return {
        "has_pending_mcq": True,
        "mcq_question": pending.question,
        "mcq_options": [
            {"index": i, "label": label}
            for i, label in enumerate(pending.options)
        ],
        "mcq_answered_question_id": str(pending.message_id),
        "mcq_selection_mode": pending.selection_mode,
    }


async def exec_ask_refine_agent(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    """Forward ``query`` into the refine thread via ``chat_service.handle_turn``.

    MCQ answering branches (in order):
    1. Structured ``_mcq_answer`` from a rail click — exact indices, no resolver.
    2. Pending MCQ + free-text query — ``mcq_resolver_v1`` maps prose → indices.
    3. Otherwise — normal refine turn.
    """
    query = _extract_query(args)
    if query is None:
        return {"error": "query is required"}

    before_idea = (
        copy.deepcopy(experiment.refined_idea_current)
        if isinstance(experiment.refined_idea_current, dict)
        else None
    )

    dispatcher: ResearchDispatcher = cast(
        ResearchDispatcher, _NoopResearchDispatcher()
    )
    user_message_metadata: dict[str, Any] | None = None
    turn_message = query

    pending = await _fetch_pending_mcq(db, experiment)
    structured = _parse_structured_mcq_answer(args.get("_mcq_answer"))

    if structured is not None and pending is not None:
        click_indices, answered_id = structured
        if answered_id == pending.message_id:
            selected = _sanitize_selected_indices(
                click_indices,
                option_count=len(pending.options),
                selection_mode=pending.selection_mode,
            )
            if selected:
                turn_message = _combined_mcq_answer_text(pending, selected)
                user_message_metadata = chat_service.build_user_message_metadata(
                    selected_option_indices=selected,
                    answered_question_from_message_id=pending.message_id,
                )
                _logger.info(
                    "mcq click submitted exact indices",
                    experiment_id=str(experiment.id),
                    selected_indices=selected,
                    pending_message_id=str(pending.message_id),
                )
            else:
                _logger.info(
                    "mcq click indices invalid; falling through to refine turn",
                    experiment_id=str(experiment.id),
                    pending_message_id=str(pending.message_id),
                )
        else:
            _logger.info(
                "mcq click answered_question_id mismatch; falling through",
                experiment_id=str(experiment.id),
                expected=str(pending.message_id),
                got=str(answered_id),
            )
    elif pending is not None:
        selected = await _resolve_mcq_indices(
            db,
            experiment_id=experiment.id,
            pending=pending,
            founder_message=query,
        )
        if selected:
            turn_message = _combined_mcq_answer_text(pending, selected)
            user_message_metadata = chat_service.build_user_message_metadata(
                selected_option_indices=selected,
                answered_question_from_message_id=pending.message_id,
            )
            _logger.info(
                "mcq resolver matched rail answer",
                experiment_id=str(experiment.id),
                selected_indices=selected,
                pending_message_id=str(pending.message_id),
            )
        else:
            _logger.info(
                "mcq resolver ambiguous; treating as new refine turn",
                experiment_id=str(experiment.id),
                pending_message_id=str(pending.message_id),
            )

    turn = await chat_service.handle_turn(
        db,
        user=user,
        message=turn_message,
        deep_research=True,
        thread_id=experiment.thread_id,
        experiment_id=experiment.id,
        idempotency_key=f"universal-refine-{uuid4()}",
        dispatcher=dispatcher,
        user_message_metadata=user_message_metadata,
        prompt_name=PROMPT_NAME_REFINE_SUBAGENT,
        system_prompt=REFINE_SUBAGENT_SYSTEM_PROMPT,
        user_prompt_builder=build_refine_subagent_user_prompt,
    )

    # handle_turn catches run_turn failures and returns a ChatTurnResult with
    # user_facing_error set (e.g. refinement ValidationError → "Something
    # didn't parse…"). That is not a successful sub-agent answer for the rail.
    if turn.user_facing_error is not None:
        _logger.warning(
            "refine sub-agent turn failed upstream",
            experiment_id=str(experiment.id),
            retry_action=turn.user_facing_error.retry_action,
            upstream_message=turn.user_facing_error.message,
        )
        return {"error": _REFINE_AGENT_TROUBLE}

    try:
        # Reload experiment — handle_turn commits; identity may be expired.
        refreshed = await db.get(Experiment, experiment.id)
        after_idea: dict[str, Any] | None = None
        if refreshed is not None and isinstance(
            refreshed.refined_idea_current, dict
        ):
            after_idea = refreshed.refined_idea_current
            # Keep caller's experiment instance in sync for subsequent tools.
            experiment.refined_idea_current = after_idea
            experiment.thread_id = refreshed.thread_id
            experiment.status = refreshed.status
            experiment.refinement_count = refreshed.refinement_count

        clarifying = turn.clarifying_questions
        clarifying_list = list(clarifying) if clarifying is not None else None
        assistant_text = turn.assistant_message
        if not isinstance(assistant_text, str) or not assistant_text.strip():
            _logger.warning(
                "refine sub-agent returned empty assistant_message",
                experiment_id=str(experiment.id),
                has_clarifying=bool(clarifying_list),
                clarifying_dimension=turn.clarifying_dimension,
            )
            return {"error": _REFINE_AGENT_TROUBLE}

        payload: dict[str, Any] = {
            "assistant_text": assistant_text,
            "refined_idea_patch": _refined_idea_patch(before_idea, after_idea),
            "log_entry": turn.clarifying_dimension,
        }
        payload.update(_outbound_mcq_fields(clarifying_list, turn.message_id))
        return payload
    except (AttributeError, KeyError, TypeError) as exc:
        _logger.warning(
            "refine sub-agent result mapping failed",
            experiment_id=str(experiment.id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return {"error": _REFINE_AGENT_TROUBLE}


def _domain_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse

        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host or url
    except Exception:
        return url


def _iter_report_citations(report: dict[str, Any]) -> list[dict[str, str]]:
    """Collect Citation-shaped dicts from findings + competitors (dedupe by URL)."""
    collected: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def _add(cite: Any) -> None:
        if not isinstance(cite, dict):
            return
        url = cite.get("url")
        if not isinstance(url, str) or not url.strip():
            return
        url = url.strip()
        if url in seen_urls:
            return
        seen_urls.add(url)
        title = cite.get("title")
        domain = cite.get("source_domain")
        collected.append(
            {
                "source_title": title.strip()
                if isinstance(title, str) and title.strip()
                else url,
                "source_url": url,
                "source_domain": domain.strip()
                if isinstance(domain, str) and domain.strip()
                else _domain_from_url(url),
            }
        )

    for qf in report.get("questions_and_findings") or []:
        if not isinstance(qf, dict):
            continue
        for finding in qf.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            for cite in finding.get("citations") or []:
                _add(cite)

    for comp in report.get("competitors") or []:
        if not isinstance(comp, dict):
            continue
        for cite in comp.get("citations") or []:
            _add(cite)

    return collected


def build_source_index(
    report: dict[str, Any] | None,
) -> dict[str, dict[str, str | None]]:
    """Map ``s1``..``sN`` -> primary source metadata from the validation report."""
    if not report:
        return {}
    index: dict[str, dict[str, str | None]] = {}
    for i, cite in enumerate(_iter_report_citations(report), start=1):
        source_id = f"s{i}"
        index[source_id] = {
            "source_title": cite["source_title"],
            "source_url": cite["source_url"],
            "source_domain": cite["source_domain"],
        }
    return index


def build_source_refs_from_cite_ids(
    text: str,
    source_index: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    """Resolve in-content ``[cite:sN]`` markers via ``source_index``.

    Unresolved ids and ``[ref:...]`` markers are dropped (frontend shows them
    as plain text).
    """
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _CITE_SOURCE_ID_RE.finditer(text):
        source_id = match.group(1).lower()
        if source_id in seen:
            continue
        meta = source_index.get(source_id)
        if meta is None:
            continue
        seen.add(source_id)
        marker_id = f"[cite:{source_id}]"
        refs.append(
            {
                "marker_id": marker_id,
                "source_title": meta.get("source_title") or source_id,
                "source_url": meta.get("source_url"),
                "source_domain": meta.get("source_domain"),
            }
        )
    return refs


def _refined_idea_patch(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return the post-turn idea when a write happened; else None.

    ``RefinementTurnDecision`` has no patch type — ``run_turn`` replaces
    ``refined_idea_current`` with a full ``RefinedIdea`` dump when present.
    """
    if after is None:
        return None
    if before == after:
        return None
    return after


_REFINE_AGENT_TROUBLE = (
    "Refine agent had trouble — try again or open Refine phase"
)


async def exec_ask_research_agent(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    """Forward ``query`` into evidence chat (non-streaming) on ``evidence_thread_id``."""
    query = _extract_query(args)
    if query is None:
        return {"error": "query is required"}

    report_raw: dict[str, Any] | None = None
    exp_result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment.id)
    )
    exp = exp_result.scalar_one_or_none()
    if exp is not None and exp.validation_report is not None:
        raw = exp.validation_report.raw_report
        if isinstance(raw, dict):
            report_raw = raw

    source_index = build_source_index(report_raw)
    sources_block = format_sources_block(source_index)

    result = await send_evidence_chat_message(
        db,
        current_user=user,
        experiment_id=experiment.id,
        message=query,
        prompt_name=PROMPT_NAME_RESEARCH_SUBAGENT,
        system_prompt=RESEARCH_SUBAGENT_SYSTEM_PROMPT,
        sources_block=sources_block,
    )

    assistant_text = result.assistant_message.content or ""

    if exp is not None and exp.evidence_thread_id is not None:
        experiment.evidence_thread_id = exp.evidence_thread_id
    else:
        refreshed = await db.get(Experiment, experiment.id)
        if refreshed is not None and refreshed.evidence_thread_id is not None:
            experiment.evidence_thread_id = refreshed.evidence_thread_id

    return {
        "assistant_text_with_citations": assistant_text,
        "source_refs": build_source_refs_from_cite_ids(assistant_text, source_index),
    }


async def exec_ask_research_agent_stream(
    db: AsyncSession,
    experiment: Experiment,
    args: dict[str, Any],
    user: User,
) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """Stream research sub-agent tokens; yield ``token`` then ``complete``.

    Uses ``stream_research_evidence_tokens`` (shared LLM token iterator). The
    universal master wraps tokens with ``agent: research`` attribution. On soft
    failure yields a single ``complete`` with ``error`` and no tokens.
    """
    query = _extract_query(args)
    if query is None:
        yield ("complete", {"error": "query is required"})
        return

    report_raw: dict[str, Any] | None = None
    exp_result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment.id)
    )
    exp = exp_result.scalar_one_or_none()
    if exp is not None and exp.validation_report is not None:
        raw = exp.validation_report.raw_report
        if isinstance(raw, dict):
            report_raw = raw

    source_index = build_source_index(report_raw)
    sources_block = format_sources_block(source_index)

    parts: list[str] = []
    try:
        async for piece in stream_research_evidence_tokens(
            db,
            user,
            experiment.id,
            query,
            prompt_name=PROMPT_NAME_RESEARCH_SUBAGENT,
            system_prompt=RESEARCH_SUBAGENT_SYSTEM_PROMPT,
            sources_block=sources_block,
        ):
            parts.append(piece)
            yield ("token", {"text": piece})
    except Exception as exc:
        _logger.warning(
            "research subagent stream failed",
            experiment_id=str(experiment.id),
            error_type=type(exc).__name__,
        )
        yield (
            "complete",
            {"error": f"{type(exc).__name__}: tool execution failed"},
        )
        return

    assistant_text = "".join(parts).strip() or _RESEARCH_STREAM_FALLBACK

    if exp is not None and exp.evidence_thread_id is not None:
        experiment.evidence_thread_id = exp.evidence_thread_id
    else:
        refreshed = await db.get(Experiment, experiment.id)
        if refreshed is not None and refreshed.evidence_thread_id is not None:
            experiment.evidence_thread_id = refreshed.evidence_thread_id

    yield (
        "complete",
        {
            "assistant_text_with_citations": assistant_text,
            "source_refs": build_source_refs_from_cite_ids(
                assistant_text, source_index
            ),
        },
    )
