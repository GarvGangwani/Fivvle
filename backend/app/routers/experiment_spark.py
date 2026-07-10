"""Spark version save / list endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.spark_version import SparkSaveIn, SparkVersionOut
from app.services.spark_version_service import list_spark_versions, save_spark_version

router = APIRouter(tags=["experiment-spark"])


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
    "/experiments/{experiment_id}/spark/save",
    response_model=SparkVersionOut,
)
async def save_spark_version_endpoint(
    experiment_id: UUID,
    payload: SparkSaveIn,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SparkVersionOut:
    """Create a new Spark version. Increments version_number automatically."""
    experiment = await _get_owned_experiment(db, experiment_id, current_user.id)
    try:
        row = await save_spark_version(
            db,
            experiment=experiment,
            user_id=current_user.id,
            raw_idea=payload.raw_idea,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return SparkVersionOut.model_validate(row)


@router.get(
    "/experiments/{experiment_id}/spark/versions",
    response_model=list[SparkVersionOut],
)
async def list_spark_versions_endpoint(
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SparkVersionOut]:
    """Returns all Spark versions for this experiment, newest first."""
    await _get_owned_experiment(db, experiment_id, current_user.id)
    rows = await list_spark_versions(db, experiment_id)
    return [SparkVersionOut.model_validate(row) for row in rows]
