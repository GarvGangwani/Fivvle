"""Founder-supplied targeting signals for research pipeline phases."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ExperimentStage


class ExperimentTargeting(BaseModel):
    """Founder-supplied targeting signals passed to pipeline phases.

    All fields nullable — a fully-null instance is valid and signals
    'no targeting captured; use default (unscoped) behavior.'
    """

    model_config = ConfigDict(from_attributes=True)

    target_geography: str | None = None
    audience_bracket: str | None = Field(
        default=None,
        description=(
            "Coarse founder-declared audience bracket (e.g. 'urban middle-class "
            "families in tier-1 cities'). Distinct from RefinedIdea.target_audience, "
            "which is the LLM-generated vivid portrait from refinement."
        ),
    )
    stage: ExperimentStage | None = None
    why_now: str | None = None

    def has_signal(self) -> bool:
        return any(
            v is not None
            for v in (
                self.target_geography,
                self.audience_bracket,
                self.stage,
                self.why_now,
            )
        )

    def has_geography(self) -> bool:
        return (
            self.target_geography is not None
            and self.target_geography.strip() != ""
        )

    @classmethod
    def from_experiment(cls, exp: object) -> ExperimentTargeting:
        return cls(
            target_geography=getattr(exp, "target_geography", None),
            audience_bracket=getattr(exp, "audience_bracket", None),
            stage=getattr(exp, "stage", None),
            why_now=getattr(exp, "why_now", None),
        )
