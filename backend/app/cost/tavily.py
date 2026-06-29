"""Tavily credit → USD helpers for ExternalAPICall audit rows."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

SearchDepth = Literal["basic", "advanced", "fast", "ultra-fast"]

_ZERO = Decimal("0")

# Tavily docs (2026): basic/fast/ultra-fast = 1 credit; advanced = 2 credits.
_CREDITS_BY_DEPTH: dict[str, int] = {
    "basic": 1,
    "fast": 1,
    "ultra-fast": 1,
    "advanced": 2,
}


def credits_for_search_depth(search_depth: str) -> int:
    """Fallback credit count when the API omits usage metadata."""
    return _CREDITS_BY_DEPTH.get(search_depth, 1)


def resolve_tavily_credits_from_response(
    raw: dict[str, object],
    *,
    search_depth: str,
) -> int:
    """Read credits consumed from a Tavily search response.

    Tavily returns ``usage.credits`` when ``include_usage=True``. The field may
    be absent or zero on some responses — fall back to depth-based pricing.
    """
    usage = raw.get("usage")
    if isinstance(usage, dict):
        credits = usage.get("credits")
        if credits is not None:
            try:
                parsed = int(credits)
                if parsed > 0:
                    return parsed
            except (TypeError, ValueError):
                pass
    return credits_for_search_depth(search_depth)


def tavily_cost_usd(credits: int, usd_per_credit: Decimal) -> Decimal:
    return Decimal(credits) * usd_per_credit


def estimate_research_tavily_credits(
    *,
    reflection_loops_used: int = 0,
    estimated_initial_queries: int = 12,
    estimated_reflector_queries_per_loop: int = 4,
) -> int:
    """Estimate Tavily credits for one completed research run (advanced depth).

    Used when historical runs completed without ExternalAPICall rows — a gap
    observed before concurrent Tavily logging was hardened.
    """
    initial = estimated_initial_queries * credits_for_search_depth("advanced")
    reflector = (
        max(reflection_loops_used, 0)
        * estimated_reflector_queries_per_loop
        * credits_for_search_depth("advanced")
    )
    return initial + reflector
