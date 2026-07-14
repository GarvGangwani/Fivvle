"""Refine session endpoints — finalize, reset, opener (canvas Refine deep-dive)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.models.chat_message import ChatMessage
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_session
from app.dispatchers.dependencies import get_dispatcher_dep
from app.dispatchers.protocol import ResearchDispatcher
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.routers.experiments import (
    GetExperimentDetailResponse,
    _build_experiment_detail_response,
)
from app.schemas.chat import ChatMessageItem, ChatTurnResponse
from app.services.chat_service import (
    ChatAuthorizationError,
    ChatMessageRetryError,
    retry_assistant_message,
)
from app.services.chat_tree_service import (
    enrich_messages_with_sibling_info,
    get_leaf_of_branch,
    get_siblings,
    set_active_leaf,
)
from app.services.refine_session_service import (
    RefineSessionError,
    finalize_refinement,
    get_owned_experiment,
    reset_refinement_session,
)
from app.services.refiner_opener_service import generate_and_persist_opener

router = APIRouter(tags=["experiment-refine"])


async def _reload_for_detail(
    db: AsyncSession,
    experiment_id: UUID,
    user_id: UUID,
) -> Experiment:
    result = await db.execute(
        select(Experiment)
        .options(
            selectinload(Experiment.validation_report),
            selectinload(Experiment.landing_page),
            selectinload(Experiment.insight_report),
        )
        .where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    return experiment


async def _message_items_with_siblings(
    db: AsyncSession,
    messages: list[ChatMessage],
) -> list[ChatMessageItem]:
    enriched = await enrich_messages_with_sibling_info(db, messages)
    return [
        ChatMessageItem.from_orm_message(
            msg,
            sibling_index=index,
            sibling_count=count,
        )
        for msg, index, count in enriched
    ]


@router.post(
    "/experiments/{experiment_id}/refine/finalize",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def finalize_refinement_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    """Marks refinement complete when refined_idea is set. Does not start research."""
    try:
        experiment = await get_owned_experiment(db, experiment_id, current_user)
        await finalize_refinement(db, experiment)
    except RefineSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from None

    experiment = await _reload_for_detail(db, experiment_id, current_user.id)
    return await _build_experiment_detail_response(db, experiment)


@router.delete(
    "/experiments/{experiment_id}/refine/session",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def reset_refinement_session_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    """Deletes refine chat messages; clears refined_idea if Evidence has not run."""
    try:
        experiment = await get_owned_experiment(db, experiment_id, current_user)
        await reset_refinement_session(db, experiment)
    except RefineSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from None

    experiment = await _reload_for_detail(db, experiment_id, current_user.id)
    return await _build_experiment_detail_response(db, experiment)


@router.post(
    "/experiments/{experiment_id}/refine/opener",
    response_model=ChatMessageItem,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_refine_opener_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageItem:
    """Generate the Refiner's proactive opening message.

    Idempotent: 400 if the chat thread already has any messages.
    """
    try:
        experiment = await get_owned_experiment(db, experiment_id, current_user)
        message = await generate_and_persist_opener(db, experiment, current_user)
    except RefineSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from None

    items = await _message_items_with_siblings(db, [message])
    return items[0]


@router.post(
    "/experiments/{experiment_id}/refine/messages/{message_id}/retry",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def retry_refine_assistant_message(
    request: Request,
    response: Response,
    experiment_id: UUID,
    message_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    dispatcher: Annotated[ResearchDispatcher, Depends(get_dispatcher_dep)],
) -> ChatTurnResponse:
    """Create a sibling assistant message on a new branch (keeps the original)."""
    try:
        result = await retry_assistant_message(
            db,
            current_user,
            experiment_id,
            message_id,
            dispatcher,
        )
        return ChatTurnResponse.from_result(result)
    except ChatAuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        ) from None
    except ChatMessageRetryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None


@router.get(
    "/experiments/{experiment_id}/refine/messages/{message_id}/siblings",
    response_model=list[ChatMessageItem],
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_message_siblings(
    request: Request,
    response: Response,
    experiment_id: UUID,
    message_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ChatMessageItem]:
    """Return sibling messages (same parent), ordered chronologically."""
    try:
        experiment = await get_owned_experiment(db, experiment_id, current_user)
    except RefineSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from None

    if experiment.thread_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Experiment has no chat thread",
        )

    msg = await db.get(ChatMessage, message_id)
    if msg is None or msg.thread_id != experiment.thread_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    siblings = await get_siblings(db, message_id)
    return await _message_items_with_siblings(db, siblings)


@router.post(
    "/experiments/{experiment_id}/refine/messages/{message_id}/set-active",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def set_active_message(
    request: Request,
    response: Response,
    experiment_id: UUID,
    message_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    """Switch the active branch to the leaf of the branch containing ``message_id``."""
    try:
        experiment = await get_owned_experiment(db, experiment_id, current_user)
    except RefineSessionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from None

    if experiment.thread_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Experiment has no chat thread",
        )

    msg = await db.get(ChatMessage, message_id)
    if msg is None or msg.thread_id != experiment.thread_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    try:
        leaf = await get_leaf_of_branch(db, message_id)
        await set_active_leaf(db, experiment.thread_id, leaf.id)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None

    experiment = await _reload_for_detail(db, experiment_id, current_user.id)
    return await _build_experiment_detail_response(db, experiment)
