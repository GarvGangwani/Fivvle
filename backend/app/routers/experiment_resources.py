"""Experiment resources CRUD endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.experiment import Experiment
from app.db.models.experiment_resource import ExperimentResource
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.experiment_canvas import ResourceCreateIn, ResourceOut, ResourcePatchIn

router = APIRouter(tags=["experiment-resources"])


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


@router.get("/experiments/{experiment_id}/resources", response_model=list[ResourceOut])
async def list_resources(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ResourceOut]:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentResource)
        .where(
            ExperimentResource.experiment_id == experiment_id,
            ExperimentResource.user_id == current_user.id,
        )
        .order_by(ExperimentResource.created_at.desc(), ExperimentResource.id.desc())
    )
    rows = result.scalars().all()
    return [ResourceOut.model_validate(row) for row in rows]


@router.post(
    "/experiments/{experiment_id}/resources",
    response_model=ResourceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_resource(
    experiment_id: UUID,
    payload: ResourceCreateIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResourceOut:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    row = ExperimentResource(
        experiment_id=experiment_id,
        user_id=current_user.id,
        title=payload.title.strip(),
        url=payload.url,
        note=payload.note,
        resource_type=payload.resource_type,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return ResourceOut.model_validate(row)


@router.patch(
    "/experiments/{experiment_id}/resources/{res_id}",
    response_model=ResourceOut,
)
async def patch_resource(
    experiment_id: UUID,
    res_id: UUID,
    payload: ResourcePatchIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResourceOut:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentResource).where(
            ExperimentResource.id == res_id,
            ExperimentResource.experiment_id == experiment_id,
            ExperimentResource.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is not None:
        updates["title"] = updates["title"].strip()
    for key, value in updates.items():
        setattr(row, key, value)
    await db.flush()
    await db.refresh(row)
    return ResourceOut.model_validate(row)


@router.delete(
    "/experiments/{experiment_id}/resources/{res_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_resource(
    experiment_id: UUID,
    res_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    result = await db.execute(
        select(ExperimentResource).where(
            ExperimentResource.id == res_id,
            ExperimentResource.experiment_id == experiment_id,
            ExperimentResource.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
