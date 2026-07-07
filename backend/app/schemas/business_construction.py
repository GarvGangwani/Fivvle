"""Business Construction Engine — internal reasoning models.

These models represent the structured intelligence layer between evidence
collection (Reader/Reflector) and report communication (Synthesizer).

They are decoupled from ValidationReport field shapes so the reasoning
pipeline can evolve independently of founder-facing report formatting.

Per product direction:
  Evidence → Reasoning → Mechanisms → Predictions → Founder Decisions
  → Business Construction → Report (communication only)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConfidenceLevel = Literal["high", "medium", "low"]

BusinessComponentType = Literal[
    "customer_definition",
    "positioning",
    "value_proposition",
    "distribution_strategy",
    "market_wedge",
    "pricing_logic",
    "business_model",
    "competitive_differentiation",
    "validation_experiments",
    "execution_priorities",
]

ClusterTheme = Literal[
    "market",
    "competition",
    "customer",
    "distribution",
    "regulatory",
    "product",
    "general",
]


class EvidenceAtom(BaseModel):
    """Canonical evidence unit — Reader owns evidence only (no recommendations)."""

    model_config = ConfigDict(extra="forbid")

    atom_id: str = Field(..., max_length=32)
    question_id: str = Field(..., max_length=8)
    observation: str = Field(..., max_length=600)
    source_url: str = Field(..., max_length=2000)
    confidence: ConfidenceLevel
    context: str = Field(..., max_length=400)
    supporting_excerpt: str | None = Field(default=None, max_length=600)


class EvidenceContradiction(BaseModel):
    """Two or more atoms that pull in opposing directions on the same theme."""

    model_config = ConfigDict(extra="forbid")

    contradiction_id: str = Field(..., max_length=32)
    atom_ids: list[str] = Field(..., min_length=2, max_length=8)
    theme: ClusterTheme
    description: str = Field(..., max_length=500)
    confidence: ConfidenceLevel


class EvidenceCluster(BaseModel):
    """Related observations grouped across questions and sources."""

    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(..., max_length=32)
    theme: ClusterTheme
    label: str = Field(..., max_length=200)
    atom_ids: list[str] = Field(..., min_length=1, max_length=40)
    dominant_confidence: ConfidenceLevel


class EvidenceAnalysisResult(BaseModel):
    """Reflector-expanded evidence quality assessment (no business decisions)."""

    model_config = ConfigDict(extra="forbid")

    analysis_version: str = Field(default="v1", max_length=16)
    atoms: list[EvidenceAtom] = Field(default_factory=list, max_length=80)
    contradictions: list[EvidenceContradiction] = Field(default_factory=list, max_length=20)
    missing_evidence: list[str] = Field(default_factory=list, max_length=20)
    weak_evidence_atom_ids: list[str] = Field(default_factory=list, max_length=40)
    clusters: list[EvidenceCluster] = Field(default_factory=list, max_length=20)
    evidence_gaps: list[str] = Field(default_factory=list, max_length=20)


class Mechanism(BaseModel):
    """Explanatory model linking multiple observations."""

    model_config = ConfigDict(extra="forbid")

    mechanism_id: str = Field(..., max_length=32)
    cluster_id: str = Field(..., max_length=32)
    statement: str = Field(..., max_length=600)
    supporting_atom_ids: list[str] = Field(..., min_length=1, max_length=20)
    confidence: ConfidenceLevel


class Hypothesis(BaseModel):
    """Competing explanation for a cluster of observations."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str = Field(..., max_length=32)
    cluster_id: str = Field(..., max_length=32)
    label: str = Field(..., max_length=8)
    statement: str = Field(..., max_length=400)
    mechanism_id: str | None = Field(default=None, max_length=32)


class HypothesisDebate(BaseModel):
    """Challenge record for one hypothesis against the evidence base."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str = Field(..., max_length=32)
    supporting_atom_ids: list[str] = Field(default_factory=list, max_length=20)
    contradicting_atom_ids: list[str] = Field(default_factory=list, max_length=20)
    confidence: ConfidenceLevel
    prediction_if_true: str = Field(..., max_length=400)
    prediction_if_false: str = Field(..., max_length=400)
    selected: bool = False


class Prediction(BaseModel):
    """Forward-looking claim derived from a mechanism."""

    model_config = ConfigDict(extra="forbid")

    prediction_id: str = Field(..., max_length=32)
    mechanism_id: str = Field(..., max_length=32)
    statement: str = Field(..., max_length=500)
    horizon: str = Field(default="12-24 months", max_length=64)
    confidence: ConfidenceLevel


class FounderDecision(BaseModel):
    """Actionable business implication for the founder (not a generic recommendation)."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(..., max_length=32)
    insight: str = Field(..., max_length=400)
    business_implication: str = Field(..., max_length=500)
    action: str = Field(..., max_length=400)
    related_hypothesis_id: str | None = Field(default=None, max_length=32)
    related_mechanism_id: str | None = Field(default=None, max_length=32)
    confidence: ConfidenceLevel


class BusinessComponent(BaseModel):
    """Constructed startup building block derived from reasoning output."""

    model_config = ConfigDict(extra="forbid")

    component_type: BusinessComponentType
    title: str = Field(..., max_length=120)
    content: str = Field(..., max_length=1200)
    supporting_decision_ids: list[str] = Field(default_factory=list, max_length=10)
    supporting_mechanism_ids: list[str] = Field(default_factory=list, max_length=10)
    confidence: ConfidenceLevel


class ReasoningEngineOutput(BaseModel):
    """Full output of the Reasoning Engine — thinking happens here, not in Synthesizer."""

    model_config = ConfigDict(extra="forbid")

    engine_version: str = Field(default="v1", max_length=16)
    clusters: list[EvidenceCluster] = Field(default_factory=list, max_length=20)
    mechanisms: list[Mechanism] = Field(default_factory=list, max_length=20)
    hypotheses: list[Hypothesis] = Field(default_factory=list, max_length=30)
    debates: list[HypothesisDebate] = Field(default_factory=list, max_length=30)
    predictions: list[Prediction] = Field(default_factory=list, max_length=20)
    founder_decisions: list[FounderDecision] = Field(default_factory=list, max_length=20)
    business_components: list[BusinessComponent] = Field(default_factory=list, max_length=12)


class BusinessConstructionArtifact(BaseModel):
    """Persisted bundle attached to ValidationReport after reasoning completes."""

    model_config = ConfigDict(extra="forbid")

    reasoning: ReasoningEngineOutput
    evidence_analysis: EvidenceAnalysisResult
