"""Unit tests for Perplexity cost helpers."""

from __future__ import annotations

from decimal import Decimal

from app.cost.perplexity import perplexity_cost_usd


def test_prefers_usage_total_cost() -> None:
    cost = perplexity_cost_usd({"total_cost": 0.006123}, Decimal("0.005"))
    assert cost == Decimal("0.006123")


def test_falls_back_to_per_request_default() -> None:
    cost = perplexity_cost_usd(None, Decimal("0.005"))
    assert cost == Decimal("0.005")
