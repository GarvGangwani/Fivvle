"""LLM provider pricing table — per million tokens.

Prices are quoted by providers per 1M tokens. Stored as Decimal to avoid
float-arithmetic errors in cost rollups.

When provider pricing changes, update this table. The wrapper reads from
here at call time, so live cost is always current.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ModelPricing:
    """Pricing for a single model. All amounts in USD per 1M tokens."""

    input_per_1m: Decimal
    output_per_1m: Decimal


# Format: (provider, model_id) -> ModelPricing
# Provider strings match what we pass to the LLMCall.provider column.
# Model strings match the model identifiers used in the provider SDKs.
#
# Prices verified 2026-05-11 against:
#   Anthropic: https://platform.claude.com/docs/en/about-claude/models/overview
#              https://www.anthropic.com/pricing (API tab)
#   Groq:      https://groq.com/pricing
_PRICING: dict[tuple[str, str], ModelPricing] = {
    # -----------------------------------------------------------------------
    # Anthropic Claude — latest generation (as of 2026-05-11)
    # -----------------------------------------------------------------------
    # Opus 4.7 — most capable generally-available model
    ("anthropic", "claude-opus-4-7"): ModelPricing(
        input_per_1m=Decimal("5.00"),
        output_per_1m=Decimal("25.00"),
    ),
    # Sonnet 4.6 — best balance of speed and intelligence
    ("anthropic", "claude-sonnet-4-6"): ModelPricing(
        input_per_1m=Decimal("3.00"),
        output_per_1m=Decimal("15.00"),
    ),
    # Haiku 4.5 — fastest, most cost-efficient
    ("anthropic", "claude-haiku-4-5"): ModelPricing(
        input_per_1m=Decimal("1.00"),
        output_per_1m=Decimal("5.00"),
    ),
    # -----------------------------------------------------------------------
    # Anthropic Claude — previous generation, still available (2026-05-11)
    # -----------------------------------------------------------------------
    # Opus 4.6
    ("anthropic", "claude-opus-4-6"): ModelPricing(
        input_per_1m=Decimal("5.00"),
        output_per_1m=Decimal("25.00"),
    ),
    # Sonnet 4.5 (API alias: claude-sonnet-4-5 → claude-sonnet-4-5-20250929)
    ("anthropic", "claude-sonnet-4-5"): ModelPricing(
        input_per_1m=Decimal("3.00"),
        output_per_1m=Decimal("15.00"),
    ),
    # Opus 4.5 (API alias: claude-opus-4-5 → claude-opus-4-5-20251101)
    # NOTE: $5/$25, NOT $15/$75 — that higher rate belongs to Opus 4.1
    ("anthropic", "claude-opus-4-5"): ModelPricing(
        input_per_1m=Decimal("5.00"),
        output_per_1m=Decimal("25.00"),
    ),
    # Opus 4.1 (API alias: claude-opus-4-1 → claude-opus-4-1-20250805)
    ("anthropic", "claude-opus-4-1"): ModelPricing(
        input_per_1m=Decimal("15.00"),
        output_per_1m=Decimal("75.00"),
    ),
    # -----------------------------------------------------------------------
    # Groq — verified 2026-05-11 against https://groq.com/pricing
    # -----------------------------------------------------------------------
    ("groq", "llama-3.3-70b-versatile"): ModelPricing(
        input_per_1m=Decimal("0.59"),
        output_per_1m=Decimal("0.79"),
    ),
    ("groq", "llama-3.1-8b-instant"): ModelPricing(
        input_per_1m=Decimal("0.05"),
        output_per_1m=Decimal("0.08"),
    ),
    # -----------------------------------------------------------------------
    # Kimi K2.6 via Moonshot direct — verify against Moonshot dashboard;
    # cached input ~$0.16 not yet modeled.
    # -----------------------------------------------------------------------
    ("kimi", "kimi-k2.6"): ModelPricing(
        input_per_1m=Decimal("0.95"),
        output_per_1m=Decimal("4.00"),
    ),
}


def compute_anthropic_cached_cost_usd(
    model: str,
    *,
    uncached_tail_input_tokens: int,
    cache_read_input_tokens: int,
    cache_creation_ephemeral_5m: int,
    cache_creation_ephemeral_1h: int,
    completion_tokens: int,
) -> Decimal:
    """Anthropic Messages API cost with prompt caching usage fields.

    Per provider docs (prompt caching):

    - ``uncached_tail_input_tokens`` corresponds to ``usage.input_tokens``
      (portion after the last cache breakpoint — billed at standard input rate).
    - ``cache_read_input_tokens`` is billed at 10% of the list input rate.
    - Write tokens split by TTL: 5-minute writes at 1.25× input, 1-hour at 2×.

    Preconditions (caller responsibility): non-negative integers;
    ``cache_creation_ephemeral_5m + cache_creation_ephemeral_1h`` should match
    ``usage.cache_creation_input_tokens`` when the SDK exposes both.
    """
    pricing = _PRICING.get(("anthropic", model))
    if pricing is None:
        return Decimal("0")

    per_m = Decimal("1000000")
    base_in = pricing.input_per_1m
    uncached_cost = (Decimal(uncached_tail_input_tokens) / per_m) * base_in
    read_cost = (Decimal(cache_read_input_tokens) / per_m) * base_in * Decimal("0.10")
    write_5m = (Decimal(cache_creation_ephemeral_5m) / per_m) * base_in * Decimal("1.25")
    write_1h = (Decimal(cache_creation_ephemeral_1h) / per_m) * base_in * Decimal("2.00")
    output_cost = (Decimal(completion_tokens) / per_m) * pricing.output_per_1m
    return (uncached_cost + read_cost + write_5m + write_1h + output_cost).quantize(
        Decimal("0.000001")
    )


def compute_cost_usd(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """Compute cost in USD for a single LLM call.

    Returns Decimal("0") for unknown (provider, model) pairs — better to log
    a zero-cost call than fail to log at all. An admin can audit zero-cost
    rows in LLMCall to find pricing gaps. The wrapper emits a warning log
    when this happens.

    Args:
        provider: lowercase provider id (e.g. "anthropic", "groq")
        model: model identifier as used in the SDK call
        prompt_tokens: input token count from the API response
        completion_tokens: output token count from the API response

    Returns:
        Cost in USD, with up to 6 decimal places (matches Numeric(10,6) column).
    """
    pricing = _PRICING.get((provider.lower(), model))
    if pricing is None:
        return Decimal("0")

    input_cost = (Decimal(prompt_tokens) / Decimal("1000000")) * pricing.input_per_1m
    output_cost = (Decimal(completion_tokens) / Decimal("1000000")) * pricing.output_per_1m
    return (input_cost + output_cost).quantize(Decimal("0.000001"))


def is_known_model(provider: str, model: str) -> bool:
    """True if the (provider, model) pair has a pricing entry."""
    return (provider.lower(), model) in _PRICING
