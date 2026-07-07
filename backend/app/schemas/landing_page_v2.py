"""Landing Page Runtime — multi-stage creative pipeline schemas (v4).

Pipeline:
  Narrative Architect → Creative Director → Visual Composer → Component Planner → Renderer

LLM stages output intent only. The renderer is deterministic and never guesses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

NarrativeArchetype = Literal[
    "b2b_saas",
    "consumer_app",
    "ai_tool",
    "marketplace",
    "founder_story",
    "dating_app",
    "generic",
]

SpacingScale = Literal["xs", "s", "m", "l", "xl", "2xl"]

AccentFamily = Literal["indigo", "emerald", "amber", "rose", "slate", "cyan"]

CardStyle = Literal["flat", "elevated", "outline", "glass"]

CtaEmphasis = Literal["subtle", "moderate", "bold"]

BackgroundStyle = Literal[
    "default",
    "surface",
    "dark_gradient",
    "accent_soft",
    "full_bleed_dark",
    "muted",
]

AnimationStyle = Literal["none", "fade", "fade_up", "slide_in", "subtle_scale"]

VisualWeight = Literal["low", "medium", "high"]

TransitionStyle = Literal["cut", "fade", "scroll", "contrast_shift"]

ComponentType = Literal[
    "HeroSection",
    "ProblemSection",
    "ProblemComparison",
    "StorySection",
    "FeatureTimeline",
    "AlternatingFeature",
    "PhoneMockup",
    "Statistics",
    "TrustSection",
    "Testimonials",
    "Pricing",
    "FAQ",
    "CtaSection",
    "SplitLayout",
    "ComparisonCards",
    "FeatureGrid",
    "AnimatedTimeline",
    "BeforeAfter",
    "FounderLetter",
    "FeatureReveal",
    "ImageShowcase",
    "FooterSection",
]

ComponentVariant = Literal[
    "centered",
    "split_left",
    "split_right",
    "editorial_left",
    "editorial_right",
    "cinematic",
    "minimal",
    "product_first",
    "image_first",
    "sticky_scroll",
    "stacked",
    "grid",
    "asymmetric",
]

VisualElementType = Literal[
    "product_screenshot",
    "dashboard",
    "phone_mockup",
    "illustration",
    "diagram",
    "chart",
    "comparison",
    "timeline",
    "cards",
    "testimonial_card",
    "logo_strip",
    "animation_placeholder",
    "before_after",
    "none",
]

HeadlineAlignment = Literal["left", "center", "right"]


# ---------------------------------------------------------------------------
# Stage 1 — Narrative Architect (goals only, no copy/layout/style)
# ---------------------------------------------------------------------------


class NarrativeStageGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(..., min_length=1, max_length=32)
    label: str = Field(..., min_length=2, max_length=80)
    goal: str = Field(..., min_length=10, max_length=400)
    visitor_feeling: str = Field(..., min_length=5, max_length=200)
    objection_addressed: str | None = Field(default=None, max_length=300)


class NarrativeArchitectOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_archetype: NarrativeArchetype
    story_summary: str = Field(..., min_length=30, max_length=1200)
    stages: list[NarrativeStageGoal] = Field(..., min_length=4, max_length=12)
    key_objections: list[str] = Field(..., min_length=1, max_length=8)
    desired_end_state: str = Field(..., min_length=10, max_length=400)
    stage_order: list[str] = Field(
        ...,
        min_length=4,
        max_length=12,
        description="Ordered stage_id values — the emotional journey sequence.",
    )


# ---------------------------------------------------------------------------
# Stage 2 — Creative Director (per-section creative brief)
# ---------------------------------------------------------------------------


class GlobalCreativeDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visual_style: Literal["editorial", "minimal", "technical", "bold", "premium", "playful"]
    tone: Literal["premium", "approachable", "urgent", "calm", "confident"]
    pace: Literal["cinematic", "steady", "snappy"]
    typography: Literal["bold_editorial", "minimal_sans", "technical_mono", "friendly_rounded"]
    color_mode: Literal["light", "dark"]
    accent_family: AccentFamily
    visual_personality: str = Field(..., min_length=8, max_length=300)


class SectionCreativeBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(..., min_length=1, max_length=32)
    purpose: str = Field(..., min_length=5, max_length=300)
    emotional_objective: str = Field(..., min_length=5, max_length=200)
    visual_objective: str = Field(..., min_length=5, max_length=200)
    emotion: str = Field(..., min_length=3, max_length=80)
    theme: Literal["light", "dark", "accent", "gradient"]
    layout_intent: Literal["centered", "split", "full_bleed", "asymmetric", "stack"]
    visual_weight: VisualWeight
    pacing: Literal["slow", "medium", "fast"]
    hierarchy: Literal["headline_dominant", "visual_dominant", "balanced"]
    storytelling_role: str = Field(..., min_length=5, max_length=200)
    transition_style: TransitionStyle
    atmosphere: str = Field(..., min_length=5, max_length=200)
    component_priority: list[str] = Field(..., min_length=1, max_length=5)
    spacing: SpacingScale = "l"
    animation: AnimationStyle = "fade_up"


class CreativeDirectorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_direction: GlobalCreativeDirection
    section_briefs: list[SectionCreativeBrief] = Field(..., min_length=4, max_length=14)


# ---------------------------------------------------------------------------
# Stage 3 — Visual Composer
# ---------------------------------------------------------------------------


class VisualElementSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(..., min_length=1, max_length=32)
    visual_type: VisualElementType
    purpose: str = Field(..., min_length=5, max_length=300)
    prominence: VisualWeight = "medium"
    asset_key: str | None = Field(default=None, max_length=64)
    alt: str | None = Field(default=None, max_length=200)


class VisualComposerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visuals: list[VisualElementSpec] = Field(..., min_length=2, max_length=20)
    rhythm_notes: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="How visuals alternate with text — never two identical beats in a row.",
    )


# ---------------------------------------------------------------------------
# Stage 4 — Component Planner (renderer input)
# ---------------------------------------------------------------------------


class SectionCopyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    body: str | None = None
    label: str | None = None
    value: str | None = None


class SectionMetadata(BaseModel):
    """Internal metadata — must NOT be rendered by the runtime."""

    model_config = ConfigDict(extra="forbid")

    purpose: str
    emotion: str
    conversion_goal: str
    recommended_layout: str | None = None
    recommended_visual: str | None = None


class ComponentPlanSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64)
    stage_id: str = Field(..., min_length=1, max_length=32)
    component: ComponentType
    variant: ComponentVariant
    background: BackgroundStyle = "default"
    spacing: SpacingScale = "l"
    headline_alignment: HeadlineAlignment = "left"
    visual: VisualElementType = "none"
    visual_asset_key: str | None = Field(default=None, max_length=64)
    animation: AnimationStyle = "fade_up"
    headline: str | None = Field(default=None, max_length=300)
    subheadline: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, max_length=4000)
    items: list[SectionCopyItem] = Field(default_factory=list, max_length=12)
    cta_label: str | None = Field(default=None, max_length=100)
    metadata: SectionMetadata


class DesignTokenSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color_mode: Literal["light", "dark"]
    accent_family: AccentFamily
    card_style: CardStyle
    cta_emphasis: CtaEmphasis


class ComponentPlannerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_tokens: DesignTokenSpec
    components: list[ComponentPlanSpec] = Field(..., min_length=4, max_length=14)


class AssetRefSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_key: str = Field(..., min_length=1, max_length=64)
    role: str = Field(..., min_length=1, max_length=64)
    alt: str = Field(..., min_length=1, max_length=200)
    storytelling_role: str | None = Field(default=None, max_length=200)
    url: str | None = None


class PipelineArtifacts(BaseModel):
    """Full pipeline trace — for export/debug; metadata not rendered."""

    model_config = ConfigDict(extra="forbid")

    narrative: NarrativeArchitectOutput
    creative_director: CreativeDirectorOutput
    visual_composer: VisualComposerOutput


class LandingPageV2Spec(BaseModel):
    """Schema v4 — deterministic renderer consumes `components` only."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[4] = 4
    page_goal: Literal["waitlist", "interest", "contact"] = "waitlist"
    pipeline: PipelineArtifacts
    design_tokens: DesignTokenSpec
    components: list[ComponentPlanSpec] = Field(..., min_length=4, max_length=14)
    asset_refs: list[AssetRefSpec] = Field(default_factory=list, max_length=12)


# ---------------------------------------------------------------------------
# API types
# ---------------------------------------------------------------------------


class LandingPageV2GenerationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    generation_status: Literal["idle", "generating", "ready", "failed"]
    generation_phase: Literal[
        "idle",
        "planning_narrative",
        "creative_direction",
        "visual_composition",
        "component_planning",
        "ready",
        "failed",
    ] = "idle"
    error_detail: str | None = None
    spec: LandingPageV2Spec | None = None
    publication_slug: str | None = None
    resolved_assets: dict[str, str] = Field(default_factory=dict)


class GenerateLandingPageV2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_goal: Literal["waitlist", "interest", "contact"] = "waitlist"
    regeneration_hint: str | None = Field(default=None, max_length=500)


class GenerateLandingPageV2Response(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    generation_status: Literal["generating"]
