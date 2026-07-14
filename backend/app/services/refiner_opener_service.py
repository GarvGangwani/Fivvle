"""Generate the Refiner's proactive opening message for an empty Refine thread."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.enums import ChatRole
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.experiment_attachment import ExperimentAttachment
from app.db.models.user import User
from app.llm import client as llm_client
from app.llm.prompts.refiner_opener import (
    PROMPT_NAME,
    SYSTEM,
    build_opener_user_prompt,
)
from app.logging_config import get_logger
from app.services.refine_session_service import RefineSessionError

_logger = get_logger(__name__)

_MAX_ATTACHMENT_TITLES = 5


async def _list_attachment_titles(
    db: AsyncSession,
    experiment_id: Experiment.id,  # type: ignore[valid-type]
) -> list[str]:
    result = await db.execute(
        select(ExperimentAttachment.title)
        .where(ExperimentAttachment.experiment_id == experiment_id)
        .order_by(ExperimentAttachment.created_at.asc())
        .limit(_MAX_ATTACHMENT_TITLES)
    )
    return [str(title) for title in result.scalars().all() if title]


async def _ensure_thread(
    db: AsyncSession,
    experiment: Experiment,
    user: User,
) -> ChatThread:
    if experiment.thread_id is not None:
        result = await db.execute(
            select(ChatThread).where(ChatThread.id == experiment.thread_id)
        )
        thread = result.scalar_one_or_none()
        if thread is None or thread.user_id != user.id:
            raise RefineSessionError("Chat thread not found", status_code=404)
        return thread

    thread = ChatThread(user_id=user.id, title="Refine")
    db.add(thread)
    await db.flush()
    experiment.thread_id = thread.id
    return thread


async def _message_count(db: AsyncSession, thread_id: Experiment.id) -> int:  # type: ignore[valid-type]
    result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
    )
    return int(result.scalar_one())


async def generate_and_persist_opener(
    db: AsyncSession,
    experiment: Experiment,
    user: User,
) -> ChatMessage:
    """Create the Refiner opener as the first assistant message.

    Idempotent: raises RefineSessionError(400) if the thread already has messages.
    """
    raw_idea = (experiment.raw_idea or "").strip()
    if not raw_idea:
        raise RefineSessionError(
            "Save your idea in Spark first before starting Refine.",
            status_code=400,
        )

    thread = await _ensure_thread(db, experiment, user)
    existing = await _message_count(db, thread.id)
    if existing > 0:
        raise RefineSessionError(
            "Chat thread already has messages. Opener already generated.",
            status_code=400,
        )

    attachment_titles = await _list_attachment_titles(db, experiment.id)
    settings = get_settings()
    user_prompt = build_opener_user_prompt(
        raw_idea=raw_idea,
        attachment_titles=attachment_titles,
    )

    result = await llm_client.complete(
        db,
        provider=settings.refinement_provider,  # type: ignore[arg-type]
        model=settings.refinement_model,
        prompt_name=PROMPT_NAME,
        system=SYSTEM,
        user=user_prompt,
        max_tokens=500,
        temperature=0.7,
        experiment_id=experiment.id,
        phase="refiner_opener",
    )
    opener_text = result.text.strip()
    if not opener_text:
        raise RefineSessionError(
            "Could not generate opener. Try sending a message instead.",
            status_code=502,
        )

    message = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content=opener_text,
        experiment_id=experiment.id,
        turn_kind=None,
        clarifying_questions=None,
        parent_message_id=None,
    )
    db.add(message)
    await db.flush()
    thread.active_leaf_message_id = message.id
    await db.commit()
    await db.refresh(message)

    _logger.info(
        "refiner_opener_generated",
        experiment_id=str(experiment.id),
        message_id=str(message.id),
    )
    return message
