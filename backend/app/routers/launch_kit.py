"""LaunchKit router — generate / get / patch / regen the launch package.

Endpoints (all under /experiments/{experiment_id}):
  - POST  /generate-launch-kit  → 202, dispatches async generation (idempotent
        regenerate). Gated on a live landing page.
  - GET   /launch-kit           → 200 LaunchKitEnvelope or 404.
  - PATCH /launch-kit           → 200 LaunchKitEnvelope, optimistic-concurrency
        edit (compare-and-swap on ``version``).
  - POST  /launch-kit/regenerate-variant → 200 LaunchKitEnvelope. Server bumps
        version; body is ``{surface}`` only. Regen writes over any concurrent
        edits to the target surface. Other surfaces and metadata are preserved.

Per .cursorrules «API Design»: handlers are thin; domain logic lives in
app.services.launch_kit_service. Per AGENTS.md: authentication via
Depends(get_current_user); ownership verified separately (404, never 403).
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
from app.db.models.landing_page import LandingPage
from app.db.models.user import User
from app.db.session import get_session
from app.dispatchers.dependencies import get_launch_kit_dispatcher_dep
from app.dispatchers.protocol import DispatchError, LaunchKitDispatcher
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.launch_kit import (
    LaunchKitEnvelope,
    LaunchKitGenerateResponse,
    LaunchKitPatchRequest,
    LaunchKitRegenRequest,
)
from app.services.launch_kit_service import (
    LaunchKitLLMError,
    LaunchKitNotFoundError,
    LaunchKitVersionConflictError,
    get_launch_kit,
    patch_launch_kit,
    regenerate_variant,
)

_logger = get_logger(__name__)

router = APIRouter(prefix="/experiments", tags=["launch-kit"])

# A launch kit can be (re)generated once the landing page is ready: status in the
# landing/insight band below. RESEARCH_READY and LANDING_GENERATING (and any other
# status) are rejected with 409 — the founder generates the landing page first.
# No LANDING_FAILED / LAUNCH_KIT_FAILED status exists; a soft-failed generation
# leaves status untouched and the founder retries the endpoint.
_LAUNCH_KIT_ALLOWED_STATUSES: frozenset[ExperimentStatus] = frozenset(
    {
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
    }
)
_LANDING_NOT_READY_MESSAGE = "Landing page must be ready before generating a launch kit."


async def _get_owned_experiment(
    db: AsyncSession, *, experiment_id: UUID, user_id: UUID
) -> Experiment:
    """Load an experiment and verify ownership. 404 on missing or not-owned."""
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    return experiment


@router.post(
    "/{experiment_id}/generate-launch-kit",
    response_model=LaunchKitGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_launch_kit_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    launch_kit_dispatcher: Annotated[
        LaunchKitDispatcher, Depends(get_launch_kit_dispatcher_dep)
    ],
) -> LaunchKitGenerateResponse:
    """Dispatch async LaunchKit generation (also used to regenerate).

    Precondition: a landing page exists AND the experiment is at or past
    LANDING_DRAFT. Otherwise 409. Regeneration overwrites raw_report, clears any
    founder edits, and bumps the version.
    """
    experiment = await _get_owned_experiment(
        db, experiment_id=experiment_id, user_id=current_user.id
    )

    if experiment.status not in _LAUNCH_KIT_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_LANDING_NOT_READY_MESSAGE,
        )

    landing_page = (
        await db.execute(
            select(LandingPage).where(LandingPage.experiment_id == experiment_id)
        )
    ).scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_LANDING_NOT_READY_MESSAGE,
        )

    try:
        await launch_kit_dispatcher.dispatch(experiment_id)
    except DispatchError as exc:
        _logger.error(
            "launch kit dispatch failed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start launch kit generation, please try again",
        ) from exc

    return LaunchKitGenerateResponse(
        experiment_id=experiment_id, generation_started=True
    )


@router.get(
    "/{experiment_id}/launch-kit",
    response_model=LaunchKitEnvelope,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_launch_kit_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LaunchKitEnvelope:
    """Return the current LaunchKit (founder-edited overlay if present)."""
    await _get_owned_experiment(
        db, experiment_id=experiment_id, user_id=current_user.id
    )
    envelope = await get_launch_kit(db, experiment_id)
    if envelope is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Launch kit not found",
        )
    return envelope


@router.patch(
    "/{experiment_id}/launch-kit",
    response_model=LaunchKitEnvelope,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def patch_launch_kit_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: LaunchKitPatchRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LaunchKitEnvelope:
    """Apply a founder edit under optimistic concurrency (CAS on ``version``)."""
    await _get_owned_experiment(
        db, experiment_id=experiment_id, user_id=current_user.id
    )
    try:
        envelope = await patch_launch_kit(
            db,
            experiment_id,
            expected_version=body.version,
            patch=body.patch,
        )
    except LaunchKitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Launch kit not found",
        ) from exc
    except LaunchKitVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Launch kit was modified since you loaded it, please reload",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await db.commit()
    return envelope


@router.post(
    "/{experiment_id}/launch-kit/regenerate-variant",
    response_model=LaunchKitEnvelope,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def regenerate_variant_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: LaunchKitRegenRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LaunchKitEnvelope:
    """Rewrite one share-copy surface; server bumps version.

    Regen writes over any concurrent edits to the target surface. Other
    surfaces and metadata are preserved.
    """
    await _get_owned_experiment(
        db, experiment_id=experiment_id, user_id=current_user.id
    )
    try:
        envelope = await regenerate_variant(
            db, experiment_id, surface=body.surface
        )
    except LaunchKitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Launch kit not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LaunchKitLLMError as exc:
        _logger.error(
            "launch kit regen failed",
            experiment_id=str(experiment_id),
            surface=body.surface.value,
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to regenerate share copy, please try again",
        ) from exc

    await db.commit()
    return envelope
