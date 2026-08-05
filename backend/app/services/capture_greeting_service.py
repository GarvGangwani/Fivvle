"""Capture-flow greeting for uncaptured experiments (universal chat rail)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.logging_config import get_logger

_logger = get_logger(__name__)


class CaptureGreetingError(Exception):
    """Domain error for capture greeting seeding."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def build_capture_greeting_text(*, project_name: str | None) -> str:
    """Warm first-turn copy. Experiment name always exists for name-only create."""
    name = (project_name or "").strip()
    if name:
        return (
            f"{name} — sounds interesting. Tell me exactly what {name} is, "
            "in as much detail as you can — and drop in any files you have "
            "(logo, research, sketches)."
        )
    return (
        "Let's start with your idea — tell me what you're building, in as much "
        "detail as you can, and drop in any files you have."
    )


async def _resolve_universal_thread(
    db: AsyncSession,
    *,
    experiment: Experiment,
    user_id: UUID,
) -> ChatThread:
    if experiment.universal_thread_id is not None:
        thread = await db.get(ChatThread, experiment.universal_thread_id)
        if thread is not None and thread.user_id == user_id:
            return thread
    thread = ChatThread(user_id=user_id, title="Universal")
    db.add(thread)
    await db.flush()
    experiment.universal_thread_id = thread.id
    return thread


async def _thread_message_count(db: AsyncSession, thread_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
    )
    return int(result.scalar_one())


async def ensure_capture_greeting(
    db: AsyncSession,
    *,
    experiment: Experiment,
    user: User,
) -> tuple[ChatMessage, bool]:
    """Idempotently seed the capture greeting as the first assistant message.

    Returns (message, created). created=False when the greeting already existed
    or the thread already has messages.
    """
    if experiment.user_id != user.id:
        raise CaptureGreetingError("Experiment not found", status_code=404)
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise CaptureGreetingError(
            "Chat is not available for archived experiments",
            status_code=409,
        )
    if experiment.original_idea is not None:
        raise CaptureGreetingError(
            "Original idea already captured",
            status_code=409,
        )

    thread = await _resolve_universal_thread(
        db, experiment=experiment, user_id=user.id
    )
    count = await _thread_message_count(db, thread.id)
    if count > 0:
        # Return the first assistant message on the active branch if present.
        result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.thread_id == thread.id,
                ChatMessage.role == ChatRole.ASSISTANT,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing, False
        raise CaptureGreetingError(
            "Chat thread already has messages",
            status_code=400,
        )

    text = build_capture_greeting_text(project_name=experiment.name)
    assistant = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=text,
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=None,
        metadata_json={"capture_greeting": True},
    )
    db.add(assistant)
    await db.flush()
    thread.active_leaf_message_id = assistant.id
    await db.commit()
    await db.refresh(assistant)

    _logger.info(
        "capture_greeting_seeded",
        experiment_id=str(experiment.id),
        message_id=str(assistant.id),
    )
    return assistant, True


async def stream_capture_greeting_tokens(
    text: str,
    *,
    chunk_size: int = 12,
) -> AsyncGenerator[str, None]:
    """Yield greeting text in small chunks for SSE token UX (no LLM)."""
    if not text:
        return
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
