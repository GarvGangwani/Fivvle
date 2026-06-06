"""Insight generator schemas — contracts for analytics aggregation and LLM output.

These schemas are the data contract for the B4 insight generator (planning doc
``docs/planning/b4-insight-generator.md`` §4). The analytics aggregator
produces ``AnalyticsAggregate``; the insight LLM emits ``InsightReportOutputDraft``;
the insight service validates citations and hydrates to ``InsightReportOutput``
before persisting JSONB columns on ``InsightReport``.

Two-tier design (mirrors ``validation_report.py`` and ``reader.py`` Draft-vs-Final
pattern):

  Draft types (TrafficSummaryDraft, ConversionSourceCommentaryDraft,
  ConversionBySourceDraft, ResearchTakeawayDraft, InsightReportOutputDraft)
  are the LLM-facing shapes. Pydantic validates structure, length caps, and
  literal enums only — no cross-reference against ValidationReport finding IDs.

  Final types (TrafficSummary, ConversionSourceCommentary, ConversionBySource,
  ResearchTakeaway, InsightReportOutput) are the post-service-validation shapes.
  Field shapes are identical to Draft; the distinction is semantic (parsed but
  not citation-validated vs validated). Citation-ID resolution lives in the
  insight service layer (planning doc §4.3), mirroring the reader service's
  URL/quote guards in ``backend/app/services/reader_service.py``.

``AnalyticsAggregate`` is NOT a Draft/Final pair — it is an internal Python
contract for what the analytics aggregator produces and the LLM consumes
(planning doc §4.1). The LLM never emits it.

Per AGENTS.md "Input and output handling":
  LLM-generated content rendered in the frontend must be treated as untrusted
  text. This schema is the boundary where we enforce that all LLM output is
  parsed and validated before reaching any consumer.

Per AGENTS.md "LLM and agent security":
  Every ResearchTakeaway requires ``cited_finding_ids`` with min_length=1.
  This is the structural anti-hallucination guardrail; the service layer
  additionally verifies each ID exists in the ValidationReport (§4.3).

Per .cursorrules Quality Discipline:
  Confidence labels and source-type labels are mandatory on every claim.
  Non-obviousness is the quality target — schemas enforce presence, not prose.

All char-limit caps are first-pass estimates per ``docs/llm-schema-calibration.md``
and MUST be re-calibrated to observed-max + 10–15% after insight generator
N=5 calibration (planning doc §10). Do not treat them as final.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.enums import InsightRecommendation

ConfidenceLabel = Literal["high", "medium", "low"]
SourceType = Literal["BEHAVIORAL", "COGNITIVE", "SYNTHESIZED"]

_FindingId = Annotated[str, Field(min_length=1, max_length=100)]


class AnalyticsAggregate(BaseModel):
    """Derived analytics input to the insight LLM (planning doc §4.1).

    Produced by the analytics aggregator service from page_views, waitlist
    signups, and landing_page metadata. Not LLM-emitted — pure internal
    contract. Derived metrics (conversion_rate_by_source, warm_network_bias_index)
    are computed server-side; the LLM only interprets what we show it.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    days_live: int = Field(ge=0)
    total_page_views: int = Field(ge=0)
    unique_visitors: int = Field(ge=0)
    total_signups: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    views_by_source: dict[str, int]
    signups_by_source: dict[str, int]
    conversion_rate_by_source: dict[str, float]
    warm_network_bias_index: float = Field(ge=0.0, le=1.0)
    time_on_page_p50_seconds: int = Field(ge=0)
    time_on_page_p90_seconds: int = Field(ge=0)
    signups_by_day: list[int]
    views_by_day: list[int]
    drop_off_signals: dict[str, str]
    data_quality_notes: list[str]

    @model_validator(mode="after")
    def _signup_sources_must_have_views(self) -> AnalyticsAggregate:
        """Every source with signups must also appear in views_by_source (§4.1)."""
        missing = set(self.signups_by_source) - set(self.views_by_source)
        if missing:
            raise ValueError(
                f"signups_by_source keys must be a subset of views_by_source; "
                f"missing views for: {sorted(missing)}"
            )
        return self

    @model_validator(mode="after")
    def _day_arrays_match_days_live(self) -> AnalyticsAggregate:
        """Cohort timeline arrays must span exactly days_live entries (§4.1)."""
        if len(self.views_by_day) != self.days_live:
            raise ValueError(
                f"len(views_by_day) must equal days_live ({self.days_live}); "
                f"got {len(self.views_by_day)}"
            )
        if len(self.signups_by_day) != self.days_live:
            raise ValueError(
                f"len(signups_by_day) must equal days_live ({self.days_live}); "
                f"got {len(self.signups_by_day)}"
            )
        return self


class ConversionSourceCommentaryDraft(BaseModel):
    """Per-source conversion commentary — LLM-facing shape (planning doc §4.2).

    One entry per traffic source in ``ConversionBySourceDraft.per_source``.
    Uses a list (not dict) for stable ordering in JSONB serialization.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    source_name: Annotated[str, Field(min_length=1, max_length=100)]
    views: int = Field(ge=0)
    signups: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    commentary: Annotated[str, Field(min_length=20, max_length=400)]
    confidence: ConfidenceLabel


class ConversionSourceCommentary(BaseModel):
    """Per-source conversion commentary — post-validation shape (planning doc §4.2).

    Field shapes identical to ConversionSourceCommentaryDraft. Produced after
    the insight service accepts the LLM output for persistence.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    source_name: Annotated[str, Field(min_length=1, max_length=100)]
    views: int = Field(ge=0)
    signups: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    commentary: Annotated[str, Field(min_length=20, max_length=400)]
    confidence: ConfidenceLabel


class TrafficSummaryDraft(BaseModel):
    """Traffic narrative summary — LLM-facing shape (planning doc §4.2).

    2-3 sentence AI write-up of overall traffic patterns with headline metric,
    confidence label, and source-type attribution.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    narrative: Annotated[str, Field(min_length=50, max_length=600)]
    headline_metric: Annotated[str, Field(min_length=10, max_length=200)]
    confidence: ConfidenceLabel
    confidence_rationale: Annotated[str, Field(min_length=20, max_length=400)]
    source_type: SourceType


class TrafficSummary(BaseModel):
    """Traffic narrative summary — post-validation shape (planning doc §4.2)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    narrative: Annotated[str, Field(min_length=50, max_length=600)]
    headline_metric: Annotated[str, Field(min_length=10, max_length=200)]
    confidence: ConfidenceLabel
    confidence_rationale: Annotated[str, Field(min_length=20, max_length=400)]
    source_type: SourceType


class ConversionBySourceDraft(BaseModel):
    """Per-source conversion breakdown — LLM-facing shape (planning doc §4.2).

    ``per_source`` is a list (not dict) for stable JSONB ordering. Includes
    warm-network bias commentary derived from analytics.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    per_source: list[ConversionSourceCommentaryDraft]
    warm_network_bias_commentary: Annotated[str, Field(min_length=30, max_length=500)]
    confidence: ConfidenceLabel
    confidence_rationale: Annotated[str, Field(min_length=20, max_length=400)]


class ConversionBySource(BaseModel):
    """Per-source conversion breakdown — post-validation shape (planning doc §4.2)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    per_source: list[ConversionSourceCommentary]
    warm_network_bias_commentary: Annotated[str, Field(min_length=30, max_length=500)]
    confidence: ConfidenceLabel
    confidence_rationale: Annotated[str, Field(min_length=20, max_length=400)]


class ResearchTakeawayDraft(BaseModel):
    """Research-backed takeaway — LLM-facing shape (planning doc §4.2).

    Each takeaway cites 1-5 ValidationReport finding IDs. Structural guardrail:
    ``cited_finding_ids`` min_length=1. ID existence validation lives in the
    insight service (planning doc §4.3), not in this schema.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    claim: Annotated[str, Field(min_length=30, max_length=500)]
    cited_finding_ids: Annotated[
        list[_FindingId],
        Field(
            min_length=1,
            max_length=5,
            description=(
                "1-5 finding IDs from the ValidationReport. NEVER zero — every "
                "research takeaway must cite at least one finding. The insight "
                "service verifies each ID exists before persistence (§4.3)."
            ),
        ),
    ]
    source_type: SourceType
    confidence: ConfidenceLabel
    confidence_rationale: Annotated[str, Field(min_length=20, max_length=400)]


class ResearchTakeaway(BaseModel):
    """Research-backed takeaway — post-validation shape (planning doc §4.2).

    Produced after the insight service confirms all ``cited_finding_ids`` resolve
    to ValidationReport findings (planning doc §4.3).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    claim: Annotated[str, Field(min_length=30, max_length=500)]
    cited_finding_ids: Annotated[
        list[_FindingId],
        Field(
            min_length=1,
            max_length=5,
            description=(
                "1-5 validated finding IDs from the ValidationReport. "
                "Confirmed by the insight service before persistence."
            ),
        ),
    ]
    source_type: SourceType
    confidence: ConfidenceLabel
    confidence_rationale: Annotated[str, Field(min_length=20, max_length=400)]


class InsightReportOutputDraft(BaseModel):
    """Full insight report — LLM-facing shape (planning doc §4.2).

    Parsed directly from the insight LLM response. The insight service validates
    citation IDs, then hydrates to InsightReportOutput for DB write. Includes
    ``what_would_change_this`` — forward-looking signpost for the recommendation
    (planning doc §4.2, §5.1).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    traffic_summary: TrafficSummaryDraft
    conversion_by_source: ConversionBySourceDraft
    research_takeaways: Annotated[
        list[ResearchTakeawayDraft],
        Field(
            min_length=3,
            max_length=5,
            description="3-5 research takeaways combining behavioral and cognitive evidence.",
        ),
    ]
    recommendation_type: InsightRecommendation
    recommendation: Annotated[str, Field(min_length=100, max_length=2500)]
    recommendation_confidence: ConfidenceLabel
    recommendation_rationale: Annotated[str, Field(min_length=30, max_length=800)]
    what_would_change_this: Annotated[str, Field(min_length=30, max_length=600)]


class InsightReportOutput(BaseModel):
    """Full insight report — post-validation shape (planning doc §4.2).

    Persisted to InsightReport JSONB columns after citation validation.
    Callers always receive this type from the insight service; Draft never
    leaves the service boundary.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    traffic_summary: TrafficSummary
    conversion_by_source: ConversionBySource
    research_takeaways: Annotated[
        list[ResearchTakeaway],
        Field(
            min_length=3,
            max_length=5,
            description="3-5 validated research takeaways with confirmed finding IDs.",
        ),
    ]
    recommendation_type: InsightRecommendation
    recommendation: Annotated[str, Field(min_length=100, max_length=2500)]
    recommendation_confidence: ConfidenceLabel
    recommendation_rationale: Annotated[str, Field(min_length=30, max_length=800)]
    what_would_change_this: Annotated[str, Field(min_length=30, max_length=600)]
