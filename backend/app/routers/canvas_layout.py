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
    "spark": {"x": -250, "y": -430},
    "refine": {"x": 250, "y": -430},
    "evidence": {"x": 500, "y": 0},
    "launch": {"x": 250, "y": 430},
    "signal": {"x": -250, "y": 430},
    "resources": {"x": -500, "y": 0},
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


def _to_out(row: ExperimentCanvasLayout, *, merge_defaults: bool = False) -> CanvasLayoutOut:
    positions = row.node_positions or {}
    if merge_defaults:
        positions = {**DEFAULT_POSITIONS, **positions}
    return CanvasLayoutOut(
        experiment_id=str(row.experiment_id),
        user_id=str(row.user_id),
        node_positions=positions,  # type: ignore[arg-type]
        viewport_x=row.viewport_x,
        viewport_y=row.viewport_y,
        viewport_zoom=row.viewport_zoom,
        updated_at=row.updated_at,
    )


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
            viewport_x=None,
            viewport_y=None,
            viewport_zoom=None,
            updated_at=datetime.now(timezone.utc),
        )
    # Merge defaults so older pentagon layouts pick up the new spark node.
    return _to_out(row, merge_defaults=True)


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
    fields_set = payload.model_fields_set
    now = datetime.now(timezone.utc)

    if row is None:
        row = ExperimentCanvasLayout(
            experiment_id=experiment_id,
            user_id=current_user.id,
            node_positions={
                k: v.model_dump() for k, v in payload.node_positions.items()
            },
            viewport_x=payload.viewport_x if "viewport_x" in fields_set else None,
            viewport_y=payload.viewport_y if "viewport_y" in fields_set else None,
            viewport_zoom=(
                payload.viewport_zoom if "viewport_zoom" in fields_set else None
            ),
            updated_at=now,
        )
        db.add(row)
        await db.flush()
    else:
        row.node_positions = {
            k: v.model_dump() for k, v in payload.node_positions.items()
        }
        # Explicit null clears saved viewport (Reset Layout); omitted fields preserve.
        if "viewport_x" in fields_set:
            row.viewport_x = payload.viewport_x
        if "viewport_y" in fields_set:
            row.viewport_y = payload.viewport_y
        if "viewport_zoom" in fields_set:
            row.viewport_zoom = payload.viewport_zoom
        row.updated_at = now
        await db.flush()

    await db.refresh(row)
    return _to_out(row)
