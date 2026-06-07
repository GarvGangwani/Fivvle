"""Landing page generator schemas — contracts for the 2-LLM-call pipeline.

These schemas are the data contract for the landing page generator (ADR 0022).
Stage 1 (strategist) emits ``LandingPageInputModel`` and ``LandingPageStrategy``
from ``ValidationReport`` + ``RefinedIdea``. Stage 2 (copy generator) emits
``CopyOutput``. Stage 3 (Python theme applicator) assembles ``page_json`` and
the orchestrator persists ``LandingPageGenerationOutput``.

Per AGENTS.md "Input and output handling":
  LLM-generated content rendered in the frontend must be treated as untrusted
  text. This schema is the boundary where we enforce that all LLM output is
  parsed and validated before reaching any consumer.

Per AGENTS.md "LLM and agent security":
  LLM outputs MUST be parsed as Pydantic models with strict validation. All
  models use ``extra="forbid"`` to reject unexpected fields from model drift
  or prompt injection via structured-output channels.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OfferCore(BaseModel):
    """Core offer framing derived from research and refinement."""

    model_config = ConfigDict(extra="forbid")

    core_offer: str = Field(
        ...,
        description="The fundamental product or service being offered.",
    )
    one_line_pitch: str = Field(
        ...,
        description="High-impact one-sentence pitch for the landing page.",
    )
    transformation_promise: str = Field(
        ...,
        description=(
            "The ultimate value or transformation promised to the customer."
        ),
    )


class ProblemIntelligence(BaseModel):
    """Problem-space intelligence for pain-led messaging."""

    model_config = ConfigDict(extra="forbid")

    pain_points: list[str] = Field(
        ...,
        description="Top pain points identified from validation research.",
    )
    urgency: str = Field(
        ...,
        description="Why resolving this problem is urgent for the target user.",
    )
    alternatives: str = Field(
        ...,
        description="Current workarounds or substitute solutions customers use.",
    )


class CustomerIntelligence(BaseModel):
    """ICP and buyer psychology for audience-targeted copy."""

    model_config = ConfigDict(extra="forbid")

    icp: str = Field(
        ...,
        description="Ideal Customer Profile definition synthesized from research.",
    )
    buyer_psychology: str = Field(
        ...,
        description="Buyer goals, motivations, and decision-making psychology.",
    )
    barriers: str = Field(
        ...,
        description="Top adoption barriers or switching frictions.",
    )
    willingness_to_pay: str = Field(
        ...,
        description=(
            "Signals about budget, pricing tolerance, and willingness to pay."
        ),
    )


class PositioningIntelligence(BaseModel):
    """Competitive positioning for differentiation-led messaging."""

    model_config = ConfigDict(extra="forbid")

    competitors: list[str] = Field(
        ...,
        description="Direct and indirect competitors surfaced by research.",
    )
    gaps: str = Field(
        ...,
        description="Identified competitive feature or positioning gaps.",
    )
    differentiators: str = Field(
        ...,
        description="Primary unfair advantages or unique differentiators.",
    )
    white_space: str = Field(
        ...,
        description="Uncontested market opportunity or positioning angle.",
    )


class BrandDirection(BaseModel):
    """Voice and visual direction for on-brand copy and template fit."""

    model_config = ConfigDict(extra="forbid")

    tone: str = Field(
        ...,
        description=(
            "Brand voice and personality (e.g. premium, serious, lighthearted)."
        ),
    )
    visual_direction: str = Field(
        ...,
        description=(
            "Visual styling advice: colors, themes, typography vibes."
        ),
    )
    trust_style: str = Field(
        ...,
        description=(
            "How to build trust signals (security, credibility, social proof)."
        ),
    )


class ProofIntelligence(BaseModel):
    """Evidence, objections, and rebuttals for proof-led sections."""

    model_config = ConfigDict(extra="forbid")

    traction_signals: list[str] = Field(
        default_factory=list,
        description="Evidence and traction signals from market/product research.",
    )
    social_proof_hooks: list[str] = Field(
        default_factory=list,
        description="Hooks suitable for social proof blocks on the page.",
    )
    top_objections: list[str] = Field(
        default_factory=list,
        description="Primary buyer objections to address on the landing page.",
    )
    objection_rebuttals: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of objection text to strategic rebuttal copy.",
    )


class LandingPageInputModel(BaseModel):
    """Marketing intelligence interpreted from ValidationReport + RefinedIdea.

    Emitted by the Stage 1 strategist LLM call (``lp_strategist_v1``). Distills
    typed research findings and founder refinement into a conversion-oriented
    input for copy generation.
    """

    model_config = ConfigDict(extra="forbid")

    offer_core: OfferCore = Field(...)
    problem_intelligence: ProblemIntelligence = Field(...)
    customer_intelligence: CustomerIntelligence = Field(...)
    positioning_intelligence: PositioningIntelligence = Field(...)
    brand_direction: BrandDirection = Field(...)
    proof_intelligence: ProofIntelligence = Field(...)
    page_goal: str = Field(
        ...,
        description=(
            "Primary conversion goal for the page (e.g. waitlist, interest, "
            "contact)."
        ),
    )


class LandingPageStrategy(BaseModel):
    """Conversion strategy: page architecture and copywriting framework.

    Emitted alongside ``LandingPageInputModel`` by the Stage 1 strategist call.
    Guides section ordering, messaging angle, and CTA approach for Stage 2 copy
    generation.
    """

    model_config = ConfigDict(extra="forbid")

    page_type: str = Field(
        ...,
        description=(
            "Target landing page goal (waitlist, launch, app_install, "
            "demo_booking, etc.)."
        ),
    )
    messaging_angle: str = Field(
        ...,
        description=(
            "Core messaging angle (e.g. trust-first, urgency-driven, "
            "transformation-led, comparison-led)."
        ),
    )
    section_sequence: list[str] = Field(
        ...,
        description=(
            "Strategic sequence of page sections to display (e.g. "
            "['hero', 'problem', 'features', 'comparison', 'faq', 'cta'])."
        ),
    )
    cta_strategy: list[str] = Field(
        ...,
        description="Copywriting strategies for primary and secondary CTAs.",
    )
    copy_framework: str = Field(
        ...,
        description=(
            "Chosen copy structure (e.g. 'PAS' for Pain-Agitate-Solve, "
            "'AIDA' for Attention-Interest-Desire-Action)."
        ),
    )


class CopyOutput(BaseModel):
    """Per-section conversion copy — Stage 2 LLM output (``lp_copy_v1``).

    ``copy_json`` keys correspond to section types in
    ``LandingPageStrategy.section_sequence`` (hero, problem, features, etc.).
    """

    model_config = ConfigDict(extra="forbid")

    copy_json: dict[str, Any] = Field(
        ...,
        description="Persuasive conversion-optimized copywriting per section.",
    )


class LandingPageGenerationOutput(BaseModel):
    """Combined final output persisted on the LandingPage row.

    ``copy_json`` comes from Stage 2; ``page_json`` is assembled by the Python
    theme applicator in Stage 3 from strategy, copy, and template config.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    copy_json: dict[str, Any] = Field(
        ...,
        description="Per-section copy keyed by section type.",
    )
    page_json: dict[str, Any] = Field(
        ...,
        description=(
            "Template config, color palette, typography, and ordered sections "
            "with populated content."
        ),
    )
