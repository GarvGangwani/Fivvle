"""Stage 3 — Visual Composer prompt."""

from __future__ import annotations

import json

import app.llm.client as llm_client
from app.llm.client import USER_CACHE_ZONE_BOUNDARY
from app.schemas.landing_page_v2 import CreativeDirectorOutput, NarrativeArchitectOutput
from app.schemas.refinement import RefinedIdea

LP_RUNTIME_VISUAL_PROMPT_NAME = "lp_runtime_visual_composer"

LP_RUNTIME_VISUAL_SYSTEM_PROMPT = ""

LP_RUNTIME_VISUAL_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
]

LP_RUNTIME_VISUAL_ZONE_A = """\
You are the **Visual Composer** at Fivvle.

Inputs: NarrativeArchitectOutput + CreativeDirectorOutput.

Decide WHAT appears visually on this page. Prioritize visual storytelling over text walls.

For each narrative stage, assign at least one VisualElementSpec when appropriate:
visual_type: product_screenshot | dashboard | phone_mockup | illustration | diagram | \
chart | comparison | timeline | cards | testimonial_card | logo_strip | \
animation_placeholder | before_after | none

Each visual needs: stage_id, visual_type, purpose, prominence (low|medium|high).
Reference asset_key when uploaded assets match (hero, product, logo, etc.).

Output rhythm_notes explaining how text and visuals alternate — never two text-only \
sections with identical visual weight in a row.

Do NOT write copy. Do NOT output layout/HTML/CSS.
"""


def build_lp_runtime_visual_user_prompt(
    *,
    narrative: NarrativeArchitectOutput,
    creative: CreativeDirectorOutput,
    refined_idea: RefinedIdea,
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
        "<refined_idea>",
        refined_idea.model_dump_json(indent=2),
        "</refined_idea>",
    ]
    if available_assets:
        parts.extend(
            [
                "",
                "<available_assets>",
                json.dumps(available_assets, indent=2),
                "</available_assets>",
            ]
        )
    return USER_CACHE_ZONE_BOUNDARY.join([LP_RUNTIME_VISUAL_ZONE_A, "", "\n".join(parts)])
