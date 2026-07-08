"""Perplexity sonar → USD helpers for ExternalAPICall audit rows."""

from __future__ import annotations

from decimal import Decimal

_ZERO = Decimal("0")
_QUANTIZE = Decimal("0.000001")


def perplexity_cost_usd(
    usage_cost: dict | None,
    fallback_per_request: Decimal,
) -> Decimal:
    """Prefer usage.cost.total_cost when Perplexity returns it.

    Fall back to fallback_per_request when the field is absent.
    """
    if isinstance(usage_cost, dict):
        total = usage_cost.get("total_cost")
        if total is not None:
            try:
                return Decimal(str(total)).quantize(_QUANTIZE)
            except (TypeError, ValueError, ArithmeticError):
                pass
    return fallback_per_request.quantize(_QUANTIZE)
