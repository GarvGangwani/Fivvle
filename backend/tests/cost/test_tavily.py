"""Tests for Tavily credit and cost resolution."""

from decimal import Decimal

from app.cost.tavily import (
    credits_for_search_depth,
    estimate_research_tavily_credits,
    resolve_tavily_credits_from_response,
    tavily_cost_usd,
)


def test_credits_for_search_depth_advanced() -> None:
    assert credits_for_search_depth("advanced") == 2
    assert credits_for_search_depth("basic") == 1


def test_resolve_tavily_credits_from_usage_field() -> None:
    raw = {"usage": {"credits": 2}, "results": []}
    assert resolve_tavily_credits_from_response(raw, search_depth="basic") == 2


def test_resolve_tavily_credits_falls_back_to_depth() -> None:
    raw = {"results": []}
    assert resolve_tavily_credits_from_response(raw, search_depth="advanced") == 2


def test_estimate_research_tavily_credits_includes_reflector() -> None:
    credits = estimate_research_tavily_credits(reflection_loops_used=1)
    # 12 initial advanced queries (24 credits) + 4 reflector queries (8 credits)
    assert credits == 32


def test_tavily_cost_usd() -> None:
    assert tavily_cost_usd(2, Decimal("0.008")) == Decimal("0.016")
