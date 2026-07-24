"""API response and request schemas for experiment sub-resource endpoints.

Kept separate from domain schemas (validation_report, insight, landing_page)
which describe LLM/pipeline contracts. These types describe the HTTP API
surface consumed by the frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.enums import ExperimentStatus, FounderDecision
from app.schemas.insight import InsightReportOutput, SignupLocationBucket
from app.schemas.validation_report import ValidationReport

# Re-export full report shapes the frontend renders directly.
ValidationReportResponse = ValidationReport
InsightReportResponse = InsightReportOutput


class LandingPageResponse(BaseModel):
    """GET/PATCH /experiments/{id}/landing-page response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    slug: str
    template_id: str
    copy_json: dict[str, Any] = Field(default_factory=dict)
    page_json: dict[str, Any] = Field(default_factory=dict)
    headline: str
    subheadline: str | None
    live_at: datetime | None

    @field_validator("copy_json", "page_json", mode="before")
    @classmethod
    def _default_json_dict(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        return value if value is not None else {}


class LandingPagePatchRequest(BaseModel):
    """PATCH /experiments/{id}/landing-page — partial update body."""

    model_config = ConfigDict(extra="forbid")

    template_id: str | None = None
    copy_json: dict[str, Any] | None = None
    page_json: dict[str, Any] | None = None
    slug: str | None = Field(
        default=None,
        description="Public URL slug (6–40 chars, lowercase alphanumeric + hyphens).",
    )


class LandingPageSlugAvailabilityResponse(BaseModel):
    """GET /experiments/{id}/landing-page/slug-availability response."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    available: bool
    taken_by_live: bool = Field(
        description="True when another published (live) landing page uses this slug.",
    )
    message: str | None = None


class LogoUploadResponse(BaseModel):
    """POST /experiments/{id}/landing-page/logo response."""

    logo_url: str
    filename: str


class SectionImageUploadResponse(BaseModel):
    """POST /experiments/{id}/landing-page/section-image response."""

    image_url: str
    filename: str


class PublishLandingPageRequest(BaseModel):
    """POST /experiments/{id}/landing-page/publish — optional publish options."""

    model_config = ConfigDict(extra="ignore")

    slug: str | None = None
    cta_mode: str | None = None
    cta_url: str | None = None


class PublishResponse(BaseModel):
    """POST /experiments/{id}/landing-page/publish response."""

    message: str
    slug: str
    public_url: str


class InsightProgress(BaseModel):
    """Distance-to-threshold fields from ``compute_insight_threshold``."""

    model_config = ConfigDict(extra="forbid")

    views_current: int = Field(ge=0)
    views_target: int = Field(ge=0)
    signups_current: int = Field(ge=0)
    signups_target: int = Field(ge=0)
    days_current: int = Field(ge=0)
    days_target: int = Field(ge=0)


class AnalyticsResponse(BaseModel):
    """GET /experiments/{id}/analytics — live landing page metrics."""

    model_config = ConfigDict(extra="forbid")

    total_page_views: int = Field(ge=0)
    total_signups: int = Field(ge=0)
    unique_visitors: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    views_by_source: dict[str, int]
    signups_by_source: dict[str, int]
    conversion_rate_by_source: dict[str, float]
    signups_by_location: list[SignupLocationBucket] = Field(default_factory=list)
    days_live: int = Field(ge=0)
    insight_threshold_met: bool
    insight_progress: InsightProgress


class MetricsAccessResponse(BaseModel):
    """GET /experiments/{id}/metrics-access — whether metrics were purchased."""

    model_config = ConfigDict(extra="forbid")

    unlocked: bool


class UnlockMetricsResponse(BaseModel):
    """POST /experiments/{id}/unlock-metrics response."""

    model_config = ConfigDict(extra="forbid")

    unlocked: bool
    already_unlocked: bool
    credits_balance: int = Field(ge=0)


class ArchiveRequest(BaseModel):
    """POST /experiments/{id}/archive body."""

    model_config = ConfigDict(extra="forbid")

    outcome: Literal["iterate", "proceed", "pivot", "kill", "manual"]


class ArchiveExperimentResponse(BaseModel):
    """POST /experiments/{id}/archive response."""

    experiment_id: UUID
    status: ExperimentStatus


class RecordFounderDecisionRequest(BaseModel):
    """PUT /experiments/{id}/founder-decision — record or amend a Signal decision.

    base_version implements optimistic concurrency (compare-and-swap), matching
    the edited_doc PATCH pattern. First write uses base_version=0 (row has never
    recorded a decision). Amendments send the version last read.
    """

    model_config = ConfigDict(extra="forbid")

    decision: FounderDecision
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Optional rationale. Cap matches Experiment.why_now.",
    )
    base_version: int = Field(
        ge=0,
        description=(
            "founder_decision_version last read. Must equal the row's current "
            "version (treat NULL as 0) or the write is rejected with 409."
        ),
    )


class FounderDecisionResponse(BaseModel):
    """Persisted founder decision after a successful record/amend."""

    model_config = ConfigDict(extra="forbid")

    founder_decision: FounderDecision
    founder_decision_at: datetime
    founder_decision_note: str | None
    founder_decision_version: int = Field(ge=1)

class DeleteExperimentRequest(BaseModel):
    """DELETE /experiments/{id} body — permanent project removal."""

    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(
        ...,
        description='Must be exactly "CONFIRM" to delete the project',
    )


class DeleteExperimentResponse(BaseModel):
    """DELETE /experiments/{id} response."""

    experiment_id: UUID
    deleted: bool = True


class WaitlistSignupItem(BaseModel):
    """Single waitlist signup in GET /experiments/{id}/waitlist."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    source_tag: str | None
    geo_city: str | None = None
    geo_region: str | None = None
    geo_country: str | None = None
    created_at: datetime


class WaitlistSignupsResponse(BaseModel):
    """GET /experiments/{id}/waitlist response."""

    model_config = ConfigDict(extra="forbid")

    signups: list[WaitlistSignupItem]
    total: int = Field(ge=0)
