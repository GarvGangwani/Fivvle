"""Central monetization pricing — credits, packs, and service costs.

All product-facing prices are in credits. USD is derived via CREDIT_CONVERSION_RATE.
Do not duplicate these constants elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal

# 1 USD = 5 credits
CREDIT_CONVERSION_RATE: Final[int] = 5

MIN_PURCHASE_USD_CENTS: Final[int] = 500  # $5.00

WELCOME_COUPON_CODE: Final[str] = "WELCOME5"
WELCOME_COUPON_CREDITS: Final[int] = 25

ServiceKey = Literal[
    "ideaRefinement",
    "validationReport",
    "landingPageGeneration",
    "distributionCampaign",
    "metricsAnalysis",
    "competitorAnalysis",
    "reportRegeneration",
    "fullValidationFlow",
    "insightReport",
]

SERVICE_PRICING: Final[dict[ServiceKey, int]] = {
    "ideaRefinement": 5,
    "validationReport": 25,
    "landingPageGeneration": 15,
    "distributionCampaign": 25,
    # Deprecated unused — metrics gating removed in PR 2; key kept until PR 5 cleanup.
    "metricsAnalysis": 20,
    "competitorAnalysis": 20,
    "reportRegeneration": 10,
    "fullValidationFlow": 50,
    "insightReport": 20,
}

SERVICE_LABELS: Final[dict[ServiceKey, str]] = {
    "ideaRefinement": "Idea refinement",
    "validationReport": "Validation report",
    "landingPageGeneration": "Landing page generation",
    "distributionCampaign": "Distribution campaign",
    "metricsAnalysis": "Metrics analysis",
    "competitorAnalysis": "Competitor analysis",
    "reportRegeneration": "Report regeneration",
    "fullValidationFlow": "Full validation flow",
    "insightReport": "Insight report",
}

PackId = Literal["starter", "builder", "founder", "growth", "scale"]


@dataclass(frozen=True, slots=True)
class CreditPack:
    id: PackId
    name: str
    usd_cents: int
    base_credits: int
    bonus_credits: int

    @property
    def total_credits(self) -> int:
        return self.base_credits + self.bonus_credits

    @property
    def usd_display(self) -> str:
        return f"${self.usd_cents // 100}"


CREDIT_PACKS: Final[tuple[CreditPack, ...]] = (
    CreditPack("starter", "Starter", 500, 25, 0),
    CreditPack("builder", "Builder", 1000, 50, 5),
    CreditPack("founder", "Founder", 2500, 125, 20),
    CreditPack("growth", "Growth", 5000, 250, 50),
    CreditPack("scale", "Scale", 10000, 500, 125),
)

PACK_BY_ID: Final[dict[PackId, CreditPack]] = {p.id: p for p in CREDIT_PACKS}


def credits_to_usd(credits: int) -> Decimal:
    """Convert credits to USD (display only)."""
    return Decimal(credits) / Decimal(CREDIT_CONVERSION_RATE)


def usd_cents_to_credits(usd_cents: int) -> int:
    """Convert USD cents to base credits (no bonus)."""
    dollars = Decimal(usd_cents) / Decimal(100)
    return int(dollars * CREDIT_CONVERSION_RATE)


def get_pack(pack_id: str) -> CreditPack:
    if pack_id not in PACK_BY_ID:
        raise ValueError(f"Unknown credit pack: {pack_id!r}")
    return PACK_BY_ID[pack_id]  # type: ignore[index]
