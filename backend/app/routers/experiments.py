"""Experiment router — POST /experiments, POST /experiments/{id}/refine,
POST /experiments/{id}/confirm, GET /experiments/{id}/research-status.

Per .cursorrules «API Design»: router functions are thin (5-15 lines each).
All domain logic lives in app.services.*.

Per AGENTS.md «Authentication and authorization»:
- Authentication: Depends(get_current_user) — verifies Firebase ID token, returns User.
- Authorization (ownership): checked SEPARATELY with an explicit comparison before any
  mutation. Ownership failure returns 404, not 403 — never reveal that the experiment
  exists for a different user.

Per AGENTS.md «Error handling»:
- LLM exceptions → 502 with generic message; full detail goes to structlog + Sentry only.
- Domain exceptions → 409 with specific but non-leaking message.
- ValueError (input) → 400.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_session
from app.dispatchers.dependencies import get_dispatcher_dep
from app.dispatchers.protocol import DispatchError, ResearchDispatcher
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.experiment import (
    ConfirmResearchResponse,
    CreateExperimentRequest,
    ExperimentResponse,
    RegenerateRefinementRequest,
    ResearchStatusResponse,
)
from app.services.experiment_service import (
    InvalidExperimentState,
    RefinementLimitExceeded,
    create_experiment_with_refinement,
    regenerate_refinement,
)
from app.services.research_phase_mapping import get_phase_label, get_phases_completed

_logger = get_logger(__name__)

# 30/min/user for the polling endpoint — per the spec.
_RESEARCH_STATUS_RATE_LIMIT = "30/minute"

router = APIRouter(prefix="/experiments", tags=["experiments"])



@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def create_experiment(
    request: Request,
    response: Response,
    body: CreateExperimentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Experiment:
    user_id = str(current_user.id)  # cache before try — avoids lazy-load on broken session
    try:
        return await create_experiment_with_refinement(db, current_user, body.raw_idea)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("experiment creation failed", error_type=type(exc).__name__, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Refinement failed, please try again",
        ) from exc


@router.post(
    "/{experiment_id}/refine",
    response_model=ExperimentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def refine_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: RegenerateRefinementRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    # 404 for not found AND wrong owner — never reveal existence to non-owners (AGENTS.md).
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    try:
        return await regenerate_refinement(db, experiment, body.feedback)
    except RefinementLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Regeneration limit reached for this experiment",
        ) from None
    except InvalidExperimentState:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment is not in a state that allows regeneration",
        ) from None
    except Exception as exc:
        _logger.error(
            "experiment regeneration failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Refinement failed, please try again",
        ) from exc


# ---------------------------------------------------------------------------
# POST /experiments/{id}/confirm — trigger research, 202 response
# ---------------------------------------------------------------------------

_CONFIRM_ALLOWED_STATUSES = {
    ExperimentStatus.REFINED,
    ExperimentStatus.RESEARCH_FAILED,  # re-dispatch after failed run
}


@router.post(
    "/{experiment_id}/confirm",
    response_model=ConfirmResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def confirm_research(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    dispatcher: Annotated[ResearchDispatcher, Depends(get_dispatcher_dep)],
) -> ConfirmResearchResponse:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    if experiment.status not in _CONFIRM_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experiment must be in REFINED or RESEARCH_FAILED status to confirm research (current: {experiment.status})",
        )

    # Clear stale error detail BEFORE setting new status so the old status
    # read on the next line is still meaningful (== RESEARCH_FAILED check).
    if experiment.status == ExperimentStatus.RESEARCH_FAILED:
        experiment.research_error_detail = None
    experiment.status = ExperimentStatus.RESEARCHING
    await db.flush()
    await db.commit()

    try:
        await dispatcher.dispatch(experiment_id)
    except DispatchError as exc:
        _logger.error("dispatch failed", error_type=type(exc).__name__, experiment_id=str(experiment_id))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start research pipeline, please try again",
        ) from exc

    status_url = str(request.url_for("get_research_status", experiment_id=experiment_id))
    return ConfirmResearchResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.RESEARCHING,
        status_url=status_url,
    )


# ---------------------------------------------------------------------------
# GET /experiments/{id}/research-status — polling endpoint, 30/min/user
# ---------------------------------------------------------------------------


@router.get(
    "/{experiment_id}/research-status",
    response_model=ResearchStatusResponse,
    status_code=status.HTTP_200_OK,
    name="get_research_status",
)
@limiter.limit(_RESEARCH_STATUS_RATE_LIMIT, key_func=user_key)
async def get_research_status(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResearchStatusResponse:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    return ResearchStatusResponse(
        status=experiment.status,
        phase_label=get_phase_label(experiment.status),
        phases_completed=get_phases_completed(experiment.status),
        last_updated_at=experiment.updated_at,
        error_detail=experiment.research_error_detail
        if experiment.status == ExperimentStatus.RESEARCH_FAILED
        else None,
    )
