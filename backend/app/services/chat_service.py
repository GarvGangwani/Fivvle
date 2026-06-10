"""Chat orchestration — deep research refinement turns and plain chat (planning §9).

HTTP routing lives in Step 5b; this module owns thread/experiment lifecycle,
refinement turns, dispatch on finalize, and plain-chat replies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
import app.services.refinement_service as refinement_service
from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, DispatchTrigger, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.refinement_idempotency import RefinementIdempotency
from app.db.models.user import User
from app.dispatchers.protocol import DispatchError, ResearchDispatcher
from app.llm.prompts.chat_discussion import (
    CHAT_DISCUSSION_SYSTEM_PROMPT,
    PROMPT_NAME_CHAT_DISCUSSION,
    build_chat_discussion_user_prompt,
)
from app.llm.prompts.chat_normal import (
    CHAT_NORMAL_SYSTEM_PROMPT,
    PROMPT_NAME_CHAT_NORMAL,
    build_chat_normal_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.refinement import RefinementTurnDecision
from app.services.chat_discussion_context import build_experiment_discussion_context
from app.services import dispatch_service, rollout
from app.services.error_translation import UserFacingError, translate_engineer_error
from app.services.experiment_service import InvalidExperimentState

_logger = get_logger(__name__)

_IN_FLIGHT_REFINING_WINDOW = timedelta(minutes=30)
_MAX_ERROR_DETAIL_LEN = 500
_THREAD_TITLE_MAX_LEN = 40

_SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY = frozenset(
    {
        ChatTurnKind.DISPATCH_ANNOUNCE,
        ChatTurnKind.PIPELINE_PROGRESS,
        ChatTurnKind.PIPELINE_COMPLETE,
        ChatTurnKind.PIPELINE_FAILED,
    }
)

_PLAIN_CHAT_HISTORY_TURN_KINDS = frozenset(
    {
        ChatTurnKind.NORMAL_CHAT,
        ChatTurnKind.DISCUSS,
        ChatTurnKind.REFINEMENT_CLARIFY,
        ChatTurnKind.REFINEMENT_FINALIZE,
    }
)

_PLAIN_CHAT_MAX_TOKENS = 1024
_DISCUSSION_CHAT_MAX_TOKENS = 1536


class ChatAuthorizationError(Exception):
    """Raised when a thread or experiment is not owned by the requesting user."""


@dataclass(frozen=True)
class ChatTurnResult:
    thread_id: UUID
    message_id: UUID
    experiment_id: UUID | None
    assistant_message: str
    turn_kind: ChatTurnKind
    clarifying_dimension: str | None
    pipeline_dispatched: bool
    dispatched_at: datetime | None
    experiment_status: ExperimentStatus | None
    research_error_detail: str | None
    user_facing_error: UserFacingError | None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "thread_id": str(self.thread_id),
            "message_id": str(self.message_id),
            "experiment_id": (
                str(self.experiment_id) if self.experiment_id is not None else None
            ),
            "assistant_message": self.assistant_message,
            "turn_kind": self.turn_kind.value,
            "clarifying_dimension": self.clarifying_dimension,
            "pipeline_dispatched": self.pipeline_dispatched,
            "dispatched_at": (
                self.dispatched_at.isoformat() if self.dispatched_at is not None else None
            ),
            "experiment_status": (
                self.experiment_status.value
                if self.experiment_status is not None
                else None
            ),
            "research_error_detail": self.research_error_detail,
            "user_facing_error": (
                None
                if self.user_facing_error is None
                else {
                    "message": self.user_facing_error.message,
                    "retry_action": self.user_facing_error.retry_action,
                }
            ),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> ChatTurnResult:
        ufe_raw = data.get("user_facing_error")
        user_facing_error: UserFacingError | None = None
        if isinstance(ufe_raw, dict):
            user_facing_error = UserFacingError(
                message=str(ufe_raw["message"]),
                retry_action=ufe_raw["retry_action"],  # type: ignore[arg-type]
            )

        dispatched_raw = data.get("dispatched_at")
        dispatched_at: datetime | None = None
        if dispatched_raw is not None:
            dispatched_at = datetime.fromisoformat(str(dispatched_raw))

        status_raw = data.get("experiment_status")
        experiment_status: ExperimentStatus | None = None
        if status_raw is not None:
            experiment_status = ExperimentStatus(str(status_raw))

        exp_raw = data.get("experiment_id")
        experiment_id: UUID | None = None
        if exp_raw is not None:
            experiment_id = UUID(str(exp_raw))

        return cls(
            thread_id=UUID(str(data["thread_id"])),
            message_id=UUID(str(data["message_id"])),
            experiment_id=experiment_id,
            assistant_message=str(data["assistant_message"]),
            turn_kind=ChatTurnKind(str(data["turn_kind"])),
            clarifying_dimension=data.get("clarifying_dimension"),
            pipeline_dispatched=bool(data["pipeline_dispatched"]),
            dispatched_at=dispatched_at,
            experiment_status=experiment_status,
            research_error_detail=data.get("research_error_detail"),
            user_facing_error=user_facing_error,
        )


def _sanitize_error_detail(phase: str, exc: BaseException) -> str:
    """Same shape as research_engine_service._sanitize_error_detail (no secrets scrub)."""
    detail = f"{phase}:{type(exc).__name__}: {exc!s}"
    return detail[:_MAX_ERROR_DETAIL_LEN]


def _sanitize_user_message(message: str) -> str:
    """Strip NUL bytes so Postgres UTF-8 text columns accept the payload."""
    return message.replace("\x00", "")


def _thread_title_from_message(message: str) -> str:
    """First 40 chars, control chars stripped, no newlines (planning §8)."""
    flattened = message.replace("\n", " ").replace("\r", " ")
    cleaned = "".join(ch for ch in flattened if ch.isprintable() and ch not in "\t\v\f")
    title = cleaned[:_THREAD_TITLE_MAX_LEN].strip()
    return title or "Chat"


async def _resolve_thread(
    db: AsyncSession,
    user: User,
    thread_id: UUID | None,
    *,
    first_message_for_title: str | None = None,
) -> ChatThread:
    if thread_id is None:
        title = (
            _thread_title_from_message(first_message_for_title)
            if first_message_for_title
            else None
        )
        thread = ChatThread(user_id=user.id, title=title)
        db.add(thread)
        await db.flush()
        return thread

    result = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
    thread = result.scalar_one_or_none()
    if thread is None or thread.user_id != user.id:
        raise ChatAuthorizationError("Thread not found or not owned by user")
    return thread


async def _load_dr_chat_history(
    db: AsyncSession,
    thread_id: UUID,
) -> list[tuple[str, str]]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history: list[tuple[str, str]] = []
    for row in result.scalars().all():
        if row.turn_kind in _SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY:
            continue
        history.append((row.role.value, row.content))
    return history


async def _load_plain_chat_history(
    db: AsyncSession,
    thread_id: UUID,
) -> list[tuple[str, str]]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history: list[tuple[str, str]] = []
    for row in result.scalars().all():
        if row.turn_kind is not None and row.turn_kind not in _PLAIN_CHAT_HISTORY_TURN_KINDS:
            continue
        history.append((row.role.value, row.content))
    return history


async def _resolve_experiment_for_plain_chat(
    db: AsyncSession,
    user: User,
    thread: ChatThread,
    experiment_id: UUID | None,
) -> Experiment | None:
    experiment: Experiment | None = None

    if experiment_id is not None:
        result = await db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if experiment is None or experiment.user_id != user.id:
            raise ChatAuthorizationError("Experiment not found or not owned by user")
        if experiment.thread_id is not None and experiment.thread_id != thread.id:
            raise InvalidExperimentState(
                "Experiment does not belong to this chat thread"
            )
        if experiment.status == ExperimentStatus.ARCHIVED:
            raise InvalidExperimentState(
                "Chat is not available for archived experiments"
            )
        return experiment

    result = await db.execute(
        select(Experiment)
        .where(Experiment.thread_id == thread.id)
        .order_by(Experiment.created_at.desc())
        .limit(1)
    )
    experiment = result.scalar_one_or_none()
    if experiment is not None and experiment.status == ExperimentStatus.ARCHIVED:
        raise InvalidExperimentState(
            "Chat is not available for archived experiments"
        )
    return experiment


def _uses_discussion_mode(experiment: Experiment | None) -> bool:
    return (
        experiment is not None
        and experiment.status != ExperimentStatus.REFINING
    )


async def list_thread_messages(
    db: AsyncSession,
    user: User,
    thread_id: UUID,
) -> list[ChatMessage]:
    """Return thread messages in chronological order (ownership enforced)."""
    thread = await _resolve_thread(db, user, thread_id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread.id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages: list[ChatMessage] = []
    for row in result.scalars().all():
        if row.turn_kind in _SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY:
            continue
        messages.append(row)
    return messages


async def list_experiment_chat_messages(
    db: AsyncSession,
    user: User,
    experiment_id: UUID,
) -> tuple[UUID | None, list[ChatMessage]]:
    """Load chat history for an experiment's linked thread."""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user.id:
        raise ChatAuthorizationError("Experiment not found or not owned by user")
    if experiment.thread_id is None:
        return None, []

    messages = await list_thread_messages(db, user, experiment.thread_id)
    return experiment.thread_id, messages


async def _find_in_flight_refinement_experiment(
    db: AsyncSession,
    thread_id: UUID,
) -> Experiment | None:
    cutoff = datetime.now(UTC) - _IN_FLIGHT_REFINING_WINDOW
    result = await db.execute(
        select(Experiment)
        .where(
            Experiment.thread_id == thread_id,
            Experiment.status == ExperimentStatus.REFINING,
            Experiment.updated_at > cutoff,
        )
        .order_by(Experiment.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_refinement_experiment(
    db: AsyncSession,
    user: User,
    thread: ChatThread,
    message: str,
    experiment_id: UUID | None,
) -> Experiment:
    if experiment_id is not None:
        result = await db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        if experiment is None or experiment.user_id != user.id:
            raise ChatAuthorizationError("Experiment not found or not owned by user")
        if experiment.thread_id != thread.id:
            raise InvalidExperimentState(
                "Experiment does not belong to this chat thread"
            )
        if experiment.status != ExperimentStatus.REFINING:
            raise InvalidExperimentState(
                f"Experiment must be in REFINING status (current: {experiment.status})"
            )
        return experiment

    existing = await _find_in_flight_refinement_experiment(db, thread.id)
    if existing is not None:
        return existing

    experiment = Experiment(
        user_id=user.id,
        thread_id=thread.id,
        raw_idea=message,
        status=ExperimentStatus.REFINING,
        refinement_count=0,
    )
    db.add(experiment)
    await db.flush()
    return experiment


async def _fetch_idempotent_result(
    db: AsyncSession,
    thread_id: UUID,
    idempotency_key: str,
) -> ChatTurnResult | None:
    result = await db.execute(
        select(RefinementIdempotency).where(
            RefinementIdempotency.thread_id == thread_id,
            RefinementIdempotency.idempotency_key == idempotency_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return ChatTurnResult.from_json_dict(row.response_payload)


async def _store_idempotency(
    db: AsyncSession,
    thread_id: UUID,
    idempotency_key: str,
    payload: ChatTurnResult,
) -> None:
    await db.execute(
        pg_insert(RefinementIdempotency)
        .values(
            thread_id=thread_id,
            idempotency_key=idempotency_key,
            response_payload=payload.to_json_dict(),
            experiment_id=payload.experiment_id,
        )
        .on_conflict_do_nothing()
    )


async def reply_plain(
    db: AsyncSession,
    chat_history: list[tuple[str, str]],
    latest_message: str,
    *,
    experiment_id: UUID | None = None,
) -> str:
    """Run plain chat turn. Returns assistant text.

    TODO(v2): translate LLM failures via error_translation for plain-chat UX.
    """
    user_prompt = build_chat_normal_user_prompt(
        chat_history=chat_history,
        latest_message=latest_message,
    )
    settings = get_settings()
    result = await llm_client.complete(
        db,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
        prompt_name=PROMPT_NAME_CHAT_NORMAL,
        system=CHAT_NORMAL_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=_PLAIN_CHAT_MAX_TOKENS,
        temperature=0.7,
        experiment_id=experiment_id,
        phase="chat_normal",
    )
    return result.text


async def reply_discussion(
    db: AsyncSession,
    experiment: Experiment,
    chat_history: list[tuple[str, str]],
    latest_message: str,
) -> str:
    """Run post-research discussion turn. Returns assistant text."""
    experiment_context = await build_experiment_discussion_context(db, experiment)
    user_prompt = build_chat_discussion_user_prompt(
        experiment_context=experiment_context,
        chat_history=chat_history,
        latest_message=latest_message,
    )
    settings = get_settings()
    result = await llm_client.complete(
        db,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
        prompt_name=PROMPT_NAME_CHAT_DISCUSSION,
        system=CHAT_DISCUSSION_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=_DISCUSSION_CHAT_MAX_TOKENS,
        temperature=0.7,
        experiment_id=experiment.id,
        phase="chat_discussion",
    )
    return result.text


async def handle_turn(
    db: AsyncSession,
    user: User,
    message: str,
    deep_research: bool,
    thread_id: UUID | None,
    experiment_id: UUID | None,
    idempotency_key: str | None,
    dispatcher: ResearchDispatcher,
) -> ChatTurnResult:
    """Top-level entry. Handles both DR and plain-chat paths."""
    message = _sanitize_user_message(message)
    if deep_research:
        return await _handle_deep_research_turn(
            db,
            user=user,
            message=message,
            thread_id=thread_id,
            experiment_id=experiment_id,
            idempotency_key=idempotency_key,
            dispatcher=dispatcher,
        )
    return await _handle_plain_chat_turn(
        db,
        user=user,
        message=message,
        thread_id=thread_id,
        experiment_id=experiment_id,
    )


async def _handle_plain_chat_turn(
    db: AsyncSession,
    *,
    user: User,
    message: str,
    thread_id: UUID | None,
    experiment_id: UUID | None,
) -> ChatTurnResult:
    thread = await _resolve_thread(
        db,
        user,
        thread_id,
        first_message_for_title=message if thread_id is None else None,
    )

    experiment = await _resolve_experiment_for_plain_chat(
        db, user, thread, experiment_id
    )
    if _uses_discussion_mode(experiment):
        assert experiment is not None
        return await _handle_discussion_turn(
            db,
            message=message,
            thread=thread,
            experiment=experiment,
        )

    chat_history = await _load_plain_chat_history(db, thread.id)

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=message,
        experiment_id=experiment.id if experiment is not None else None,
        turn_kind=None,
    )
    db.add(user_msg)
    await db.flush()

    assistant_text = await reply_plain(
        db,
        chat_history,
        message,
        experiment_id=experiment.id if experiment is not None else None,
    )

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id if experiment is not None else None,
        turn_kind=ChatTurnKind.NORMAL_CHAT,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatTurnResult(
        thread_id=thread.id,
        message_id=assistant_msg.id,
        experiment_id=experiment.id if experiment is not None else None,
        assistant_message=assistant_text,
        turn_kind=ChatTurnKind.NORMAL_CHAT,
        clarifying_dimension=None,
        pipeline_dispatched=False,
        dispatched_at=None,
        experiment_status=experiment.status if experiment is not None else None,
        research_error_detail=(
            experiment.research_error_detail if experiment is not None else None
        ),
        user_facing_error=None,
    )


async def _handle_discussion_turn(
    db: AsyncSession,
    *,
    message: str,
    thread: ChatThread,
    experiment: Experiment,
) -> ChatTurnResult:
    chat_history = await _load_dr_chat_history(db, thread.id)

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=message,
        experiment_id=experiment.id,
        turn_kind=None,
    )
    db.add(user_msg)
    await db.flush()

    assistant_text = await reply_discussion(db, experiment, chat_history, message)

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.DISCUSS,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatTurnResult(
        thread_id=thread.id,
        message_id=assistant_msg.id,
        experiment_id=experiment.id,
        assistant_message=assistant_text,
        turn_kind=ChatTurnKind.DISCUSS,
        clarifying_dimension=None,
        pipeline_dispatched=False,
        dispatched_at=None,
        experiment_status=experiment.status,
        research_error_detail=experiment.research_error_detail,
        user_facing_error=None,
    )


async def _handle_deep_research_turn(
    db: AsyncSession,
    *,
    user: User,
    message: str,
    thread_id: UUID | None,
    experiment_id: UUID | None,
    idempotency_key: str | None,
    dispatcher: ResearchDispatcher,
) -> ChatTurnResult:
    if idempotency_key is None:
        raise ValueError("idempotency_key required for deep_research=true")

    thread = await _resolve_thread(
        db,
        user,
        thread_id,
        first_message_for_title=message if thread_id is None else None,
    )

    cached = await _fetch_idempotent_result(db, thread.id, idempotency_key)
    if cached is not None:
        return cached

    experiment = await _resolve_refinement_experiment(
        db, user, thread, message, experiment_id
    )

    chat_history = await _load_dr_chat_history(db, thread.id)

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=message,
        experiment_id=experiment.id,
        turn_kind=None,
    )
    db.add(user_msg)
    await db.flush()

    try:
        decision = await refinement_service.run_turn(
            db,
            experiment,
            chat_history,
            message,
        )
    except Exception as exc:
        user_error = translate_engineer_error(
            type(exc).__name__,
            _sanitize_error_detail("refinement", exc),
            experiment.status,
        )
        assistant_msg = ChatMessage(
            thread_id=thread.id,
            role=ChatRole.ASSISTANT,
            content=user_error.message,
            experiment_id=experiment.id,
            turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
        )
        db.add(assistant_msg)
        await db.commit()
        return ChatTurnResult(
            thread_id=thread.id,
            message_id=assistant_msg.id,
            experiment_id=experiment.id,
            assistant_message=user_error.message,
            turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
            clarifying_dimension=None,
            pipeline_dispatched=False,
            dispatched_at=None,
            experiment_status=experiment.status,
            research_error_detail=experiment.research_error_detail,
            user_facing_error=user_error,
        )

    if decision.decision == "finalize":
        turn_kind = ChatTurnKind.REFINEMENT_FINALIZE
        clarifying_dimension = None
    else:
        turn_kind = ChatTurnKind.REFINEMENT_CLARIFY
        clarifying_dimension = decision.clarifying_dimension

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=decision.assistant_message,
        experiment_id=experiment.id,
        turn_kind=turn_kind,
        clarifying_dimension=clarifying_dimension,
    )
    db.add(assistant_msg)
    await db.flush()

    pipeline_dispatched = False
    dispatched_at: datetime | None = None
    user_facing_error: UserFacingError | None = None
    research_error_detail = experiment.research_error_detail

    if decision.decision == "finalize":
        settings = get_settings()
        if rollout.should_auto_fire(experiment.id, settings.auto_fire_chat_enabled):
            try:
                await dispatch_service.transition_to_researching_and_dispatch(
                    db,
                    experiment,
                    DispatchTrigger.AUTO_FIRE,
                    dispatcher,
                )
                pipeline_dispatched = True
                dispatched_at = datetime.now(UTC)
            except DispatchError as exc:
                detail = _sanitize_error_detail("dispatch", exc)
                experiment.status = ExperimentStatus.RESEARCH_FAILED
                experiment.research_error_detail = detail
                research_error_detail = detail
                await db.commit()
                user_facing_error = translate_engineer_error(
                    "DispatchError",
                    detail,
                    experiment.status,
                )
                result = ChatTurnResult(
                    thread_id=thread.id,
                    message_id=assistant_msg.id,
                    experiment_id=experiment.id,
                    assistant_message=decision.assistant_message,
                    turn_kind=turn_kind,
                    clarifying_dimension=clarifying_dimension,
                    pipeline_dispatched=False,
                    dispatched_at=None,
                    experiment_status=experiment.status,
                    research_error_detail=research_error_detail,
                    user_facing_error=user_facing_error,
                )
                await _store_idempotency(db, thread.id, idempotency_key, result)
                await db.commit()
                return result
        else:
            experiment.status = ExperimentStatus.REFINED
            await db.commit()
            _logger.info(
                "auto_fire_gated",
                experiment_id=str(experiment.id),
                mode=settings.auto_fire_chat_enabled,
                would_have_fired=True,
            )
    else:
        await db.commit()

    result = ChatTurnResult(
        thread_id=thread.id,
        message_id=assistant_msg.id,
        experiment_id=experiment.id,
        assistant_message=decision.assistant_message,
        turn_kind=turn_kind,
        clarifying_dimension=clarifying_dimension,
        pipeline_dispatched=pipeline_dispatched,
        dispatched_at=dispatched_at,
        experiment_status=experiment.status,
        research_error_detail=research_error_detail,
        user_facing_error=user_facing_error,
    )
    await _store_idempotency(db, thread.id, idempotency_key, result)
    await db.commit()
    return result
