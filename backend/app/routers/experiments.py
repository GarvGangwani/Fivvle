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

import asyncio
import csv
import io
import re
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.enums import DispatchTrigger, ExperimentStatus, FounderDecision
from app.db.models.experiment import Experiment
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.db.models.waitlist_signup import WaitlistSignup
from app.db.session import get_session
from app.dispatchers.dependencies import (
    get_dispatcher_dep,
    get_insight_dispatcher_dep,
    get_landing_page_dispatcher_dep,
)
from app.dispatchers.in_process_landing_page import landing_generation_in_progress
from app.services.landing_page_revalidate import notify_live_landing_page_changed
from app.services.landing_page_publish_service import (
    close_and_open_next_cohort,
    create_first_cohort,
    get_open_cohort,
)
from app.utils.landing_page_public import is_landing_page_editable, is_public_landing_page_accessible
from app.utils.landing_page_urls import build_public_landing_page_url
from app.utils.wallet_http import debit_for_service_or_raise, refund_for_service
from app.utils.experiment_naming import (
    sync_landing_page_project_name,
    validate_landing_slug,
)
from app.dispatchers.protocol import (
    DispatchError,
    InsightDispatcher,
    LandingPageDispatcher,
    ResearchDispatcher,
)
from app.logging_config import get_logger
from app.pricing import SERVICE_PRICING
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.api_responses import (
    AnalyticsResponse,
    ArchiveExperimentResponse,
    ArchiveRequest,
    DeleteExperimentRequest,
    DeleteExperimentResponse,
    FounderDecisionResponse,
    InsightProgress,
    InsightReportResponse,
    LandingPagePatchRequest,
    LandingPageResponse,
    LandingPageSlugAvailabilityResponse,
    LogoUploadResponse,
    MetricsAccessResponse,
    RecordFounderDecisionRequest,
    SectionImageUploadResponse,
    PublishLandingPageRequest,
    PublishResponse,
    UnlockMetricsResponse,
    ValidationReportResponse,
    WaitlistSignupItem,
    WaitlistSignupsResponse,
)
from app.schemas.experiment import (
    ConfirmResearchResponse,
    CreateExperimentRequest,
    ExperimentListItemResponse,
    ExperimentResponse,
    RegenerateRefinementRequest,
    RenameExperimentRequest,
    ResearchStatusResponse,
    SetExperimentThemeRequest,
)
from app.schemas.chat import ChatMessageItem
from app.schemas.evidence_chat import (
    EvidenceChatActivateResponse,
    EvidenceChatEditRequest,
    EvidenceChatEditResponse,
    EvidenceChatMessagesResponse,
    EvidenceChatRegenerateRequest,
    EvidenceChatRegenerateResponse,
    EvidenceChatSendRequest,
    EvidenceChatSendResponse,
)
from app.schemas.evidence_chat_feedback import (
    EvidenceChatFeedbackRequest,
    EvidenceChatFeedbackResponse,
)
from app.schemas.universal_chat import (
    UniversalChatCancelRequest,
    UniversalChatMessagesResponse,
    UniversalChatSendRequest,
    UniversalChatSendResponse,
)
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport as ValidationReportSchema
from app.schemas.validation_report_edited_doc import (
    EditedDocPatchRequest,
    EditedDocResponse,
)
from app.schemas.tags import UpdateExperimentTagsRequest
from app.services.evidence_chat_service import (
    EvidenceChatInvalidTarget,
    EvidenceChatNotFound,
    activate_evidence_chat_branch,
    edit_evidence_chat_message,
    format_sse_event,
    list_evidence_chat_messages,
    prepare_evidence_stream,
    regenerate_evidence_chat_message,
    send_evidence_chat_message,
    stream_evidence_reply,
    upsert_evidence_chat_feedback,
)
from app.services.universal_chat_service import (
    UniversalChatNotFound,
    UniversalChatUnavailable,
    cancel_universal_turn,
    list_universal_chat_messages,
    prepare_universal_stream,
    send_universal_chat_message,
    start_universal_turn,
    stream_universal_chat_message,
)
from app.services.chat_attachment_service import ChatAttachmentAccessError
from app.utils.chat_attachment import ChatAttachmentValidationError
from app.services.validation_report_editor import (
    EditedDocVersionConflict,
    apply_edited_doc_patch,
    build_edited_doc_response,
)
from app.services.tag_service import validate_tags
from app.services.analytics_aggregator import (
    LandingPageNotLiveError,
    build_analytics_aggregate,
)
from app.services.insight_threshold import compute_insight_threshold
from app.services.dispatch_service import transition_to_researching_and_dispatch
from app.services.experiment_dashboard_stats import build_experiment_card_stats_map
from app.services.experiment_service import (
    InvalidExperimentState,
    RefinementLimitExceeded,
    create_experiment_spark,
    create_experiment_with_refinement,
    delete_experiment,
    extract_refined_idea_text,
    fetch_experiment_canvas_metrics,
    infer_status_after_unarchive,
    regenerate_refinement,
)
from app.services.founder_decision_service import (
    FounderDecisionArchivedError,
    FounderDecisionVersionConflict,
    apply_founder_decision,
)
from app.services.spark_version_service import fetch_spark_phase_version_info
from app.services.idea_capture_service import (
    IdeaAlreadyCapturedError,
    IdeaCaptureValidationError,
    capture_original_idea,
)
from app.services.capture_greeting_service import (
    CaptureGreetingError,
    ensure_capture_greeting,
    stream_capture_greeting_tokens,
)
from app.db.models.chat_attachment import ChatAttachment
from app.schemas.idea_capture import (
    CaptureIdeaFrozenAttachment,
    CaptureIdeaRequest,
    CaptureIdeaResponse,
    OriginFrozenAttachment,
)
from app.services.logo_upload_service import (
    LogoUploadError,
    upload_landing_page_logo,
    upload_landing_page_section_image,
)
from app.services.research_phase_mapping import get_phase_label, get_phases_completed
from app.services.wallet_service import (
    InsufficientCredits,
    get_or_create_wallet,
    has_purchased_service_for_experiment,
    purchase_service_for_experiment,
)
from app.utils.wallet_http import insufficient_credits_http

_logger = get_logger(__name__)

# 30/min/user for the polling endpoint — per the spec.
_RESEARCH_STATUS_RATE_LIMIT = "30/minute"

_WAITLIST_EXPORT_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _ensure_landing_page_editable(experiment: Experiment) -> None:
    """Reject landing-page mutations when archived, generating, or pre-landing."""
    if experiment.status == ExperimentStatus.LANDING_GENERATING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Landing page is regenerating. Try again shortly.",
        )
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived projects cannot be edited.",
        )
    if not is_landing_page_editable(experiment.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Landing page cannot be edited in the current project stage.",
        )


def _ensure_metrics_access_allowed(
    experiment: Experiment,
    *,
    live_at: datetime | None,
) -> None:
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived projects cannot unlock metrics.",
        )
    if not is_public_landing_page_accessible(experiment.status, live_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Metrics are available after your landing page is live.",
        )


_RESEARCH_ACTIVE_STATUSES: frozenset[ExperimentStatus] = frozenset(
    {
        ExperimentStatus.RESEARCHING,
        ExperimentStatus.RESEARCH_PLANNING,
        ExperimentStatus.RESEARCH_SEARCHING,
        ExperimentStatus.RESEARCH_READING,
        ExperimentStatus.RESEARCH_REFLECTING,
        ExperimentStatus.RESEARCH_VOICES,
        ExperimentStatus.RESEARCH_SYNTHESIZING,
    }
)


async def _get_owned_experiment_for_update(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    user_id: UUID,
) -> Experiment:
    """Load an experiment row with FOR UPDATE for billing-critical transitions."""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id).with_for_update()
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    return experiment


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
    credits_balance: int = Field(ge=0)


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
    regeneration_hint: str | None = Field(
        default=None,
        description=(
            "Optional nonce/hint to force a distinct regeneration output "
            "(e.g. section name + timestamp)."
        ),
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
    name: str | None = None
    raw_idea: str
    status: ExperimentStatus
    thread_id: UUID | None = None
    validation_report: ExperimentValidationReportSummary | None = None
    refined_idea: str | None = None
    refined_idea_current: RefinedIdea | None = None
    refined_idea_updated_at: datetime | None = None
    chat_message_count: int = Field(default=0, ge=0)
    evidence_atom_count: int = Field(default=0, ge=0)
    landing_page_view_count: int = Field(default=0, ge=0)
    resource_count: int = Field(default=0, ge=0)
    attachment_count: int = Field(default=0, ge=0)
    demand_score: int | None = Field(default=None, ge=0, le=100)
    verdict: str | None = None
    # Founder-recorded Signal decision — distinct from `verdict` above.
    founder_decision: FounderDecision | None = None
    founder_decision_at: datetime | None = None
    founder_decision_note: str | None = None
    founder_decision_version: int | None = Field(default=None, ge=1)
    spark_last_edited_at: datetime | None = None
    refinement_started_at: datetime | None = None
    # Progressive canvas reveal signals. refine_completed_at is the founder's
    # explicit "done refining" stamp; landing_page_live_at is durable where
    # status is not (re-finalizing refine can move status back to REFINED, and a
    # revealed phase must never disappear).
    refine_completed_at: datetime | None = None
    landing_page_live_at: datetime | None = None
    current_spark_version: int = 0
    current_refined_idea_version: int = 0
    current_edited_doc_version: int | None = None
    refine_spark_version: int | None = None
    evidence_spark_version: int | None = None
    launch_spark_version: int | None = None
    signal_spark_version: int | None = None
    refine_refined_idea_version: int | None = None
    evidence_refined_idea_version: int | None = None
    launch_refined_idea_version: int | None = None
    signal_refined_idea_version: int | None = None
    launch_edited_doc_version: int | None = None
    refine_is_stale: bool = False
    evidence_is_stale: bool = False
    launch_is_stale: bool = False
    signal_is_stale: bool = False
    refine_stale_reasons: list[str] = Field(default_factory=list)
    evidence_stale_reasons: list[str] = Field(default_factory=list)
    launch_stale_reasons: list[str] = Field(default_factory=list)
    signal_stale_reasons: list[str] = Field(default_factory=list)
    # Immutable original idea (write-once at capture). Null until captured.
    has_original_idea: bool = False
    original_idea: str | None = None
    original_idea_captured_at: datetime | None = None
    origin_attachments: list[OriginFrozenAttachment] = Field(default_factory=list)
    # Canvas palette: active founder choice (null = platform purple) and the
    # AI suggestion from capture, offered separately by the canvas control.
    theme_palette: str | None = None
    suggested_palette: str | None = None


async def _list_origin_attachments(
    db: AsyncSession,
    experiment_id: UUID,
) -> list[OriginFrozenAttachment]:
    result = await db.execute(
        select(ChatAttachment)
        .where(ChatAttachment.origin_experiment_id == experiment_id)
        .order_by(ChatAttachment.created_at.asc())
    )
    rows = list(result.scalars().all())
    return [
        OriginFrozenAttachment(
            id=row.id,
            original_filename=row.original_filename,
            content_kind=row.content_kind,
            media_type=row.media_type,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def _build_experiment_detail_response(
    db: AsyncSession,
    experiment: Experiment,
) -> GetExperimentDetailResponse:
    summary = None
    validation_raw = None
    if experiment.validation_report is not None:
        validation_raw = experiment.validation_report.raw_report
        summary = _aggregate_validation_report(validation_raw)

    metrics = await fetch_experiment_canvas_metrics(
        db,
        experiment.id,
        thread_id=experiment.thread_id,
        validation_raw=validation_raw,
    )
    spark_info = await fetch_spark_phase_version_info(db, experiment)
    origin_attachments = await _list_origin_attachments(db, experiment.id)
    has_original = experiment.original_idea is not None
    # Queried rather than read off experiment.landing_page — not every caller of
    # this builder eager-loads that relation.
    landing_live_at = await db.scalar(
        select(LandingPage.live_at).where(LandingPage.experiment_id == experiment.id)
    )

    return GetExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        raw_idea=experiment.raw_idea,
        status=experiment.status,
        thread_id=experiment.thread_id,
        validation_report=summary,
        refined_idea=extract_refined_idea_text(experiment.refined_idea),
        refined_idea_current=_coerce_refined_idea(experiment.refined_idea_current),
        refined_idea_updated_at=experiment.refined_idea_updated_at,
        chat_message_count=metrics.chat_message_count,
        evidence_atom_count=metrics.evidence_atom_count,
        landing_page_view_count=metrics.landing_page_view_count,
        resource_count=metrics.resource_count,
        attachment_count=metrics.attachment_count,
        demand_score=metrics.demand_score,
        verdict=metrics.verdict,
        founder_decision=experiment.founder_decision,
        founder_decision_at=experiment.founder_decision_at,
        founder_decision_note=experiment.founder_decision_note,
        founder_decision_version=experiment.founder_decision_version,
        spark_last_edited_at=experiment.spark_last_edited_at,
        refinement_started_at=experiment.refinement_started_at,
        refine_completed_at=experiment.refine_completed_at,
        landing_page_live_at=landing_live_at,
        current_spark_version=spark_info.current_spark_version,
        current_refined_idea_version=spark_info.current_refined_idea_version,
        current_edited_doc_version=spark_info.current_edited_doc_version,
        refine_spark_version=spark_info.refine_spark_version,
        evidence_spark_version=spark_info.evidence_spark_version,
        launch_spark_version=spark_info.launch_spark_version,
        signal_spark_version=spark_info.signal_spark_version,
        refine_refined_idea_version=spark_info.refine_refined_idea_version,
        evidence_refined_idea_version=spark_info.evidence_refined_idea_version,
        launch_refined_idea_version=spark_info.launch_refined_idea_version,
        signal_refined_idea_version=spark_info.signal_refined_idea_version,
        launch_edited_doc_version=spark_info.launch_edited_doc_version,
        refine_is_stale=spark_info.refine_is_stale,
        evidence_is_stale=spark_info.evidence_is_stale,
        launch_is_stale=spark_info.launch_is_stale,
        signal_is_stale=spark_info.signal_is_stale,
        refine_stale_reasons=spark_info.refine_stale_reasons,
        evidence_stale_reasons=spark_info.evidence_stale_reasons,
        launch_stale_reasons=spark_info.launch_stale_reasons,
        signal_stale_reasons=spark_info.signal_stale_reasons,
        has_original_idea=has_original,
        original_idea=experiment.original_idea,
        original_idea_captured_at=experiment.original_idea_captured_at,
        origin_attachments=origin_attachments,
        theme_palette=experiment.theme_palette,
        suggested_palette=experiment.suggested_palette,
    )


def _coerce_refined_idea(value: dict | None) -> RefinedIdea | None:
    if not value:
        return None
    try:
        return RefinedIdea.model_validate(value)
    except Exception:
        return None


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


# ---------------------------------------------------------------------------
# GET /experiments — list current user's experiments (before /{experiment_id})
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ExperimentListItemResponse], status_code=status.HTTP_200_OK)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def list_experiments(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    archived: Annotated[bool, Query(description="When true, return archived projects only")] = False,
) -> list[ExperimentListItemResponse]:
    query = select(Experiment).where(Experiment.user_id == current_user.id)
    if archived:
        query = query.where(Experiment.status == ExperimentStatus.ARCHIVED)
    else:
        query = query.where(Experiment.status != ExperimentStatus.ARCHIVED)
    result = await db.execute(query.order_by(Experiment.updated_at.desc()))
    experiments = list(result.scalars().all())
    stats_map = await build_experiment_card_stats_map(
        db,
        experiments,
        user_id=current_user.id,
    )

    items: list[ExperimentListItemResponse] = []
    for experiment in experiments:
        base = ExperimentResponse.model_validate(experiment)
        items.append(
            ExperimentListItemResponse(
                **base.model_dump(),
                card_stats=stats_map.get(experiment.id),
            )
        )
    return items


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def create_experiment(
    request: Request,
    response: Response,
    body: CreateExperimentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Experiment:
    user_id = str(current_user.id)
    try:
        # Name-only Spark create. Legacy clients that still send a long raw_idea
        # keep the immediate-refinement path.
        if body.raw_idea and len(body.raw_idea.strip()) >= 50:
            return await create_experiment_with_refinement(
                db,
                current_user,
                body.raw_idea,
                body.name,
            )
        return await create_experiment_spark(db, current_user, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("experiment creation failed", error_type=type(exc).__name__, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create experiment, please try again",
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
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )

    if experiment.status in _RESEARCH_ACTIVE_STATUSES:
        status_url = str(request.url_for("get_research_status", experiment_id=experiment_id))
        wallet = await get_or_create_wallet(db, current_user.id)
        return ConfirmResearchResponse(
            experiment_id=experiment_id,
            status=experiment.status,
            status_url=status_url,
            credits_balance=wallet.credits_balance,
        )

    if experiment.status not in {
        ExperimentStatus.REFINED,
        ExperimentStatus.RESEARCH_FAILED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in REFINED or RESEARCH_FAILED status to confirm "
                f"research (current: {experiment.status})"
            ),
        )

    await debit_for_service_or_raise(
        db,
        user_id=current_user.id,
        service="fullValidationFlow",
        experiment_id=experiment_id,
    )
    await db.commit()

    try:
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.USER_CONFIRM,
            dispatcher,
        )
    except InvalidExperimentState:
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="fullValidationFlow",
            reason="invalid experiment state",
            experiment_id=experiment_id,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in REFINED or RESEARCH_FAILED status to confirm "
                f"research (current: {experiment.status})"
            ),
        ) from None
    except DispatchError as exc:
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="fullValidationFlow",
            reason="research dispatch failed",
            experiment_id=experiment_id,
        )
        await db.commit()
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
    wallet = await get_or_create_wallet(db, current_user.id)
    return ConfirmResearchResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.RESEARCHING,
        status_url=status_url,
        credits_balance=wallet.credits_balance,
    )


@router.post(
    "/{experiment_id}/evidence/rerun",
    response_model=ConfirmResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def rerun_evidence(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    dispatcher: Annotated[ResearchDispatcher, Depends(get_dispatcher_dep)],
) -> ConfirmResearchResponse:
    """Re-trigger the research pipeline against the current Spark version."""
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )

    if experiment.status in _RESEARCH_ACTIVE_STATUSES:
        status_url = str(request.url_for("get_research_status", experiment_id=experiment_id))
        wallet = await get_or_create_wallet(db, current_user.id)
        return ConfirmResearchResponse(
            experiment_id=experiment_id,
            status=experiment.status,
            status_url=status_url,
            credits_balance=wallet.credits_balance,
        )

    await debit_for_service_or_raise(
        db,
        user_id=current_user.id,
        service="fullValidationFlow",
        experiment_id=experiment_id,
    )
    await db.commit()

    try:
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.EVIDENCE_RERUN,
            dispatcher,
        )
    except InvalidExperimentState:
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="fullValidationFlow",
            reason="invalid experiment state",
            experiment_id=experiment_id,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Evidence re-run requires a completed or failed research phase "
                f"(current: {experiment.status})"
            ),
        ) from None
    except DispatchError as exc:
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="fullValidationFlow",
            reason="research dispatch failed",
            experiment_id=experiment_id,
        )
        await db.commit()
        _logger.error(
            "evidence rerun dispatch failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start research pipeline, please try again",
        ) from exc

    status_url = str(request.url_for("get_research_status", experiment_id=experiment_id))
    wallet = await get_or_create_wallet(db, current_user.id)
    return ConfirmResearchResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.RESEARCHING,
        status_url=status_url,
        credits_balance=wallet.credits_balance,
    )


async def _check_min_insight_data(
    db: AsyncSession, experiment_id: UUID
) -> tuple[int, int, int]:
    """Compute (page_view_count, signup_count, days_live) for the current cohort.

    Returns the triple even when min-data is not met — the caller decides
    whether to raise 409 based on these numbers. Delegates to
    ``compute_insight_threshold`` so the ratchet stays single-sourced.
    """
    threshold = await compute_insight_threshold(db, experiment_id)
    return (
        threshold.views_current,
        threshold.signups_current,
        threshold.days_current,
    )


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
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )

    if experiment.status == ExperimentStatus.INSIGHT_GENERATING:
        wallet = await get_or_create_wallet(db, current_user.id)
        return GenerateInsightResponse(
            experiment_id=experiment_id,
            status=ExperimentStatus.INSIGHT_GENERATING,
            credits_balance=wallet.credits_balance,
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

    await debit_for_service_or_raise(
        db,
        user_id=current_user.id,
        service="insightReport",
        experiment_id=experiment_id,
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
        experiment = await _get_owned_experiment_for_update(
            db,
            experiment_id=experiment_id,
            user_id=current_user.id,
        )
        experiment.status = ExperimentStatus.INSIGHT_FAILED
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="insightReport",
            reason="insight dispatch failed",
            experiment_id=experiment_id,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start insight generation, please try again",
        ) from exc

    wallet = await get_or_create_wallet(db, current_user.id)
    return GenerateInsightResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.INSIGHT_GENERATING,
        credits_balance=wallet.credits_balance,
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
    (regen). LANDING_GENERATING returns 202 idempotently. Any other status
    returns 409.

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

    stuck_generating = False
    if experiment.status == ExperimentStatus.LANDING_GENERATING:
        settings = get_settings()
        stuck_generating = (
            settings.dispatcher_mode == "in_process"
            and not landing_generation_in_progress(experiment_id)
        )
        if not stuck_generating:
            return GenerateLandingPageResponse(
                experiment_id=experiment_id,
                status=ExperimentStatus.LANDING_GENERATING,
            )

    allowed_source_statuses = {
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
    }
    if stuck_generating:
        allowed_source_statuses.add(ExperimentStatus.LANDING_GENERATING)
    if experiment.status not in allowed_source_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in RESEARCH_READY, LANDING_DRAFT, or LANDING_LIVE status "
                f"to generate landing page (current: {experiment.status.value})."
            ),
        )

    was_live = experiment.status == ExperimentStatus.LANDING_LIVE
    experiment.status = ExperimentStatus.LANDING_GENERATING
    await db.commit()

    try:
        await landing_page_dispatcher.dispatch(
            experiment_id,
            body.page_goal,
            body.template_id,
            body.regeneration_hint,
            was_live,
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
# Sub-resource reads and mutations (must register before GET /{experiment_id})
# ---------------------------------------------------------------------------


async def _load_owned_validation_report(
    db: AsyncSession,
    experiment_id: UUID,
    user_id: UUID,
) -> ValidationReport:
    """Load a ValidationReport row after verifying the caller owns the experiment.

    Ownership failure returns the same 404 as a non-existent experiment (never
    reveal existence for another user, per AGENTS.md).
    """
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    report_result = await db.execute(
        select(ValidationReport).where(ValidationReport.experiment_id == experiment_id),
    )
    report = report_result.scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Validation report not found"
        )
    return report


@router.get(
    "/{experiment_id}/validation-report",
    response_model=ValidationReportResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_validation_report(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ValidationReportResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    report_result = await db.execute(
        select(ValidationReport).where(ValidationReport.experiment_id == experiment_id),
    )
    report = report_result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation report not found")

    return ValidationReportSchema.model_validate(report.raw_report)


@router.get(
    "/{experiment_id}/validation-report/edited-doc",
    response_model=EditedDocResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_validation_report_edited_doc(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EditedDocResponse:
    report = await _load_owned_validation_report(db, experiment_id, current_user.id)
    return EditedDocResponse(**build_edited_doc_response(report))


@router.patch(
    "/{experiment_id}/validation-report/edited-doc",
    response_model=EditedDocResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def patch_validation_report_edited_doc(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: EditedDocPatchRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EditedDocResponse:
    report = await _load_owned_validation_report(db, experiment_id, current_user.id)
    try:
        apply_edited_doc_patch(report, doc=body.doc, base_version=body.base_version)
    except EditedDocVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "edited_doc_version conflict", "current_version": exc.current_version},
        ) from exc
    await db.commit()
    await db.refresh(report)
    return EditedDocResponse(**build_edited_doc_response(report))


@router.post(
    "/{experiment_id}/evidence-chat",
    response_model=EvidenceChatSendResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def send_evidence_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: EvidenceChatSendRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceChatSendResponse:
    try:
        result = await send_evidence_chat_message(
            db,
            current_user,
            experiment_id,
            body.message,
            selection_text=body.selection_text,
            selection_question_id=body.selection_question_id,
            parent_message_id=body.parent_message_id,
        )
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    except EvidenceChatInvalidTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        _logger.error(
            "evidence chat turn failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evidence chat failed, please try again",
        ) from exc
    return EvidenceChatSendResponse(
        user_message=ChatMessageItem.from_orm_message(result.user_message),
        assistant_message=ChatMessageItem.from_orm_message(result.assistant_message),
        thread_id=result.thread_id,
    )


def _evidence_items_with_siblings(
    messages: list,
    sibling_info: dict[str, dict[str, int]],
) -> list[ChatMessageItem]:
    """Build ChatMessageItems, merging per-message sibling position when present."""
    items: list[ChatMessageItem] = []
    for msg in messages:
        info = sibling_info.get(str(msg.id))
        if info is not None:
            items.append(
                ChatMessageItem.from_orm_message(
                    msg,
                    sibling_count=info["sibling_count"],
                    sibling_index=info["sibling_index"],
                )
            )
        else:
            items.append(ChatMessageItem.from_orm_message(msg))
    return items


@router.get(
    "/{experiment_id}/evidence-chat/messages",
    response_model=EvidenceChatMessagesResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_evidence_chat_messages(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceChatMessagesResponse:
    try:
        result = await list_evidence_chat_messages(db, current_user, experiment_id)
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    return EvidenceChatMessagesResponse(
        thread_id=result.thread_id,
        experiment_id=experiment_id,
        active_leaf_message_id=result.active_leaf_message_id,
        messages=_evidence_items_with_siblings(result.messages, result.sibling_info),
        sibling_info=result.sibling_info,
    )


@router.post(
    "/{experiment_id}/evidence-chat/messages/{assistant_message_id}/regenerate",
    response_model=EvidenceChatRegenerateResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def regenerate_evidence_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    assistant_message_id: UUID,
    body: EvidenceChatRegenerateRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceChatRegenerateResponse:
    try:
        result = await regenerate_evidence_chat_message(
            db,
            current_user,
            experiment_id,
            assistant_message_id,
            selection_text=body.selection_text,
            selection_question_id=body.selection_question_id,
        )
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from None
    except EvidenceChatInvalidTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        _logger.error(
            "evidence chat regenerate failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evidence chat regenerate failed, please try again",
        ) from exc
    return EvidenceChatRegenerateResponse(
        assistant_message=ChatMessageItem.from_orm_message(result.assistant_message),
        thread_id=result.thread_id,
    )


@router.post(
    "/{experiment_id}/evidence-chat/messages/{message_id}/feedback",
    response_model=EvidenceChatFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def submit_evidence_chat_feedback(
    request: Request,
    response: Response,
    experiment_id: UUID,
    message_id: UUID,
    body: EvidenceChatFeedbackRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceChatFeedbackResponse:
    try:
        row = await upsert_evidence_chat_feedback(
            db, current_user, experiment_id, message_id, body.verdict
        )
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from None
    except EvidenceChatInvalidTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return EvidenceChatFeedbackResponse(message_id=row.message_id, verdict=row.verdict)


@router.post(
    "/{experiment_id}/evidence-chat/stream",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def stream_evidence_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: EvidenceChatSendRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream an evidence-chat reply as SSE (token/done/error frames).

    The user message is persisted + committed here (request session) BEFORE the
    stream starts, so a mid-stream disconnect never loses it. The generator owns
    the assistant persist + LLMCall accounting on its own session.
    """
    try:
        prep = await prepare_evidence_stream(
            db,
            current_user,
            experiment_id,
            body.message,
            selection_text=body.selection_text,
            selection_question_id=body.selection_question_id,
            parent_message_id=body.parent_message_id,
        )
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    except EvidenceChatInvalidTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return StreamingResponse(
        stream_evidence_reply(prep),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{experiment_id}/evidence-chat/messages/{user_message_id}/edit",
    response_model=EvidenceChatEditResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def edit_evidence_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    user_message_id: UUID,
    body: EvidenceChatEditRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceChatEditResponse:
    """Edit a user message: branch a sibling, re-answer, move the active leaf."""
    try:
        result = await edit_evidence_chat_message(
            db,
            current_user,
            experiment_id,
            user_message_id,
            body.content,
            selection_text=body.selection_text,
            selection_question_id=body.selection_question_id,
        )
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from None
    except EvidenceChatInvalidTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        _logger.error(
            "evidence chat edit failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evidence chat edit failed, please try again",
        ) from exc
    return EvidenceChatEditResponse(
        new_user_message=ChatMessageItem.from_orm_message(result.new_user_message),
        new_assistant_message=ChatMessageItem.from_orm_message(
            result.new_assistant_message
        ),
        thread_id=result.thread_id,
        active_leaf_message_id=result.active_leaf_message_id,
        sibling_info=result.sibling_info,
    )


@router.post(
    "/{experiment_id}/evidence-chat/messages/{message_id}/activate",
    response_model=EvidenceChatActivateResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def activate_evidence_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    message_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvidenceChatActivateResponse:
    """Switch the active branch to the leaf of the branch containing message_id."""
    try:
        result = await activate_evidence_chat_branch(
            db, current_user, experiment_id, message_id
        )
    except EvidenceChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from None
    except EvidenceChatInvalidTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return EvidenceChatActivateResponse(
        thread_id=result.thread_id,
        active_leaf_message_id=result.active_leaf_message_id,
    )


@router.post(
    "/{experiment_id}/chat/universal",
    response_model=UniversalChatSendResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def send_universal_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: UniversalChatSendRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UniversalChatSendResponse:
    try:
        result = await send_universal_chat_message(
            db,
            current_user,
            experiment_id,
            body.message,
            attachment_ids=body.attachment_ids,
            current_open_phase=body.current_open_phase,
            mcq_answer=body.mcq_answer,
        )
    except UniversalChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    except UniversalChatUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ChatAttachmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ChatAttachmentAccessError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more attachments are invalid or expired.",
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        _logger.error(
            "universal chat turn failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Universal chat failed, please try again",
        ) from exc
    return UniversalChatSendResponse(
        user_message=ChatMessageItem.from_orm_message(result.user_message),
        assistant_message=ChatMessageItem.from_orm_message(result.assistant_message),
        messages=[
            ChatMessageItem.from_orm_message(message) for message in result.messages
        ],
        thread_id=result.thread_id,
    )


@router.post(
    "/{experiment_id}/chat/universal/stream",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def stream_universal_chat(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: UniversalChatSendRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream a universal-chat turn as SSE (tool_call/tool_result/tokens/done/error).

    User message is persisted + committed on the request session before the
    generator starts. The generator owns tool/assistant rows on its own session.
    """
    try:
        prep = await prepare_universal_stream(
            db,
            current_user,
            experiment_id,
            body.message,
            attachment_ids=body.attachment_ids,
            current_open_phase=body.current_open_phase,
            mcq_answer=body.mcq_answer,
            replace_message_id=body.replace_message_id,
            kick=body.kick,
        )
    except UniversalChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    except UniversalChatUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ChatAttachmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ChatAttachmentAccessError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more attachments are invalid or expired.",
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # Detach work before the StreamingResponse is consumed so a fast disconnect
    # cannot prevent the turn task from starting.
    start_universal_turn(prep)

    async def _frames():
        async for event_name, payload in stream_universal_chat_message(prep):
            if event_name.startswith("_"):
                continue
            yield format_sse_event(event_name, payload)

    return StreamingResponse(
        _frames(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{experiment_id}/chat/universal/cancel",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def cancel_universal_chat_turn(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: UniversalChatCancelRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, bool]:
    """Explicit stop — does not run on reload/disconnect."""
    try:
        cancelled = await cancel_universal_turn(
            db, current_user, experiment_id, body.turn_id
        )
    except UniversalChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    return {"cancelled": cancelled}


@router.get(
    "/{experiment_id}/chat/universal/messages",
    response_model=UniversalChatMessagesResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_universal_chat_messages(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UniversalChatMessagesResponse:
    try:
        result = await list_universal_chat_messages(db, current_user, experiment_id)
    except UniversalChatNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        ) from None
    return UniversalChatMessagesResponse(
        thread_id=result.thread_id,
        experiment_id=experiment_id,
        active_leaf_message_id=result.active_leaf_message_id,
        messages=[ChatMessageItem.from_orm_message(m) for m in result.messages],
        in_progress_turn_id=result.in_progress_turn_id,
    )


@router.get(
    "/{experiment_id}/landing-page",
    response_model=LandingPageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    return LandingPageResponse.model_validate(landing_page)


@router.post(
    "/{experiment_id}/landing-page/logo",
    response_model=LogoUploadResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def upload_landing_page_logo_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LogoUploadResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    _ensure_landing_page_editable(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    if lp_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    file_bytes = await file.read()
    try:
        result = upload_landing_page_logo(
            experiment_id=experiment_id,
            user_id=current_user.id,
            file_bytes=file_bytes,
        )
    except LogoUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error(
            "logo upload failed",
            experiment_id=str(experiment_id),
            user_id=str(current_user.id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Logo upload failed. Try again or paste an image URL.",
        ) from exc

    logo_url = result.logo_url
    if logo_url.startswith("/"):
        logo_url = str(request.base_url).rstrip("/") + logo_url

    return LogoUploadResponse(logo_url=logo_url, filename=result.filename)


@router.post(
    "/{experiment_id}/landing-page/section-image",
    response_model=SectionImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def upload_landing_page_section_image_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SectionImageUploadResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    _ensure_landing_page_editable(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    if lp_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    file_bytes = await file.read()
    try:
        result = upload_landing_page_section_image(
            experiment_id=experiment_id,
            user_id=current_user.id,
            file_bytes=file_bytes,
        )
    except LogoUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error(
            "section image upload failed",
            experiment_id=str(experiment_id),
            user_id=str(current_user.id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image upload failed. Try again with a smaller PNG, JPEG, or WebP file.",
        ) from exc

    image_url = result.image_url
    if image_url.startswith("/"):
        image_url = str(request.base_url).rstrip("/") + image_url

    return SectionImageUploadResponse(image_url=image_url, filename=result.filename)


@router.get(
    "/{experiment_id}/landing-page/slug-availability",
    response_model=LandingPageSlugAvailabilityResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def check_landing_page_slug_availability(
    request: Request,
    response: Response,
    experiment_id: UUID,
    slug: Annotated[str, Query(min_length=1, max_length=40)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageSlugAvailabilityResponse:
    """Check whether a slug is free for this landing page.

    Compares against all landing pages in the database (unique constraint).
    ``taken_by_live`` is true when another *published* page already uses the slug.
    """
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    try:
        normalized = validate_landing_slug(slug)
    except ValueError as exc:
        return LandingPageSlugAvailabilityResponse(
            slug=slug.strip().lower(),
            available=False,
            taken_by_live=False,
            message=str(exc),
        )

    existing_result = await db.execute(
        select(LandingPage).where(LandingPage.slug == normalized),
    )
    existing = existing_result.scalar_one_or_none()
    if existing is None or existing.id == landing_page.id:
        return LandingPageSlugAvailabilityResponse(
            slug=normalized,
            available=True,
            taken_by_live=False,
            message="This URL is available.",
        )

    taken_by_live = existing.live_at is not None
    message = (
        "This URL is already used by a live published page."
        if taken_by_live
        else "This URL is already taken by another project."
    )
    return LandingPageSlugAvailabilityResponse(
        slug=normalized,
        available=False,
        taken_by_live=taken_by_live,
        message=message,
    )


@router.patch(
    "/{experiment_id}/landing-page",
    response_model=LandingPageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def patch_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: LandingPagePatchRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    _ensure_landing_page_editable(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    previous_slug = landing_page.slug

    if body.template_id is not None:
        landing_page.template_id = body.template_id
    if body.copy_json is not None:
        landing_page.copy_json = body.copy_json
    if body.page_json is not None:
        landing_page.page_json = body.page_json
    if body.slug is not None:
        try:
            normalized_slug = validate_landing_slug(body.slug)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        conflict_result = await db.execute(
            select(LandingPage).where(
                LandingPage.slug == normalized_slug,
                LandingPage.id != landing_page.id,
            ),
        )
        if conflict_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This URL is already taken. Choose a different slug.",
            )
        landing_page.slug = normalized_slug

    await db.commit()
    await db.refresh(landing_page)

    if landing_page.live_at is not None and experiment.status != ExperimentStatus.ARCHIVED:
        await notify_live_landing_page_changed(
            db,
            landing_page,
            previous_slug=previous_slug,
        )

    return LandingPageResponse.model_validate(landing_page)


@router.post(
    "/{experiment_id}/landing-page/publish",
    response_model=PublishResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def publish_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    _body: PublishLandingPageRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PublishResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    if experiment.status != ExperimentStatus.LANDING_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment must be in LANDING_DRAFT status to publish the landing page",
        )

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    existing_cohort = (
        await db.execute(
            select(LandingPagePublish.id).where(
                LandingPagePublish.landing_page_id == landing_page.id,
            ).limit(1),
        )
    ).scalar_one_or_none()
    if existing_cohort is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Landing page already has a publish cohort; "
                "use POST …/landing-page/republish to start a new cohort"
            ),
        )

    now = datetime.now(timezone.utc)
    landing_page.live_at = now
    experiment.status = ExperimentStatus.LANDING_LIVE
    cohort = await create_first_cohort(db, landing_page.id)
    await db.commit()
    await db.refresh(landing_page)

    await notify_live_landing_page_changed(db, landing_page)

    public_url = build_public_landing_page_url(landing_page.slug)
    return PublishResponse(
        message="Landing page published",
        slug=landing_page.slug,
        public_url=public_url,
        publish_number=cohort.publish_number,
    )


@router.post(
    "/{experiment_id}/landing-page/republish",
    response_model=PublishResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def republish_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PublishResponse:
    """Close the current Signal cohort and open a new one. Does not change live_at/status."""
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    if experiment.status != ExperimentStatus.LANDING_LIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment must be in LANDING_LIVE status to republish",
        )

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None or landing_page.live_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Landing page not found or not live",
        )

    open_cohort = await get_open_cohort(db, landing_page.id)
    if open_cohort is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No open publish cohort to close; publish first",
        )

    try:
        new_cohort = await close_and_open_next_cohort(db, landing_page.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No open publish cohort to close; publish first",
        ) from None

    await db.commit()

    public_url = build_public_landing_page_url(landing_page.slug)
    return PublishResponse(
        message="Landing page republished",
        slug=landing_page.slug,
        public_url=public_url,
        publish_number=new_cohort.publish_number,
    )


@router.get(
    "/{experiment_id}/metrics-access",
    response_model=MetricsAccessResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_metrics_access(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MetricsAccessResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    unlocked = await has_purchased_service_for_experiment(
        db,
        user_id=current_user.id,
        service="metricsAnalysis",
        experiment_id=experiment_id,
    )
    return MetricsAccessResponse(unlocked=unlocked)


@router.post(
    "/{experiment_id}/unlock-metrics",
    response_model=UnlockMetricsResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def unlock_metrics(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UnlockMetricsResponse:
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None or landing_page.live_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not available until the landing page is published",
        )
    _ensure_metrics_access_allowed(experiment, live_at=landing_page.live_at)

    try:
        _tx, already_unlocked = await purchase_service_for_experiment(
            db,
            user_id=current_user.id,
            service="metricsAnalysis",
            experiment_id=experiment_id,
        )
    except InsufficientCredits as exc:
        raise insufficient_credits_http(exc) from exc

    await db.commit()
    wallet = await get_or_create_wallet(db, current_user.id)
    return UnlockMetricsResponse(
        unlocked=True,
        already_unlocked=already_unlocked,
        credits_balance=wallet.credits_balance,
    )


@router.get(
    "/{experiment_id}/analytics",
    response_model=AnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_experiment_analytics(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    publish_id: Annotated[UUID | None, Query()] = None,
    include_all: Annotated[bool, Query(alias="all")] = False,
) -> AnalyticsResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    if not await has_purchased_service_for_experiment(
        db,
        user_id=current_user.id,
        service="metricsAnalysis",
        experiment_id=experiment_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "metrics_not_unlocked",
                "required": SERVICE_PRICING["metricsAnalysis"],
            },
        )

    try:
        built = await build_analytics_aggregate(
            db,
            experiment_id,
            publish_id=publish_id,
            include_all_publishes=include_all,
        )
    except LandingPageNotLiveError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not available until the landing page is published",
        ) from None

    threshold = await compute_insight_threshold(db, experiment_id)
    aggregate = built.aggregate

    return AnalyticsResponse(
        total_page_views=aggregate.total_page_views,
        total_signups=aggregate.total_signups,
        unique_visitors=aggregate.unique_visitors,
        conversion_rate=aggregate.conversion_rate,
        views_by_source=aggregate.views_by_source,
        signups_by_source=aggregate.signups_by_source,
        conversion_rate_by_source=aggregate.conversion_rate_by_source,
        signups_by_location=aggregate.signups_by_location,
        days_live=aggregate.days_live,
        publish_number=built.publish_number,
        total_publishes=built.total_publishes,
        insight_threshold_met=threshold.met,
        insight_progress=InsightProgress(
            views_current=threshold.views_current,
            views_target=threshold.views_target,
            signups_current=threshold.signups_current,
            signups_target=threshold.signups_target,
            days_current=threshold.days_current,
            days_target=threshold.days_target,
        ),
    )


def _waitlist_export_filename(experiment: Experiment) -> str:
    base = (experiment.name or experiment.slug or str(experiment.id)).strip()
    safe = _WAITLIST_EXPORT_FILENAME_RE.sub("-", base).strip("-._") or "experiment"
    return f"{safe[:80]}-waitlist.csv"


@router.get(
    "/{experiment_id}/waitlist/export",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def export_experiment_waitlist(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    # Historical view: all signups across publish cohorts (include_all_publishes).
    # Cohort filtering is for Signal analytics / insight only — not waitlist export.
    signups_result = await db.execute(
        select(WaitlistSignup)
        .where(WaitlistSignup.experiment_id == experiment_id)
        .order_by(WaitlistSignup.ts.desc()),
    )
    signups = list(signups_result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "source_tag", "city", "region", "country", "signed_up_at"])
    for signup in signups:
        writer.writerow(
            [
                signup.email,
                signup.source_tag or "",
                signup.geo_city or "",
                signup.geo_region or "",
                signup.geo_country or "",
                signup.ts.isoformat(),
            ]
        )

    filename = _waitlist_export_filename(experiment)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{experiment_id}/waitlist",
    response_model=WaitlistSignupsResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def list_experiment_waitlist(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WaitlistSignupsResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    # Historical view across all publish cohorts (same decision as waitlist export).
    signups_result = await db.execute(
        select(WaitlistSignup)
        .where(WaitlistSignup.experiment_id == experiment_id)
        .order_by(WaitlistSignup.ts.desc()),
    )
    signups = list(signups_result.scalars().all())

    return WaitlistSignupsResponse(
        signups=[
            WaitlistSignupItem(
                id=signup.id,
                email=signup.email,
                source_tag=signup.source_tag,
                geo_city=signup.geo_city,
                geo_region=signup.geo_region,
                geo_country=signup.geo_country,
                created_at=signup.ts,
            )
            for signup in signups
        ],
        total=len(signups),
    )


@router.get(
    "/{experiment_id}/insight-report",
    response_model=InsightReportResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_insight_report(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InsightReportResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    report_result = await db.execute(
        select(InsightReport).where(InsightReport.experiment_id == experiment_id),
    )
    report = report_result.scalar_one_or_none()
    if report is None or report.raw_output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight report not found")

    return InsightReportResponse.model_validate(report.raw_output)


@router.delete(
    "/{experiment_id}",
    response_model=DeleteExperimentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def delete_experiment_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: DeleteExperimentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DeleteExperimentResponse:
    """Permanently delete a project. Requires body ``{"confirmation": "CONFIRM"}``."""
    if body.confirmation != "CONFIRM":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Type "CONFIRM" exactly to delete this project',
        )

    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    await delete_experiment(db, experiment)
    await db.commit()

    return DeleteExperimentResponse(experiment_id=experiment_id)


@router.put(
    "/{experiment_id}/founder-decision",
    response_model=FounderDecisionResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def record_founder_decision(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: RecordFounderDecisionRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FounderDecisionResponse:
    """Record or amend the founder's Signal decision (CAS on version).

    Does not archive and does not change experiment.status. Rejects ARCHIVED.
    """
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )
    try:
        apply_founder_decision(
            experiment,
            decision=body.decision,
            note=body.note,
            base_version=body.base_version,
        )
    except FounderDecisionArchivedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot record a decision on an archived experiment",
        ) from exc
    except FounderDecisionVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "founder_decision_version conflict",
                "current_version": exc.current_version,
            },
        ) from exc

    await db.commit()
    await db.refresh(experiment)

    assert experiment.founder_decision is not None
    assert experiment.founder_decision_at is not None
    assert experiment.founder_decision_version is not None

    return FounderDecisionResponse(
        founder_decision=experiment.founder_decision,
        founder_decision_at=experiment.founder_decision_at,
        founder_decision_note=experiment.founder_decision_note,
        founder_decision_version=experiment.founder_decision_version,
    )


@router.post(
    "/{experiment_id}/archive",
    response_model=ArchiveExperimentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def archive_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: ArchiveRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArchiveExperimentResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    if experiment.status == ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment is already archived",
        )

    experiment.status = ExperimentStatus.ARCHIVED
    await db.commit()

    return ArchiveExperimentResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.ARCHIVED,
    )


@router.post(
    "/{experiment_id}/unarchive",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def unarchive_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    result = await db.execute(
        select(Experiment)
        .options(
            selectinload(Experiment.validation_report),
            selectinload(Experiment.landing_page),
            selectinload(Experiment.insight_report),
        )
        .where(Experiment.id == experiment_id),
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    if experiment.status != ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment is not archived",
        )

    experiment.status = infer_status_after_unarchive(experiment)
    await db.commit()

    return await _build_experiment_detail_response(db, experiment)


@router.post(
    "/{experiment_id}/chat/universal/capture-greeting/stream",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def stream_capture_greeting(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Seed + stream the pre-capture greeting (template tokens; no LLM).

    Idempotent: if the greeting already exists, streams the existing text then
    done. Capture card should appear only after the client receives ``done``.
    """
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    try:
        greeting, created = await ensure_capture_greeting(
            db, experiment=experiment, user=current_user
        )
    except CaptureGreetingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    text = greeting.content or ""
    message_id = str(greeting.id)
    thread_id = str(greeting.thread_id)

    async def _frames():
        yield format_sse_event(
            "turn_started",
            {
                "message_id": message_id,
                "thread_id": thread_id,
                "created": created,
            },
        )
        async for chunk in stream_capture_greeting_tokens(text):
            yield format_sse_event("assistant_token", {"text": chunk})
            # Light pacing so the dock can paint tokens.
            await asyncio.sleep(0.012)
        yield format_sse_event(
            "done",
            {
                "assistant_message_id": message_id,
                "thread_id": thread_id,
                "user_message_id": None,
            },
        )

    return StreamingResponse(
        _frames(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{experiment_id}/capture-idea",
    response_model=CaptureIdeaResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def capture_experiment_idea(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: CaptureIdeaRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CaptureIdeaResponse:
    """Freeze the immutable original idea + attachments, suggest a palette."""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    try:
        captured = await capture_original_idea(
            db,
            experiment=experiment,
            user_id=current_user.id,
            idea_text=body.idea_text,
            attachment_ids=body.attachment_ids,
        )
    except IdeaAlreadyCapturedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc
    except IdeaCaptureValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    return CaptureIdeaResponse(
        experiment_id=captured.experiment_id,
        original_idea=captured.original_idea,
        original_idea_captured_at=captured.original_idea_captured_at,
        suggested_palette=captured.suggested_palette,
        frozen_attachments=[
            CaptureIdeaFrozenAttachment(
                id=att.id,
                original_filename=att.original_filename,
                content_kind=att.content_kind,
            )
            for att in captured.frozen_attachments
        ],
        user_message_id=captured.user_message_id,
    )


@router.patch(
    "/{experiment_id}/name",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def rename_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: RenameExperimentRequest,
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

    stripped = body.name.strip()
    if not stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name must not be empty",
        )

    experiment.name = stripped

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is not None:
        landing_page.page_json = sync_landing_page_project_name(
            landing_page.page_json if isinstance(landing_page.page_json, dict) else {},
            stripped,
        )

    await db.commit()

    return await _build_experiment_detail_response(db, experiment)


@router.patch(
    "/{experiment_id}/theme",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def set_experiment_theme(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: SetExperimentThemeRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    """Activate a curated canvas palette for this experiment (null = default)."""
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment_id),
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )

    experiment.theme_palette = body.palette_name
    await db.commit()
    # commit releases the connection; the detail builder fans out with
    # asyncio.gather, which cannot re-provision one concurrently.
    await db.refresh(experiment)

    return await _build_experiment_detail_response(db, experiment)


@router.patch(
    "/{experiment_id}/tags",
    response_model=ExperimentListItemResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def update_experiment_tags(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: UpdateExperimentTagsRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExperimentListItemResponse:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    try:
        validated = validate_tags(body.tags)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if len(validated) < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one tag is required",
        )

    experiment.tags = validated
    await db.commit()
    await db.refresh(experiment)

    stats_map = await build_experiment_card_stats_map(
        db,
        [experiment],
        user_id=current_user.id,
    )
    base = ExperimentResponse.model_validate(experiment)
    return ExperimentListItemResponse(
        **base.model_dump(),
        card_stats=stats_map.get(experiment.id),
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

    return await _build_experiment_detail_response(db, experiment)
