"""Experiment activity endpoints and UI event ingestion."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.chat_message import ChatMessage
from app.db.models.experiment import Experiment
from app.db.models.experiment_event import ExperimentEvent
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.experiment_canvas import ActivityItem, EventCreateIn
from app.services.activity_service import (
    ALLOWED_EXPERIMENT_EVENT_TYPES,
    UI_TELEMETRY_EVENT_TYPES,
    merge_activity_items,
    summarize_experiment_event,
)

router = APIRouter(tags=["experiment-activity"])


async def _get_owned_experiment(
    db: AsyncSession,
    experiment_id: UUID,
    user_id: UUID,
) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post(
    "/experiments/{experiment_id}/events",
    response_model=ActivityItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_experiment_event(
    experiment_id: UUID,
    payload: EventCreateIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ActivityItem:
    await _get_owned_experiment(db, experiment_id, current_user.id)

    if payload.event_type in UI_TELEMETRY_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UI telemetry events are not recorded in the activity stream.",
        )
    if payload.event_type not in ALLOWED_EXPERIMENT_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported event type.",
        )

    event = ExperimentEvent(
        experiment_id=experiment_id,
        user_id=current_user.id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    item = summarize_experiment_event(event)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event could not be summarized for activity feed.",
        )
    return item


@router.get("/experiments/{experiment_id}/activity", response_model=list[ActivityItem])
async def get_activity(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(30, ge=1, le=100),
) -> list[ActivityItem]:
    await _get_owned_experiment(db, experiment_id, current_user.id)

    llm_rows = (
        await db.execute(
            select(LLMCall)
            .where(LLMCall.experiment_id == experiment_id)
            .order_by(LLMCall.called_at.desc(), LLMCall.id.desc())
            .limit(limit * 3)
        )
    ).scalars().all()
    chat_rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.experiment_id == experiment_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit * 3)
        )
    ).scalars().all()
    event_rows = (
        await db.execute(
            select(ExperimentEvent)
            .where(ExperimentEvent.experiment_id == experiment_id)
            .order_by(ExperimentEvent.occurred_at.desc(), ExperimentEvent.id.desc())
            .limit(limit * 3)
        )
    ).scalars().all()

    return merge_activity_items(
        llm_rows,
        chat_rows,
        event_rows,
        limit=limit,
    )
