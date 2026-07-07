"""Stage 2 — Creative Director prompt."""

from __future__ import annotations

import app.llm.client as llm_client
from app.llm.client import USER_CACHE_ZONE_BOUNDARY
from app.schemas.landing_page_v2 import NarrativeArchitectOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport

LP_RUNTIME_CREATIVE_PROMPT_NAME = "lp_runtime_creative_director"

LP_RUNTIME_CREATIVE_SYSTEM_PROMPT = ""

LP_RUNTIME_CREATIVE_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
]

LP_RUNTIME_CREATIVE_ZONE_A = """\
You are the **Creative Director** at Fivvle.

Input: NarrativeArchitectOutput (emotional journey only).

Your job: convert narrative into creative direction for each stage.

For EVERY stage in stage_order, output a SectionCreativeBrief with:
- purpose, emotional_objective, visual_objective, emotion, theme
- layout_intent, visual_weight, pacing, hierarchy, storytelling_role
- transition_style, atmosphere, component_priority (ordered list of what leads: Illustration, Narrative, Statistic, etc.)
- spacing (xs|s|m|l|xl|2xl), animation (none|fade|fade_up|slide_in|subtle_scale)

Also output global_direction: visual_style, tone, pace, typography, color_mode, accent_family, visual_personality.

Do NOT write page copy. Do NOT output HTML/CSS/React.
Ensure visual rhythm — no two consecutive sections should feel identical in weight or layout_intent.
"""


def build_lp_runtime_creative_user_prompt(
    *,
    narrative: NarrativeArchitectOutput,
    validation_report: ValidationReport,
    refined_idea: RefinedIdea,
    page_goal: str,
) -> str:
    parts = [
        "<narrative_architect_output>",
        narrative.model_dump_json(indent=2),
        "</narrative_architect_output>",
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
    return USER_CACHE_ZONE_BOUNDARY.join([LP_RUNTIME_CREATIVE_ZONE_A, "", "\n".join(parts)])
