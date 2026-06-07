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

from app.db.enums import ExperimentStatus
from app.schemas.insight import InsightReportOutput
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
    days_live: int = Field(ge=0)


class ArchiveRequest(BaseModel):
    """POST /experiments/{id}/archive body."""

    model_config = ConfigDict(extra="forbid")

    outcome: Literal["iterate", "proceed", "pivot", "kill"]


class ArchiveExperimentResponse(BaseModel):
    """POST /experiments/{id}/archive response."""

    experiment_id: UUID
    status: ExperimentStatus
