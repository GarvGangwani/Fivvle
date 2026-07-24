"""Tests for cost category resolution."""

from app.cost.category import (
    CostCategory,
    resolve_cost_category_from_external_provider,
    resolve_cost_category_from_phase,
)


def test_refinement_phases_map_to_refinement_category() -> None:
    for phase in (
        "refinement",
        "refinement_chat",
        "chat_normal",
        "chat_discussion",
        "chat_attachment",
        "evidence_chat",
        "universal_chat",
    ):
        assert resolve_cost_category_from_phase(phase) is CostCategory.REFINEMENT


def test_research_phases_map_to_cognitive_validation() -> None:
    for phase in (
        "planner",
        "searcher",
        "reader",
        "reflector",
        "synthesizer",
        "geography_hint",
        "voices_subreddit_selection",
        "voices_extraction",
    ):
        assert resolve_cost_category_from_phase(phase) is CostCategory.COGNITIVE_VALIDATION


def test_landing_and_insight_phases() -> None:
    assert resolve_cost_category_from_phase("landing_page") is CostCategory.LANDING_PAGE
    assert resolve_cost_category_from_phase("insight") is CostCategory.INSIGHT


def test_unknown_phase_maps_to_platform() -> None:
    assert resolve_cost_category_from_phase(None) is CostCategory.PLATFORM
    assert resolve_cost_category_from_phase("dispatch_started") is CostCategory.PLATFORM


def test_external_providers_map_to_expected_categories() -> None:
    assert (
        resolve_cost_category_from_external_provider("tavily")
        is CostCategory.COGNITIVE_VALIDATION
    )
    assert (
        resolve_cost_category_from_external_provider("reddit")
        is CostCategory.COGNITIVE_VALIDATION
    )
    assert (
        resolve_cost_category_from_external_provider("pytrends")
        is CostCategory.COGNITIVE_VALIDATION
    )
    assert (
        resolve_cost_category_from_external_provider("ipwho")
        is CostCategory.LANDING_PAGE
    )
    assert (
        resolve_cost_category_from_external_provider("unknown")
        is CostCategory.PLATFORM
    )
