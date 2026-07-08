"""Founder-journey cost categories for LLM and external API audit rows.

Maps fine-grained ``phase`` / ``provider`` values to product-level buckets used
in admin rollups (Refinement, Validation report, Landing page, Insight).
"""

from __future__ import annotations

from enum import StrEnum


class CostCategory(StrEnum):
    REFINEMENT = "refinement"
    COGNITIVE_VALIDATION = "cognitive_validation"
    LANDING_PAGE = "landing_page"
    INSIGHT = "insight"
    PLATFORM = "platform"


COST_CATEGORY_LABELS: dict[CostCategory, str] = {
    CostCategory.REFINEMENT: "Refinement",
    CostCategory.COGNITIVE_VALIDATION: "Validation report",
    CostCategory.LANDING_PAGE: "Landing page",
    CostCategory.INSIGHT: "Insight",
    CostCategory.PLATFORM: "Platform",
}

# Ordered for stable API responses.
COST_CATEGORY_ORDER: tuple[CostCategory, ...] = (
    CostCategory.REFINEMENT,
    CostCategory.COGNITIVE_VALIDATION,
    CostCategory.LANDING_PAGE,
    CostCategory.INSIGHT,
    CostCategory.PLATFORM,
)

_PHASE_TO_CATEGORY: dict[str, CostCategory] = {
    # Refinement (idea intake + chat)
    "refinement": CostCategory.REFINEMENT,
    "refinement_chat": CostCategory.REFINEMENT,
    "chat_normal": CostCategory.REFINEMENT,
    "chat_discussion": CostCategory.REFINEMENT,
    "chat_attachment": CostCategory.REFINEMENT,
    # Cognitive validation / research engine (validation report)
    "planner": CostCategory.COGNITIVE_VALIDATION,
    "searcher": CostCategory.COGNITIVE_VALIDATION,
    "reader": CostCategory.COGNITIVE_VALIDATION,
    "reflector": CostCategory.COGNITIVE_VALIDATION,
    "synthesizer": CostCategory.COGNITIVE_VALIDATION,
    "geography_hint": CostCategory.COGNITIVE_VALIDATION,
    "voices_subreddit_selection": CostCategory.COGNITIVE_VALIDATION,
    "voices_extraction": CostCategory.COGNITIVE_VALIDATION,
    # Landing page generation
    "landing_page": CostCategory.LANDING_PAGE,
    # Insight report
    "insight": CostCategory.INSIGHT,
}

_EXTERNAL_PROVIDER_TO_CATEGORY: dict[str, CostCategory] = {
    "tavily": CostCategory.COGNITIVE_VALIDATION,
    "reddit": CostCategory.COGNITIVE_VALIDATION,
    "perplexity": CostCategory.COGNITIVE_VALIDATION,
    "pytrends": CostCategory.COGNITIVE_VALIDATION,
    "ipwho": CostCategory.LANDING_PAGE,
}


def resolve_cost_category_from_phase(phase: str | None) -> CostCategory:
    """Map an LLMCall.phase value to a product cost category."""
    if phase is None:
        return CostCategory.PLATFORM
    return _PHASE_TO_CATEGORY.get(phase, CostCategory.PLATFORM)


def resolve_cost_category_from_external_provider(provider: str) -> CostCategory:
    """Map an ExternalAPICall.provider value to a product cost category."""
    return _EXTERNAL_PROVIDER_TO_CATEGORY.get(provider.lower(), CostCategory.PLATFORM)


def category_label(category: CostCategory | str) -> str:
    if isinstance(category, str):
        try:
            category = CostCategory(category)
        except ValueError:
            return category
    return COST_CATEGORY_LABELS.get(category, str(category))
