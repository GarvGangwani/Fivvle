"""Stage 4 — Component Planner prompt."""

from __future__ import annotations

import json

import app.llm.client as llm_client
from app.llm.client import USER_CACHE_ZONE_BOUNDARY
from app.schemas.landing_page_v2 import (
    CreativeDirectorOutput,
    NarrativeArchitectOutput,
    VisualComposerOutput,
)
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport

LP_RUNTIME_COMPONENT_PROMPT_NAME = "lp_runtime_component_planner"

LP_RUNTIME_COMPONENT_SYSTEM_PROMPT = ""

LP_RUNTIME_COMPONENT_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
]

LP_RUNTIME_COMPONENT_ZONE_A = """\
You are the **Component Planner** at Fivvle.

Inputs: full pipeline (narrative, creative director, visual composer) + research.

Your job: produce ComponentPlannerOutput — the ONLY input the React renderer needs.

For each stage, output ComponentPlanSpec:
- component: HeroSection | ProblemSection | ProblemComparison | StorySection | \
FeatureTimeline | AlternatingFeature | PhoneMockup | Statistics | TrustSection | \
Testimonials | Pricing | FAQ | CtaSection | SplitLayout | ComparisonCards | \
FeatureGrid | AnimatedTimeline | BeforeAfter | FounderLetter | FeatureReveal | \
ImageShowcase | FooterSection
- variant: centered | split_left | split_right | editorial_left | editorial_right | \
cinematic | minimal | product_first | image_first | sticky_scroll | stacked | grid | asymmetric
- background, spacing, headline_alignment, visual, visual_asset_key, animation
- headline, subheadline, body, items (copy), cta_label for CTA/waitlist sections
- metadata: purpose, emotion, conversion_goal (INTERNAL — never shown to visitors)

Also output design_tokens: color_mode, accent_family, card_style, cta_emphasis.

Rules:
- Compose premium startup pages using the component library — not generic text documents.
- Alternate visual and text rhythm per visual_composer.rhythm_notes.
- Write outcome-first, second-person copy. Never cite "research" on the page.
- Waitlist backend is locked — only set cta_label text.
- metadata fields are for planning only.
"""


def build_lp_runtime_component_user_prompt(
    *,
    narrative: NarrativeArchitectOutput,
    creative: CreativeDirectorOutput,
    visual: VisualComposerOutput,
    validation_report: ValidationReport,
    refined_idea: RefinedIdea,
    page_goal: str,
    regeneration_hint: str | None,
    available_assets: list[dict[str, str]],
) -> str:
    parts = [
        "<narrative>",
        narrative.model_dump_json(indent=2),
        "</narrative>",
        "",
        "<creative_director>",
        creative.model_dump_json(indent=2),
        "</creative_director>",
        "",
        "<visual_composer>",
        visual.model_dump_json(indent=2),
        "</visual_composer>",
        "",
        "<validation_report>",
        validation_report.model_dump_json(indent=2),
        "</validation_report>",
        "",
        "<refined_idea>",
        refined_idea.model_dump_json(indent=2),
        "</refined_idea>",
        "",
        f"page_goal: {page_goal}",
    ]
    if regeneration_hint:
        parts.extend(["", f"regeneration_hint: {regeneration_hint}"])
    if available_assets:
        parts.extend(
            [
                "",
                "<available_assets>",
                json.dumps(available_assets, indent=2),
                "</available_assets>",
            ]
        )
    return USER_CACHE_ZONE_BOUNDARY.join([LP_RUNTIME_COMPONENT_ZONE_A, "", "\n".join(parts)])
