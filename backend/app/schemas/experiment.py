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

from app.db.enums import ExperimentStatus
from app.schemas.refinement import RefinedIdea


class CreateExperimentRequest(BaseModel):
    """Body for POST /experiments — founder submits their raw startup idea.

    Field constraints mirror the service-layer validation in experiment_service.py
    and the USER_FLOW Stage 2 guidance ("2-5 sentences in their own words").
    FastAPI validates this at request-parse time (returns 422 on failure);
    the service also validates defensively (returns 400 on whitespace-only inputs).
    """

    raw_idea: str = Field(
        min_length=50,
        max_length=2000,
        description=(
            "The founder's raw idea. Describe the problem, who it is for, "
            "and the proposed solution. 2-5 sentences."
        ),
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
    raw_idea: str
    refined_idea: RefinedIdea | None
    status: ExperimentStatus
    refinement_count: int
    created_at: datetime
    updated_at: datetime
