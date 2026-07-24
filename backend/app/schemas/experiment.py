"""Pydantic request/response schemas for Experiment endpoints.

ExperimentResponse serialises the SQLAlchemy Experiment ORM model for the API.
The model_config = ConfigDict(from_attributes=True) allows FastAPI to call
model_validate() on the ORM object directly.

refined_idea is stored as JSONB (dict | None) in the DB. Pydantic v2 with
from_attributes=True will coerce the dict into a RefinedIdea instance when
serialising — this matches the shape displayed in the refinement review form (FE3).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ExperimentStage, ExperimentStatus, FounderDecision
from app.schemas.refinement import RefinedIdea


class CreateExperimentRequest(BaseModel):
    """Body for POST /experiments — name-only Spark create.

    Idea text is captured later on the canvas Spark node. The 50-char
    raw_idea minimum is enforced when Refine starts, not at creation.
    """

    name: str = Field(
        min_length=3,
        max_length=100,
        description="Project name for the new validation.",
    )
    raw_idea: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional. Prefer empty at create; edit via PATCH /spark.",
    )


class PatchSparkRequest(BaseModel):
    """Body for PATCH /experiments/{id}/spark — update raw idea."""

    raw_idea: str = Field(
        max_length=2000,
        description="Spark idea text. Empty string allowed until Refine starts.",
    )


class RenameExperimentRequest(BaseModel):
    """Body for PATCH /experiments/{id}/name."""

    name: str = Field(
        max_length=100,
        description="User-defined project name (1-100 characters).",
    )


class RegenerateRefinementRequest(BaseModel):
    """Body for POST /experiments/{id}/refine — request a new refinement pass."""

    feedback: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Optional guidance for the regeneration — what to change, "
            "emphasise, or reconsider."
        ),
    )


class ExperimentResponse(BaseModel):
    """API response shape for Experiment.

    Used by both POST /experiments (201) and POST /experiments/{id}/refine (200).
    from_attributes=True lets Pydantic read directly from the SQLAlchemy ORM object.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    slug: str | None
    name: str | None
    raw_idea: str
    refined_idea: RefinedIdea | None
    target_geography: str | None = None
    audience_bracket: str | None = None
    stage: ExperimentStage | None = None
    why_now: str | None = None
    status: ExperimentStatus
    refinement_count: int
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ExperimentCardStats(BaseModel):
    """Lightweight behavioral metrics for dashboard project cards."""

    page_views: int = Field(ge=0)
    waitlist_signups: int = Field(ge=0)


class ExperimentListItemResponse(ExperimentResponse):
    """GET /experiments list item — behavioral metrics when metrics are unlocked."""

    card_stats: ExperimentCardStats | None = None


class ConfirmResearchResponse(BaseModel):
    """202 response for POST /experiments/{id}/confirm.

    status_url is the absolute path to the polling endpoint so clients
    can start polling without constructing the URL themselves.
    credits_balance is the wallet balance after any debit for this request.
    """

    experiment_id: UUID
    status: ExperimentStatus
    status_url: str
    credits_balance: int = Field(ge=0)


class ResearchStatusResponse(BaseModel):
    """Response for GET /experiments/{id}/research-status.

    phase_label: human-readable string from research_phase_mapping.get_phase_label().
        None for non-research statuses and terminal states (RESEARCH_READY,
        RESEARCH_FAILED) where the frontend shows a different component.

    phases_completed: ordered list of ExperimentStatus values the experiment
        has passed through in the current research run.  Determined server-side
        from the current status rather than stored separately — avoids a
        separate audit log table for B2.4.

    error_detail: populated only when status == RESEARCH_FAILED.
        Sanitized by the state machine; safe to surface in the UI.
    """

    status: ExperimentStatus
    phase_label: str | None
    phases_completed: list[ExperimentStatus]
    last_updated_at: datetime
    error_detail: str | None


class ExperimentCanvasDetailFields(BaseModel):
    """Extra fields on GET /experiments/{id} for the experiment canvas."""

    model_config = ConfigDict(extra="forbid")

    refined_idea: str | None = None
    chat_message_count: int = Field(default=0, ge=0)
    evidence_atom_count: int = Field(default=0, ge=0)
    landing_page_view_count: int = Field(default=0, ge=0)
    resource_count: int = Field(default=0, ge=0)
    demand_score: int | None = Field(default=None, ge=0, le=100)
    # Research validation overall_recommendation (NOT the founder's Signal decision).
    verdict: str | None = None
    founder_decision: FounderDecision | None = None
    founder_decision_at: datetime | None = None
    founder_decision_note: str | None = None
    founder_decision_version: int | None = Field(default=None, ge=1)
