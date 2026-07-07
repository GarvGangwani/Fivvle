"""Tests for LLM cost computation."""

from decimal import Decimal

from app.llm.cost import compute_cost_usd


def test_kimi_cost_applies_cached_discount() -> None:
    cost = compute_cost_usd(
        "kimi",
        "kimi-k2.6",
        prompt_tokens=5000,
        completion_tokens=500,
        cached_input_tokens=3000,
    )
    # Uncached input: 2000 * $0.95 / 1M = $0.0019
    # Cached input:   3000 * $0.16 / 1M = $0.00048
    # Output:         500 * $4.00 / 1M  = $0.002
    assert cost == Decimal("0.004380")


def test_kimi_cost_all_uncached() -> None:
    without_cached = compute_cost_usd("kimi", "kimi-k2.6", 5000, 500)
    explicit_none = compute_cost_usd(
        "kimi",
        "kimi-k2.6",
        prompt_tokens=5000,
        completion_tokens=500,
        cached_input_tokens=None,
    )
    assert without_cached == explicit_none
    assert without_cached == Decimal("0.006750")


def test_kimi_cost_all_cached_capped_at_prompt_tokens() -> None:
    cost = compute_cost_usd(
        "kimi",
        "kimi-k2.6",
        prompt_tokens=1000,
        completion_tokens=100,
        cached_input_tokens=2000,
    )
    # uncached = max(0, 1000 - 2000) = 0; cached billed at 2000 * 0.16 / 1M
    assert cost == Decimal("0.000720")
