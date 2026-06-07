"""Experiment router — POST /experiments, POST /experiments/{id}/refine,
POST /experiments/{id}/confirm, GET /experiments/{id}, GET /experiments/{id}/research-status.

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
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.enums import DispatchTrigger, ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.session import get_session
from app.dispatchers.dependencies import get_dispatcher_dep, get_insight_dispatcher_dep
from app.dispatchers.factory import get_landing_page_dispatcher_dep
from app.dispatchers.protocol import (
    DispatchError,
    InsightDispatcher,
    LandingPageDispatcher,
    ResearchDispatcher,
)
from app.logging_config import get_logger
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.experiment import (
    ConfirmResearchResponse,
    CreateExperimentRequest,
    ExperimentResponse,
    RegenerateRefinementRequest,
    ResearchStatusResponse,
)
from app.services.dispatch_service import transition_to_researching_and_dispatch
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


class ExperimentValidationReportSummary(BaseModel):
    """Aggregates for smoke / dashboards — not the full ValidationReport JSON."""

    model_config = ConfigDict(extra="forbid")

    overall_recommendation: str | None = None
    total_finding_count: int = Field(ge=0)
    total_citation_count: int = Field(ge=0)


class GenerateInsightResponse(BaseModel):
    """Response from POST /experiments/{id}/generate-insight.

    Returned with HTTP 202. The actual InsightReport is built asynchronously;
    the frontend polls GET /experiments/{id} for status transitions until
    status reaches INSIGHT_READY or INSIGHT_FAILED.
    """

    model_config = ConfigDict(from_attributes=True)

    experiment_id: UUID
    status: ExperimentStatus = Field(
        description="Set to INSIGHT_GENERATING by this endpoint immediately on dispatch."
    )


class GenerateLandingPageRequest(BaseModel):
    """Optional body for POST /experiments/{id}/generate-landing-page."""

    model_config = ConfigDict(extra="forbid")

    page_goal: str = Field(
        default="waitlist",
        description="Primary conversion goal (waitlist, interest, or contact).",
    )
    template_id: str = Field(
        default="dark-premium",
        description="Designer template ID to apply (e.g. dark-premium, bold-v1).",
    )


class GenerateLandingPageResponse(BaseModel):
    """Response from POST /experiments/{id}/generate-landing-page.

    Returned with HTTP 202. Landing page copy and layout are built asynchronously;
    the frontend polls GET /experiments/{id} for status transitions until
    status reaches LANDING_DRAFT or returns to RESEARCH_READY on failure.
    """

    model_config = ConfigDict(from_attributes=True)

    experiment_id: UUID
    status: ExperimentStatus = Field(
        description="Set to LANDING_GENERATING by this endpoint immediately on dispatch."
    )


class GetExperimentDetailResponse(BaseModel):
    """GET /experiments/{id} — minimal experiment row + optional report aggregates."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: ExperimentStatus
    validation_report: ExperimentValidationReportSummary | None = None


def _aggregate_validation_report(raw: dict) -> ExperimentValidationReportSummary:
    qfs = raw.get("questions_and_findings") or []
    finding_count = sum(len(qf.get("findings") or []) for qf in qfs)
    citation_count = 0
    for qf in qfs:
        for f in qf.get("findings") or []:
            citation_count += len(f.get("citations") or [])
    for comp in raw.get("competitors") or []:
        citation_count += len(comp.get("citations") or [])
    rec = raw.get("overall_recommendation")
    if rec is not None and not isinstance(rec, str):
        rec = str(rec)
    return ExperimentValidationReportSummary(
        overall_recommendation=rec,
        total_finding_count=finding_count,
        total_citation_count=citation_count,
    )

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

    try:
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.USER_CONFIRM,
            dispatcher,
        )
    except InvalidExperimentState:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in REFINED or RESEARCH_FAILED status to confirm "
                f"research (current: {experiment.status})"
            ),
        ) from None
    except DispatchError as exc:
        _logger.error(
            "dispatch failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
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


async def _check_min_insight_data(
    db: AsyncSession, experiment_id: UUID
) -> tuple[int, int, int]:
    """Compute (page_view_count, signup_count, days_live) for the experiment.

    Returns the triple even when min-data is not met — the caller decides
    whether to raise 409 based on these numbers.

    days_live is 0 when LandingPage is missing or live_at is None — in that
    case the (LANDING_LIVE status precondition) should have blocked the call
    earlier, but we return 0 defensively.
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    from sqlalchemy import func  # noqa: PLC0415

    from app.db.models.landing_page import LandingPage  # noqa: PLC0415
    from app.db.models.page_view import PageView  # noqa: PLC0415
    from app.db.models.waitlist_signup import WaitlistSignup  # noqa: PLC0415

    views_stmt = select(func.count(PageView.id)).where(
        PageView.experiment_id == experiment_id
    )
    signups_stmt = select(func.count(WaitlistSignup.id)).where(
        WaitlistSignup.experiment_id == experiment_id
    )
    landing_stmt = select(LandingPage.live_at).where(
        LandingPage.experiment_id == experiment_id
    )

    views_result = await db.execute(views_stmt)
    signups_result = await db.execute(signups_stmt)
    landing_result = await db.execute(landing_stmt)

    page_view_count = int(views_result.scalar_one() or 0)
    signup_count = int(signups_result.scalar_one() or 0)
    live_at = landing_result.scalar_one_or_none()

    if live_at is None:
        days_live = 0
    else:
        days_live = max((datetime.now(timezone.utc) - live_at).days, 0)

    return page_view_count, signup_count, days_live


@router.post(
    "/{experiment_id}/generate-insight",
    response_model=GenerateInsightResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_insight(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    insight_dispatcher: Annotated[InsightDispatcher, Depends(get_insight_dispatcher_dep)],
) -> GenerateInsightResponse:
    """User-triggered insight generation per b4-insight-generator.md.

    Allowed source statuses: LANDING_LIVE (first generation), INSIGHT_READY (regen),
    INSIGHT_FAILED (retry). Any other status returns 409.

    Min-data guard: at least one of (≥10 page views, ≥1 signup, ≥7 days live).
    Below the threshold → 409 with a guidance message.

    On dispatch, transitions status to INSIGHT_GENERATING and commits before
    awaiting the dispatcher. The dispatcher transitions to terminal state
    (INSIGHT_READY or INSIGHT_FAILED) asynchronously. On DispatchError, rolls
    back to INSIGHT_FAILED and returns 502.
    """
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()

    # 404 on missing OR not-owned — never reveal existence to a non-owner.
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )

    allowed_source_statuses = {
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
    }
    if experiment.status not in allowed_source_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in LANDING_LIVE, INSIGHT_READY, or INSIGHT_FAILED "
                f"status to generate insight (current: {experiment.status.value})."
            ),
        )

    page_view_count, signup_count, days_live = await _check_min_insight_data(
        db, experiment_id
    )
    meets_threshold = (
        page_view_count >= 10 or signup_count >= 1 or days_live >= 7
    )
    if not meets_threshold:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Insufficient data for insight generation. Need at least one of: "
                "10 page views, 1 signup, or 7 days since landing page went live. "
                f"Current: {page_view_count} views, {signup_count} signups, "
                f"{days_live} day(s) live."
            ),
        )

    experiment.status = ExperimentStatus.INSIGHT_GENERATING
    await db.commit()

    try:
        await insight_dispatcher.dispatch(experiment_id)
    except DispatchError as exc:
        _logger.error(
            "insight dispatch failed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        # Roll back to FAILED so the user sees an actionable state.
        experiment.status = ExperimentStatus.INSIGHT_FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start insight generation, please try again",
        ) from exc

    return GenerateInsightResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.INSIGHT_GENERATING,
    )


@router.post(
    "/{experiment_id}/generate-landing-page",
    response_model=GenerateLandingPageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: GenerateLandingPageRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    landing_page_dispatcher: Annotated[
        LandingPageDispatcher, Depends(get_landing_page_dispatcher_dep)
    ],
) -> GenerateLandingPageResponse:
    """User-triggered landing page generation per ADR 0022.

    Allowed source statuses: RESEARCH_READY (first generation), LANDING_DRAFT
    (regen). Any other status returns 409.

    On dispatch, transitions status to LANDING_GENERATING and commits before
    awaiting the dispatcher. The dispatcher transitions to terminal state
    (LANDING_DRAFT or RESEARCH_READY on failure) asynchronously. On
    DispatchError, rolls back to RESEARCH_READY and returns 502.
    """
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()

    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )

    allowed_source_statuses = {
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.LANDING_DRAFT,
    }
    if experiment.status not in allowed_source_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in RESEARCH_READY or LANDING_DRAFT status "
                f"to generate landing page (current: {experiment.status.value})."
            ),
        )

    experiment.status = ExperimentStatus.LANDING_GENERATING
    await db.commit()

    try:
        await landing_page_dispatcher.dispatch(
            experiment_id,
            body.page_goal,
            body.template_id,
        )
    except DispatchError as exc:
        _logger.error(
            "landing page dispatch failed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        experiment.status = ExperimentStatus.RESEARCH_READY
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start landing page generation, please try again",
        ) from exc

    return GenerateLandingPageResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.LANDING_GENERATING,
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


# ---------------------------------------------------------------------------
# GET /experiments/{id} — owner detail + ValidationReport aggregates (smoke / FE)
# ---------------------------------------------------------------------------


@router.get(
    "/{experiment_id}",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_experiment_detail(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment_id),
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    summary = None
    if experiment.validation_report is not None:
        summary = _aggregate_validation_report(experiment.validation_report.raw_report)

    return GetExperimentDetailResponse(
        id=experiment.id,
        status=experiment.status,
        validation_report=summary,
    )
