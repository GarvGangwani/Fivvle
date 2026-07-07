"""Experimental Landing Page Runtime V2 routes — isolated from V1 generator."""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_session, get_sessionmaker
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.landing_page_v2 import (
    GenerateLandingPageV2Request,
    GenerateLandingPageV2Response,
    LandingPageV2GenerationStatus,
)
from app.services.landing_page_v2_service import (
    MissingResearchData,
    assert_v2_generation_prerequisites,
    get_landing_page_v2_status,
    run_landing_page_v2_generation_task,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])
_logger = get_logger(__name__)

_v2_tasks: dict[UUID, asyncio.Task[None]] = {}


async def _get_owned_experiment(
    db: AsyncSession,
    experiment_id: UUID,
    user_id: UUID,
) -> Experiment:
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    return experiment


async def _dispatch_v2_generation(
    experiment_id: UUID,
    body: GenerateLandingPageV2Request,
    db: AsyncSession,
) -> GenerateLandingPageV2Response:
    try:
        await assert_v2_generation_prerequisites(db, experiment_id=experiment_id)
    except MissingResearchData as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    status_payload = await get_landing_page_v2_status(db, experiment_id=experiment_id)
    if status_payload.generation_status == "generating":
        existing = _v2_tasks.get(experiment_id)
        if existing is not None and not existing.done():
            return GenerateLandingPageV2Response(
                experiment_id=str(experiment_id),
                generation_status="generating",
            )

    try:
        sessionmaker = get_sessionmaker()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready",
        ) from exc

    task = asyncio.create_task(
        run_landing_page_v2_generation_task(
            experiment_id,
            sessionmaker,
            page_goal=body.page_goal,
            regeneration_hint=body.regeneration_hint,
        ),
        name=f"lp_v2_{experiment_id}",
    )
    _v2_tasks[experiment_id] = task

    def _cleanup(t: asyncio.Task[None]) -> None:
        if _v2_tasks.get(experiment_id) is t:
            _v2_tasks.pop(experiment_id, None)

    task.add_done_callback(_cleanup)

    return GenerateLandingPageV2Response(
        experiment_id=str(experiment_id),
        generation_status="generating",
    )


@router.get(
    "/{experiment_id}/landing-page-v2",
    response_model=LandingPageV2GenerationStatus,
)
@router.get(
    "/{experiment_id}/landing-page-runtime",
    response_model=LandingPageV2GenerationStatus,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_landing_page_v2(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageV2GenerationStatus:
    await _get_owned_experiment(db, experiment_id, current_user.id)
    return await get_landing_page_v2_status(db, experiment_id=experiment_id)


@router.post(
    "/{experiment_id}/landing-page-v2/generate",
    response_model=GenerateLandingPageV2Response,
    status_code=status.HTTP_202_ACCEPTED,
)
@router.post(
    "/{experiment_id}/landing-page-runtime/generate",
    response_model=GenerateLandingPageV2Response,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_landing_page_v2(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: GenerateLandingPageV2Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GenerateLandingPageV2Response:
    """Generate a runtime page spec from existing research. Does not affect V1."""
    await _get_owned_experiment(db, experiment_id, current_user.id)
    return await _dispatch_v2_generation(experiment_id, body, db)
