"""Reflector schema — decision + per-question re-search specification.

Reflector emits internal pipeline state (not user-facing, not in SynthesizerInput).
Decision schema + per-question re-search specification. Caps are first-pass per
docs/llm-schema-calibration.md. Per ADR 0013, the decision_method is rule_v1 for v1.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.business_construction import EvidenceAnalysisResult

ReflectorDecisionMethod = Literal["rule_v1"]
"""Type alias for the Reflector decision method.

v1 is "rule_v1" (deterministic Python rules, per ADR 0013).
Future v2 will extend this Literal to include "llm_critic_v1" or similar.
Extending requires updating: (1) this alias, (2) the constant set below,
(3) tests covering the new method name.
"""

REFLECTOR_DECISION_METHOD_VALUES: frozenset[str] = frozenset({"rule_v1"})

_ALLOWED_REFLECTOR_TRIGGER_SIGNALS: frozenset[str] = frozenset(
    {"gap_note", "sparse_atoms", "mono_domain"}
)


class QuestionReSearchSpec(BaseModel):
    """One question selected for follow-up search with refined queries."""

    question_id: str = Field(
        ...,
        description=(
            "e.g. 'q1' through 'q7'; matches Planner's ResearchQuestion.id."
        ),
    )
    trigger_signals: list[str] = Field(
        ...,
        min_length=1,
        max_length=8,
        description=(
            "Labels for which §2 disjuncts fired. Allowed values: 'gap_note', "
            "'sparse_atoms', 'mono_domain'. Future versions may add more."
        ),
    )
    refined_queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=4,
        description=(
            "2-3 typical; max 4 first-pass per planning §4 Option B. "
            "Each query bounded to 200 chars."
        ),
    )

    @field_validator("refined_queries")
    @classmethod
    def _validate_refined_queries(cls, v: list[str]) -> list[str]:
        for item in v:
            if not item:
                raise ValueError("refined_queries item must be non-empty")
            if len(item) > 200:
                truncated = item[:40]
                raise ValueError(
                    f"refined_queries item exceeds 200 chars: {truncated!r}"
                )
        return v

    @field_validator("trigger_signals")
    @classmethod
    def _validate_trigger_signals(cls, v: list[str]) -> list[str]:
        for item in v:
            if item not in _ALLOWED_REFLECTOR_TRIGGER_SIGNALS:
                raise ValueError(
                    f"unknown trigger_signals value {item!r}; allowed: "
                    f"{sorted(_ALLOWED_REFLECTOR_TRIGGER_SIGNALS)}"
                )
        return v

    model_config = ConfigDict(extra="forbid")


class ReflectorDecision(BaseModel):
    """Outcome of one Reflector evaluation pass over current Reader outputs."""

    questions_to_re_search: list[QuestionReSearchSpec] = Field(
        default_factory=list,
        max_length=7,
        description=(
            "Subset of questions scheduled for re-search this wave. "
            "Empty when no triggers fire."
        ),
    )
    skipped_question_ids_due_to_budget: list[str] = Field(
        default_factory=list,
        max_length=7,
        description=(
            "Questions that matched triggers but were excluded by "
            "max_questions_per_run cap."
        ),
    )

    model_config = ConfigDict(extra="forbid")


class ReflectorPhaseSummary(BaseModel):
    """Aggregate for logging/metrics — not part of Synthesizer input."""

    loop_iteration: int = Field(
        ...,
        ge=0,
        description=(
            "Current refinement wave (0-indexed, max controlled by "
            "Settings.reflector_max_refinement_waves)."
        ),
    )
    questions_flagged_count: int = Field(
        ...,
        ge=0,
        description="Total questions matching §2 OR-rule before scheduling cap.",
    )
    questions_scheduled_count: int = Field(
        ...,
        ge=0,
        description=(
            "Total questions actually scheduled (after max_questions_per_run cap)."
        ),
    )
    decision_method: ReflectorDecisionMethod = Field(
        ...,
        description=(
            "The decision method used. Currently only 'rule_v1' per ADR 0013."
        ),
    )
    waves_used: int = Field(
        ...,
        ge=0,
        description=(
            "Refinement waves with at least one successful Tavily re-search that "
            "returned new hits (maps to ValidationReport.reflection_loops_used)."
        ),
    )

    evidence_analysis: EvidenceAnalysisResult | None = Field(
        default=None,
        description=(
            "Deterministic evidence quality analysis (contradictions, clusters, gaps). "
            "Produced at end of Reflector phase; feeds Reasoning Engine."
        ),
    )

    model_config = ConfigDict(extra="forbid")
