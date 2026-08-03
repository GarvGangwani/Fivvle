"""Chat orchestration — deep research refinement turns and plain chat (planning §9).

HTTP routing lives in Step 5b; this module owns thread/experiment lifecycle,
refinement turns, dispatch on finalize, and plain-chat replies.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
import app.services.refinement_service as refinement_service
from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.refinement_idempotency import RefinementIdempotency
from app.db.models.user import User
from app.dispatchers.protocol import ResearchDispatcher
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
from app.schemas.refinement import ClarifyingQuestion
from app.services.chat_attachment_service import (
    build_message_with_attachment_context,
    resolve_chat_attachments,
)
from app.services.chat_discussion_context import build_experiment_discussion_context
from app.services.chat_tree_service import (
    get_active_branch,
    get_branch_up_to,
    history_tuples_from_branch,
    set_active_leaf,
)
from app.services.error_translation import UserFacingError, translate_engineer_error
from app.services.experiment_service import InvalidExperimentState
from app.utils.experiment_naming import normalize_experiment_name

_logger = get_logger(__name__)


@dataclass(frozen=True)
class UserMessageMeta:
    """Optional MCQ answer metadata stored on the user ChatMessage row."""

    selected_option_indices: tuple[int, ...] | None = None
    custom_added_text: str | None = None
    answered_question_from_message_id: UUID | None = None


def build_user_message_metadata(
    *,
    selected_option_indices: list[int] | None = None,
    custom_added_text: str | None = None,
    answered_question_from_message_id: UUID | None = None,
) -> dict[str, Any] | None:
    meta: dict[str, Any] = {}
    if selected_option_indices is not None:
        meta["selected_option_indices"] = list(selected_option_indices)
    if custom_added_text and custom_added_text.strip():
        meta["custom_added_text"] = custom_added_text.strip()
    if answered_question_from_message_id is not None:
        meta["answered_question_from_message_id"] = str(
            answered_question_from_message_id
        )
    return meta or None


_IN_FLIGHT_REFINING_WINDOW = timedelta(minutes=30)
_MAX_ERROR_DETAIL_LEN = 500
_THREAD_TITLE_MAX_LEN = 40

# Statuses that may reopen into REFINING without clearing refined_idea / downstream
# artifacts. SPARK uses a separate begin path. Mid-research, generating, and
# ARCHIVED remain blocked by the != REFINING guard below.
_REFINEMENT_REOPEN_STATUSES = frozenset(
    {
        ExperimentStatus.REFINED,
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.RESEARCH_FAILED,
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
    }
)

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


class ChatMessageEditError(Exception):
    """Raised when the edit target is missing or not a user message."""


@dataclass(frozen=True)
class ChatEditTurnResult:
    thread_id: UUID
    edited_message_id: UUID
    message_id: UUID
    experiment_id: UUID | None
    assistant_message: str
    turn_kind: ChatTurnKind
    clarifying_dimension: str | None
    clarifying_questions: tuple[ClarifyingQuestion, ...]
    pipeline_dispatched: bool
    dispatched_at: datetime | None
    experiment_status: ExperimentStatus | None
    research_error_detail: str | None
    user_facing_error: UserFacingError | None
    messages: list[ChatMessage]


@dataclass(frozen=True)
class ChatTurnResult:
    thread_id: UUID
    message_id: UUID
    experiment_id: UUID | None
    assistant_message: str
    turn_kind: ChatTurnKind
    clarifying_dimension: str | None
    clarifying_questions: tuple[ClarifyingQuestion, ...]
    pipeline_dispatched: bool
    dispatched_at: datetime | None
    experiment_status: ExperimentStatus | None
    research_error_detail: str | None
    user_facing_error: UserFacingError | None
    refinement_count: int | None = None

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
            "clarifying_questions": [q.model_dump() for q in self.clarifying_questions],
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
            "refinement_count": self.refinement_count,
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

        cq_raw = data.get("clarifying_questions") or []
        clarifying_questions = tuple(
            ClarifyingQuestion.model_validate(item) for item in cq_raw
        )

        return cls(
            thread_id=UUID(str(data["thread_id"])),
            message_id=UUID(str(data["message_id"])),
            experiment_id=experiment_id,
            assistant_message=str(data["assistant_message"]),
            turn_kind=ChatTurnKind(str(data["turn_kind"])),
            clarifying_dimension=data.get("clarifying_dimension"),
            clarifying_questions=clarifying_questions,
            pipeline_dispatched=bool(data["pipeline_dispatched"]),
            dispatched_at=dispatched_at,
            experiment_status=experiment_status,
            research_error_detail=data.get("research_error_detail"),
            user_facing_error=user_facing_error,
            refinement_count=(
                int(data["refinement_count"])
                if data.get("refinement_count") is not None
                else None
            ),
        )


def _questions_to_json(
    questions: tuple[ClarifyingQuestion, ...] | list[ClarifyingQuestion],
) -> list[dict[str, Any]] | None:
    if not questions:
        return None
    return [q.model_dump() for q in questions]


def _questions_tuple(
    questions: list[ClarifyingQuestion],
) -> tuple[ClarifyingQuestion, ...]:
    return tuple(questions)


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
    """Active-branch history for deep-research / discussion turns."""
    branch = await get_active_branch(db, thread_id)
    return history_tuples_from_branch(
        branch,
        exclude_system_kinds=_SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY,
    )


async def _load_history_before_message(
    db: AsyncSession,
    thread_id: UUID,
    before: ChatMessage,
    *,
    plain_chat_only: bool,
) -> list[tuple[str, str]]:
    """Ancestor chain of ``before`` via parent_message_id (excludes ``before``)."""
    del thread_id  # tree walk is parent-linked; thread scoped by message ownership
    if before.parent_message_id is None:
        ancestors: list[ChatMessage] = []
    else:
        ancestors = await get_branch_up_to(db, before.parent_message_id)
    return history_tuples_from_branch(
        ancestors,
        exclude_system_kinds=_SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY,
        plain_chat_only=plain_chat_only,
        plain_chat_kinds=_PLAIN_CHAT_HISTORY_TURN_KINDS,
    )


async def _list_thread_messages_after_edit(
    db: AsyncSession,
    thread_id: UUID,
) -> list[ChatMessage]:
    """Active branch after edit/retry (excludes system pipeline turns)."""
    branch = await get_active_branch(db, thread_id)
    return [
        row
        for row in branch
        if row.turn_kind not in _SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY
    ]


async def _load_plain_chat_history(
    db: AsyncSession,
    thread_id: UUID,
) -> list[tuple[str, str]]:
    branch = await get_active_branch(db, thread_id)
    return history_tuples_from_branch(
        branch,
        plain_chat_only=True,
        plain_chat_kinds=_PLAIN_CHAT_HISTORY_TURN_KINDS,
    )


async def _append_user_message(
    db: AsyncSession,
    *,
    thread: ChatThread,
    content: str,
    experiment_id: UUID | None,
    user_message_metadata: dict[str, Any] | None,
) -> ChatMessage:
    """Create a user message as a child of the current active leaf."""
    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=content,
        experiment_id=experiment_id,
        turn_kind=None,
        metadata_json=user_message_metadata,
        parent_message_id=thread.active_leaf_message_id,
    )
    db.add(user_msg)
    await db.flush()
    return user_msg


async def _append_assistant_and_activate(
    db: AsyncSession,
    *,
    thread: ChatThread,
    parent_user: ChatMessage,
    content: str,
    experiment_id: UUID | None,
    turn_kind: ChatTurnKind,
    clarifying_dimension: str | None = None,
    clarifying_questions: list | None = None,
) -> ChatMessage:
    """Create an assistant child of ``parent_user`` and set it as the active leaf."""
    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=content,
        experiment_id=experiment_id,
        turn_kind=turn_kind,
        clarifying_dimension=clarifying_dimension,
        clarifying_questions=clarifying_questions,
        parent_message_id=parent_user.id,
    )
    db.add(assistant_msg)
    await db.flush()
    await set_active_leaf(db, thread.id, assistant_msg.id)
    return assistant_msg


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
    """Return the active branch in chronological order (ownership enforced)."""
    thread = await _resolve_thread(db, user, thread_id)
    branch = await get_active_branch(db, thread.id)
    return [
        row
        for row in branch
        if row.turn_kind not in _SYSTEM_TURN_KINDS_EXCLUDED_FROM_DR_HISTORY
    ]


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
    name: str | None = None,
) -> Experiment:
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
        if experiment.status == ExperimentStatus.SPARK:
            from app.services.experiment_service import begin_refinement_from_spark
            from app.services.spark_version_service import stamp_chat_thread_spark_version

            try:
                experiment = await begin_refinement_from_spark(db, experiment)
            except ValueError as exc:
                raise InvalidExperimentState(str(exc)) from exc
            if experiment.thread_id is None:
                experiment.thread_id = thread.id
                await db.flush()
            await stamp_chat_thread_spark_version(db, thread, experiment.id)
            return experiment
        if experiment.status in _REFINEMENT_REOPEN_STATUSES:
            # Reopen Refine without clearing refined_idea or downstream artifacts.
            # Stable idea stays until explicit re-finalize; artifacts go stale via
            # refined_idea_version (not deleted here).
            experiment.status = ExperimentStatus.REFINING
            await db.flush()
            _logger.info(
                "refinement_reopened",
                experiment_id=str(experiment.id),
                thread_id=str(thread.id),
            )
            return experiment
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
        name=normalize_experiment_name(name),
        status=ExperimentStatus.REFINING,
        refinement_count=0,
        refinement_started_at=datetime.now(UTC),
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


def _build_user_display_content(
    message: str,
    filenames: list[str],
) -> str:
    display = message.strip()
    if filenames:
        names = ", ".join(filenames)
        if display:
            return f"{display}\n\n📎 {names}"
        return f"📎 {names}"
    return display


async def _prepare_turn_messages(
    db: AsyncSession,
    *,
    user: User,
    message: str,
    attachment_ids: list[UUID],
) -> tuple[str, str]:
    """Return (display_content for DB/UI, llm_message for model calls)."""
    clean_message = _sanitize_user_message(message).strip()
    attachments = await resolve_chat_attachments(
        db,
        user=user,
        attachment_ids=attachment_ids,
    )
    filenames = [item.filename for item in attachments]
    display = _build_user_display_content(clean_message, filenames)
    llm_message = build_message_with_attachment_context(clean_message, attachments)
    if not display:
        raise ValueError("message or attachment_ids is required")
    return display, llm_message


async def handle_turn(
    db: AsyncSession,
    user: User,
    message: str,
    deep_research: bool,
    thread_id: UUID | None,
    experiment_id: UUID | None,
    idempotency_key: str | None,
    dispatcher: ResearchDispatcher,
    name: str | None = None,
    attachment_ids: list[UUID] | None = None,
    user_message_metadata: dict[str, Any] | None = None,
    *,
    prompt_name: str | None = None,
    system_prompt: str | None = None,
    user_prompt_builder: Callable[..., str] | None = None,
) -> ChatTurnResult:
    """Top-level entry. Handles both DR and plain-chat paths."""
    message = _sanitize_user_message(message)
    attachment_ids = attachment_ids or []
    if deep_research:
        return await _handle_deep_research_turn(
            db,
            user=user,
            message=message,
            attachment_ids=attachment_ids,
            thread_id=thread_id,
            experiment_id=experiment_id,
            idempotency_key=idempotency_key,
            dispatcher=dispatcher,
            name=name,
            user_message_metadata=user_message_metadata,
            prompt_name=prompt_name,
            system_prompt=system_prompt,
            user_prompt_builder=user_prompt_builder,
        )
    return await _handle_plain_chat_turn(
        db,
        user=user,
        message=message,
        attachment_ids=attachment_ids,
        thread_id=thread_id,
        experiment_id=experiment_id,
        user_message_metadata=user_message_metadata,
    )


async def _handle_plain_chat_turn(
    db: AsyncSession,
    *,
    user: User,
    message: str,
    attachment_ids: list[UUID],
    thread_id: UUID | None,
    experiment_id: UUID | None,
    existing_user_message: ChatMessage | None = None,
    user_message_metadata: dict[str, Any] | None = None,
) -> ChatTurnResult:
    title_seed = message.strip() or ("Shared attachments" if attachment_ids else "")
    display_content, llm_message = await _prepare_turn_messages(
        db,
        user=user,
        message=message,
        attachment_ids=attachment_ids,
    )
    thread = await _resolve_thread(
        db,
        user,
        thread_id,
        first_message_for_title=title_seed if thread_id is None else None,
    )

    experiment = await _resolve_experiment_for_plain_chat(
        db, user, thread, experiment_id
    )
    if _uses_discussion_mode(experiment):
        assert experiment is not None
        return await _handle_discussion_turn(
            db,
            display_content=display_content,
            llm_message=llm_message,
            thread=thread,
            experiment=experiment,
            existing_user_message=existing_user_message,
            user_message_metadata=user_message_metadata,
        )

    if existing_user_message is not None:
        chat_history = await _load_history_before_message(
            db, thread.id, existing_user_message, plain_chat_only=True
        )
        user_msg = existing_user_message
    else:
        chat_history = await _load_plain_chat_history(db, thread.id)
        user_msg = await _append_user_message(
            db,
            thread=thread,
            content=display_content,
            experiment_id=experiment.id if experiment is not None else None,
            user_message_metadata=user_message_metadata,
        )

    assistant_text = await reply_plain(
        db,
        chat_history,
        llm_message,
        experiment_id=experiment.id if experiment is not None else None,
    )

    assistant_msg = await _append_assistant_and_activate(
        db,
        thread=thread,
        parent_user=user_msg,
        content=assistant_text,
        experiment_id=experiment.id if experiment is not None else None,
        turn_kind=ChatTurnKind.NORMAL_CHAT,
    )
    await db.commit()

    return ChatTurnResult(
        thread_id=thread.id,
        message_id=assistant_msg.id,
        experiment_id=experiment.id if experiment is not None else None,
        assistant_message=assistant_text,
        turn_kind=ChatTurnKind.NORMAL_CHAT,
        clarifying_dimension=None,
        clarifying_questions=(),
        pipeline_dispatched=False,
        dispatched_at=None,
        experiment_status=experiment.status if experiment is not None else None,
        research_error_detail=(
            experiment.research_error_detail if experiment is not None else None
        ),
        user_facing_error=None,
        refinement_count=(
            experiment.refinement_count if experiment is not None else None
        ),
    )


async def _handle_discussion_turn(
    db: AsyncSession,
    *,
    display_content: str,
    llm_message: str,
    thread: ChatThread,
    experiment: Experiment,
    existing_user_message: ChatMessage | None = None,
    user_message_metadata: dict[str, Any] | None = None,
) -> ChatTurnResult:
    if existing_user_message is not None:
        chat_history = await _load_history_before_message(
            db, thread.id, existing_user_message, plain_chat_only=False
        )
        user_msg = existing_user_message
    else:
        chat_history = await _load_dr_chat_history(db, thread.id)
        user_msg = await _append_user_message(
            db,
            thread=thread,
            content=display_content,
            experiment_id=experiment.id,
            user_message_metadata=user_message_metadata,
        )

    assistant_text = await reply_discussion(db, experiment, chat_history, llm_message)

    assistant_msg = await _append_assistant_and_activate(
        db,
        thread=thread,
        parent_user=user_msg,
        content=assistant_text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.DISCUSS,
    )
    await db.commit()

    return ChatTurnResult(
        thread_id=thread.id,
        message_id=assistant_msg.id,
        experiment_id=experiment.id,
        assistant_message=assistant_text,
        turn_kind=ChatTurnKind.DISCUSS,
        clarifying_dimension=None,
        clarifying_questions=(),
        pipeline_dispatched=False,
        dispatched_at=None,
        experiment_status=experiment.status,
        research_error_detail=experiment.research_error_detail,
        user_facing_error=None,
        refinement_count=experiment.refinement_count,
    )


async def _handle_deep_research_turn(
    db: AsyncSession,
    *,
    user: User,
    message: str,
    attachment_ids: list[UUID],
    thread_id: UUID | None,
    experiment_id: UUID | None,
    idempotency_key: str | None,
    dispatcher: ResearchDispatcher,
    name: str | None = None,
    existing_user_message: ChatMessage | None = None,
    user_message_metadata: dict[str, Any] | None = None,
    bump_refinement_count: bool = True,
    prompt_name: str | None = None,
    system_prompt: str | None = None,
    user_prompt_builder: Callable[..., str] | None = None,
) -> ChatTurnResult:
    if idempotency_key is None:
        raise ValueError("idempotency_key required for deep_research=true")

    title_seed = message.strip() or ("Shared attachments" if attachment_ids else "")
    thread = await _resolve_thread(
        db,
        user,
        thread_id,
        first_message_for_title=title_seed if thread_id is None else None,
    )

    if existing_user_message is None:
        cached = await _fetch_idempotent_result(db, thread.id, idempotency_key)
        if cached is not None:
            return cached

    display_content, llm_message = await _prepare_turn_messages(
        db,
        user=user,
        message=message,
        attachment_ids=attachment_ids,
    )

    experiment = await _resolve_refinement_experiment(
        db, user, thread, display_content, experiment_id, name
    )

    if existing_user_message is not None:
        chat_history = await _load_history_before_message(
            db, thread.id, existing_user_message, plain_chat_only=False
        )
        user_msg = existing_user_message
    else:
        chat_history = await _load_dr_chat_history(db, thread.id)
        user_msg = await _append_user_message(
            db,
            thread=thread,
            content=display_content,
            experiment_id=experiment.id,
            user_message_metadata=user_message_metadata,
        )

    try:
        decision = await refinement_service.run_turn(
            db,
            experiment,
            chat_history,
            llm_message,
            bump_refinement_count=bump_refinement_count,
            prompt_name=prompt_name,
            system_prompt=system_prompt,
            user_prompt_builder=user_prompt_builder,
        )
    except Exception as exc:
        user_error = translate_engineer_error(
            type(exc).__name__,
            _sanitize_error_detail("refinement", exc),
            experiment.status,
        )
        assistant_msg = await _append_assistant_and_activate(
            db,
            thread=thread,
            parent_user=user_msg,
            content=user_error.message,
            experiment_id=experiment.id,
            turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
        )
        await db.commit()
        return ChatTurnResult(
            thread_id=thread.id,
            message_id=assistant_msg.id,
            experiment_id=experiment.id,
            assistant_message=user_error.message,
            turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
            clarifying_dimension=None,
            clarifying_questions=(),
            pipeline_dispatched=False,
            dispatched_at=None,
            experiment_status=experiment.status,
            research_error_detail=experiment.research_error_detail,
            user_facing_error=user_error,
            refinement_count=experiment.refinement_count,
        )

    turn_kind = ChatTurnKind.REFINEMENT_CLARIFY
    clarifying_dimension = decision.clarifying_dimension
    clarifying_questions_tuple = _questions_tuple(decision.clarifying_questions)

    assistant_msg = await _append_assistant_and_activate(
        db,
        thread=thread,
        parent_user=user_msg,
        content=decision.assistant_message,
        experiment_id=experiment.id,
        turn_kind=turn_kind,
        clarifying_dimension=clarifying_dimension,
        clarifying_questions=_questions_to_json(clarifying_questions_tuple),
    )

    pipeline_dispatched = False
    dispatched_at: datetime | None = None
    user_facing_error: UserFacingError | None = None
    research_error_detail = experiment.research_error_detail

    # User owns finalize — LLM turns never flip status to REFINED.
    await db.commit()

    result = ChatTurnResult(
        thread_id=thread.id,
        message_id=assistant_msg.id,
        experiment_id=experiment.id,
        assistant_message=decision.assistant_message,
        turn_kind=turn_kind,
        clarifying_dimension=clarifying_dimension,
        clarifying_questions=clarifying_questions_tuple,
        pipeline_dispatched=pipeline_dispatched,
        dispatched_at=dispatched_at,
        experiment_status=experiment.status,
        research_error_detail=research_error_detail,
        user_facing_error=user_facing_error,
        refinement_count=experiment.refinement_count,
    )
    await _store_idempotency(db, thread.id, idempotency_key, result)
    await db.commit()
    return result


async def handle_edit_turn(
    db: AsyncSession,
    user: User,
    thread_id: UUID,
    message_id: UUID,
    new_content: str,
    dispatcher: ResearchDispatcher,
) -> ChatEditTurnResult:
    """Fork a new user message sibling and regenerate the assistant response.

    Does not delete the original user message or its descendants.
    """
    new_content = _sanitize_user_message(new_content)
    if not new_content.strip():
        raise ValueError("new_content must not be empty")

    thread = await _resolve_thread(db, user, thread_id)

    result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.thread_id == thread.id,
        )
    )
    original_user = result.scalar_one_or_none()
    if original_user is None:
        raise ChatMessageEditError("Message not found in this thread")
    if original_user.role != ChatRole.USER:
        raise ChatMessageEditError("Only user messages can be edited")

    new_user = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content=new_content,
        experiment_id=original_user.experiment_id,
        turn_kind=None,
        metadata_json=None,
        parent_message_id=original_user.parent_message_id,
    )
    db.add(new_user)
    await db.flush()

    experiment = await _resolve_experiment_for_plain_chat(
        db,
        user,
        thread,
        original_user.experiment_id,
    )

    if experiment is not None and experiment.status in (
        ExperimentStatus.REFINING,
        ExperimentStatus.REFINED,
    ):
        turn_result = await _handle_deep_research_turn(
            db,
            user=user,
            message=new_content,
            attachment_ids=[],
            thread_id=thread.id,
            experiment_id=experiment.id,
            idempotency_key=str(uuid4()),
            dispatcher=dispatcher,
            existing_user_message=new_user,
            bump_refinement_count=False,
        )
    else:
        turn_result = await _handle_plain_chat_turn(
            db,
            user=user,
            message=new_content,
            attachment_ids=[],
            thread_id=thread.id,
            experiment_id=original_user.experiment_id,
            existing_user_message=new_user,
        )

    messages = await _list_thread_messages_after_edit(db, thread.id)

    return ChatEditTurnResult(
        thread_id=turn_result.thread_id,
        edited_message_id=new_user.id,
        message_id=turn_result.message_id,
        experiment_id=turn_result.experiment_id,
        assistant_message=turn_result.assistant_message,
        turn_kind=turn_result.turn_kind,
        clarifying_dimension=turn_result.clarifying_dimension,
        clarifying_questions=turn_result.clarifying_questions,
        pipeline_dispatched=turn_result.pipeline_dispatched,
        dispatched_at=turn_result.dispatched_at,
        experiment_status=turn_result.experiment_status,
        research_error_detail=turn_result.research_error_detail,
        user_facing_error=turn_result.user_facing_error,
        messages=messages,
    )


class ChatMessageRetryError(Exception):
    """Raised when an assistant message cannot be retried."""


async def retry_assistant_message(
    db: AsyncSession,
    user: User,
    experiment_id: UUID,
    message_id: UUID,
    dispatcher: ResearchDispatcher,
) -> ChatTurnResult:
    """Create a sibling assistant message (branch). Does not delete the original."""
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user.id:
        raise ChatAuthorizationError("Experiment not found or not owned by user")
    if experiment.thread_id is None:
        raise ChatMessageRetryError("Experiment has no chat thread")

    thread = await _resolve_thread(db, user, experiment.thread_id)

    msg_result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.thread_id == thread.id,
        )
    )
    target = msg_result.scalar_one_or_none()
    if target is None:
        raise ChatMessageRetryError("Message not found in this thread")
    if target.role != ChatRole.ASSISTANT:
        raise ChatMessageRetryError("Only assistant messages can be retried")
    if target.parent_message_id is None:
        raise ChatMessageRetryError("Cannot retry the first message of a thread")

    parent_user = await db.get(ChatMessage, target.parent_message_id)
    if parent_user is None or parent_user.role != ChatRole.USER:
        raise ChatMessageRetryError("Parent must be a user message")

    return await _handle_deep_research_turn(
        db,
        user=user,
        message=parent_user.content,
        attachment_ids=[],
        thread_id=thread.id,
        experiment_id=experiment.id,
        idempotency_key=str(uuid4()),
        dispatcher=dispatcher,
        existing_user_message=parent_user,
        bump_refinement_count=False,
    )
