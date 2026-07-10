"""Experiment canvas layout endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.experiment import Experiment
from app.db.models.experiment_canvas_layout import ExperimentCanvasLayout
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.experiment_canvas import CanvasLayoutIn, CanvasLayoutOut

router = APIRouter(tags=["canvas-layout"])

DEFAULT_POSITIONS = {
    "refine": {"x": 475, "y": -155},
    "evidence": {"x": 295, "y": 405},
    "launch": {"x": -295, "y": 405},
    "signal": {"x": -475, "y": -155},
    "resources": {"x": 0, "y": -500},
}


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


@router.get("/experiments/{experiment_id}/canvas-layout", response_model=CanvasLayoutOut)
async def get_layout(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CanvasLayoutOut:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentCanvasLayout).where(
            ExperimentCanvasLayout.experiment_id == experiment_id,
            ExperimentCanvasLayout.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return CanvasLayoutOut(
            experiment_id=str(experiment_id),
            user_id=str(current_user.id),
            node_positions=DEFAULT_POSITIONS,  # type: ignore[arg-type]
            updated_at=datetime.now(timezone.utc),
        )
    return CanvasLayoutOut(
        experiment_id=str(row.experiment_id),
        user_id=str(row.user_id),
        node_positions=row.node_positions,  # type: ignore[arg-type]
        updated_at=row.updated_at,
    )


@router.put("/experiments/{experiment_id}/canvas-layout", response_model=CanvasLayoutOut)
async def upsert_layout(
    experiment_id: UUID,
    payload: CanvasLayoutIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CanvasLayoutOut:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentCanvasLayout).where(
            ExperimentCanvasLayout.experiment_id == experiment_id,
            ExperimentCanvasLayout.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = ExperimentCanvasLayout(
            experiment_id=experiment_id,
            user_id=current_user.id,
            node_positions={k: v.model_dump() for k, v in payload.node_positions.items()},
        )
        db.add(row)
        await db.flush()
    else:
        row.node_positions = {k: v.model_dump() for k, v in payload.node_positions.items()}
    await db.refresh(row)
    return CanvasLayoutOut(
        experiment_id=str(row.experiment_id),
        user_id=str(row.user_id),
        node_positions=row.node_positions,  # type: ignore[arg-type]
        updated_at=row.updated_at,
    )
