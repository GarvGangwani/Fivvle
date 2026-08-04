"""Sub-agent executors for the universal-chat tool loop (Phase 2).

``ask_refine_agent`` calls the existing refine chat service so rail and
phase-panel share the same refine thread. Research is master-native via
``get_research_context`` (see ``research_context.py``). Mapped results are
typed dicts persisted as ``tool_payload.result``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.logging_config import get_logger
from app.schemas.mcq_resolver import McqIndexResolution
from app.schemas.refinement import ClarifyingQuestion
from app.services import chat_service
from app.services.chat_tree_service import get_active_branch
from app.services.refinement_service import _RAIL_REFINE_MAX_TOKENS
from app.services.research_context import (  # noqa: F401 — re-export for tests
    build_source_index,
    build_source_refs_from_cite_ids,
    format_sources_block,
)

_logger = get_logger(__name__)

_POST_FINALIZE_MCQ_CAP = 3

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


def _sentence_case_label(label: str) -> str:
    """Normalize UPPERCASE MCQ labels for readable chat display."""
    lowered = label.strip().lower()
    if not lowered:
        return lowered
    for i, ch in enumerate(lowered):
        if ch.isalpha():
            return lowered[:i] + ch.upper() + lowered[i + 1 :]
    return lowered


def _natural_join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _combined_mcq_answer_text(pending: _PendingMcq, indices: list[int]) -> str:
    labels = [_sentence_case_label(pending.options[i]) for i in indices]
    return _natural_join_labels(labels)


def _parse_structured_mcq_answer(
    raw: Any,
) -> tuple[list[int], UUID, bool] | None:
    """Extract click/skip path from injected args.

    Returns ``(indices, answered_id, skipped)`` or None if malformed.
    """
    if not isinstance(raw, dict):
        return None
    qid_raw = raw.get("answered_question_id") or raw.get(
        "answered_question_from_message_id"
    )
    if qid_raw is None:
        return None
    try:
        answered_id = qid_raw if isinstance(qid_raw, UUID) else UUID(str(qid_raw))
    except (TypeError, ValueError):
        return None

    skipped = bool(raw.get("skipped"))
    if skipped:
        return [], answered_id, True

    indices_raw = raw.get("selected_option_indices")
    if not isinstance(indices_raw, list):
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
    return indices, answered_id, False


def _is_post_finalize(experiment: Experiment) -> bool:
    """True only after the founder has finalized at least once.

    ``refined_idea`` JSON is populated throughout REFINING as a WIP draft —
    that must NOT trip the rail's post-finalize clarifying-question cap.
    """
    return experiment.refined_idea_version >= 1


async def _count_post_finalize_clarifying_asks(
    db: AsyncSession,
    experiment: Experiment,
) -> int:
    """How many refine-thread assistant rows asked an MCQ after finalize."""
    if not _is_post_finalize(experiment) or experiment.thread_id is None:
        return 0
    branch = await get_active_branch(db, experiment.thread_id)
    count = 0
    for msg in branch:
        if msg.role != ChatRole.ASSISTANT:
            continue
        pending = _parse_pending_mcq_from_assistant(msg.clarifying_questions, msg.id)
        if pending is not None:
            count += 1
    return count


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
    1. Structured ``_mcq_answer`` skip — proceed without option indices.
    2. Structured ``_mcq_answer`` click — exact indices, no resolver.
    3. Pending MCQ + free-text query — ``mcq_resolver_v1`` maps prose → indices.
    4. Otherwise — normal refine turn (with post-finalize question cap).
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
    force_no_question = False

    pending = await _fetch_pending_mcq(db, experiment)
    structured = _parse_structured_mcq_answer(args.get("_mcq_answer"))

    if structured is not None and pending is not None:
        click_indices, answered_id, skipped = structured
        if answered_id == pending.message_id and skipped:
            turn_message = "Skipped"
            user_message_metadata = chat_service.build_user_message_metadata(
                answered_question_from_message_id=pending.message_id,
                skipped_clarifying_question=True,
            )
            _logger.info(
                "mcq skipped by founder",
                experiment_id=str(experiment.id),
                pending_message_id=str(pending.message_id),
            )
        elif answered_id == pending.message_id:
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

    if _is_post_finalize(experiment):
        prior_asks = await _count_post_finalize_clarifying_asks(db, experiment)
        if prior_asks >= _POST_FINALIZE_MCQ_CAP:
            force_no_question = True
            turn_message = (
                f"{turn_message}\n\n"
                "[rail_cap] Clarifying-question budget exhausted for this "
                "post-finalize session. Do NOT emit clarifying_questions — "
                "update refined_idea or answer briefly without a question."
            )
            _logger.info(
                "refine post-finalize mcq cap reached",
                experiment_id=str(experiment.id),
                prior_asks=prior_asks,
                cap=_POST_FINALIZE_MCQ_CAP,
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
        max_tokens=_RAIL_REFINE_MAX_TOKENS,
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
            experiment.refined_idea = refreshed.refined_idea
            experiment.refined_idea_version = refreshed.refined_idea_version

        clarifying = turn.clarifying_questions
        clarifying_list = list(clarifying) if clarifying is not None else None

        # Hard gate: strip clarifying questions if over post-finalize cap.
        if force_no_question and clarifying_list:
            clarifying_list = None
            from app.db.models.chat_message import ChatMessage

            assistant_row = await db.get(ChatMessage, turn.message_id)
            if assistant_row is not None:
                assistant_row.clarifying_questions = None
                assistant_row.clarifying_dimension = None
                await db.flush()

        assistant_text = turn.assistant_message
        has_mcq = bool(
            clarifying_list
            and _parse_pending_mcq_from_assistant(clarifying_list, turn.message_id)
        )
        if not isinstance(assistant_text, str):
            assistant_text = ""
        # Question-only turns: empty/minimal prose is valid when an MCQ is present.
        if not assistant_text.strip() and not has_mcq:
            if force_no_question:
                # Cap stripped a question-only LLM turn — surface brief prose.
                assistant_text = (
                    "I've got enough to keep going without another question."
                )
            else:
                _logger.warning(
                    "refine sub-agent returned empty assistant_message",
                    experiment_id=str(experiment.id),
                    has_clarifying=bool(clarifying_list),
                    clarifying_dimension=turn.clarifying_dimension,
                )
                return {"error": _REFINE_AGENT_TROUBLE}

        payload: dict[str, Any] = {
            "assistant_text": assistant_text.strip(),
            "refined_idea_patch": _refined_idea_patch(before_idea, after_idea),
            "log_entry": None if force_no_question else turn.clarifying_dimension,
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


def _refined_idea_patch(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return the post-turn idea when a write happened; else None."""
    if after is None:
        return None
    if before == after:
        return None
    return after


_REFINE_AGENT_TROUBLE = (
    "Refine agent had trouble — try again or open Refine phase"
)

