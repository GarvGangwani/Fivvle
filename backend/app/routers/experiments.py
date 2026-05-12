"""Experiment router — POST /experiments and POST /experiments/{id}/refine.

Per .cursorrules "API Design": router functions are thin (5-15 lines each).
All domain logic lives in app.services.experiment_service.

Per AGENTS.md "Authentication and authorization":
- Authentication: Depends(get_current_user) — verifies Firebase ID token, returns User.
- Authorization (ownership): checked SEPARATELY with an explicit comparison before any
  mutation. Ownership failure returns 404, not 403 — never reveal that the experiment
  exists for a different user.

Per AGENTS.md "Error handling":
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
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_session
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.experiment import (
    CreateExperimentRequest,
    ExperimentResponse,
    RegenerateRefinementRequest,
)
from app.services.experiment_service import (
    InvalidExperimentState,
    RefinementLimitExceeded,
    create_experiment_with_refinement,
    regenerate_refinement,
)

_logger = get_logger(__name__)

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
