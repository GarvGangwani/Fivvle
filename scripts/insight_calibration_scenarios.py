"""Synthetic AnalyticsAggregate scenarios for insight calibration.

Each scenario stresses a specific obligation from the insight_v1_cached prompt:

- warm_only_low_volume: warm_network_bias_index = 1.0, low total volume.
  Expects the LLM to flag "this could be just friends" / discount the signal.

- cold_high_volume_no_conversion: 200 cold views, 0 signups.
  Triggers drop_off_signals["zero_conversion"]. Expects KILL or PIVOT verdict
  with concrete recommendation_rationale citing the conversion rate.

- insufficient_data: 5 views, 0 signups, 4 days live.
  Triggers INSUFFICIENT DATA PATHWAY. Expects recommendation_type to default
  to the ValidationReport's overall_recommendation, and at least one
  [COGNITIVE] takeaway acknowledging the missing behavioral signal.

- bimodal_engagement: time_on_page_p50_seconds=0, p90=240.
  Triggers drop_off_signals["bimodal_engagement"]. Expects the LLM to discuss
  the engagement split in research_takeaways or recommendation.

- high_warm_high_conversion: warm_network_bias_index=0.9, conversion_rate=0.25.
  Tests whether the LLM correctly skeptically calls out "high conversion on
  friendly traffic isn't a real signal."

Validator notes:
- views_by_day / signups_by_day MUST have length == days_live.
- conversion_rate_by_source keys MUST be a subset of views_by_source keys.
- All counts are non-negative; warm_network_bias_index in [0, 1].
"""

from __future__ import annotations

from uuid import UUID

from app.schemas.insight import AnalyticsAggregate


def build_warm_only_low_volume(_experiment_id: UUID) -> AnalyticsAggregate:
    return AnalyticsAggregate(
        days_live=5,
        total_page_views=30,
        unique_visitors=25,
        total_signups=4,
        conversion_rate=0.16,
        views_by_source={"twitter": 18, "linkedin": 9, "discord": 3},
        signups_by_source={"twitter": 3, "linkedin": 1},
        conversion_rate_by_source={
            "twitter": 0.167,
            "linkedin": 0.111,
            "discord": 0.0,
        },
        warm_network_bias_index=1.0,
        time_on_page_p50_seconds=42,
        time_on_page_p90_seconds=180,
        views_by_day=[8, 6, 7, 5, 4],
        signups_by_day=[2, 1, 0, 1, 0],
        drop_off_signals={},
        data_quality_notes=[
            "Traffic concentrated on a single source (twitter) — results may not generalize."
        ],
    )


def build_cold_high_volume_no_conversion(_experiment_id: UUID) -> AnalyticsAggregate:
    return AnalyticsAggregate(
        days_live=10,
        total_page_views=200,
        unique_visitors=185,
        total_signups=0,
        conversion_rate=0.0,
        views_by_source={"google-search": 120, "reddit": 50, "hackernews": 30},
        signups_by_source={},
        conversion_rate_by_source={
            "google-search": 0.0,
            "reddit": 0.0,
            "hackernews": 0.0,
        },
        warm_network_bias_index=0.0,
        time_on_page_p50_seconds=18,
        time_on_page_p90_seconds=45,
        views_by_day=[15, 22, 28, 24, 18, 19, 20, 21, 16, 17],
        signups_by_day=[0] * 10,
        drop_off_signals={
            "zero_conversion": (
                "≥50 views with zero signups — check CTA visibility or value proposition clarity"
            )
        },
        data_quality_notes=[],
    )


def build_insufficient_data(_experiment_id: UUID) -> AnalyticsAggregate:
    return AnalyticsAggregate(
        days_live=4,
        total_page_views=5,
        unique_visitors=5,
        total_signups=0,
        conversion_rate=0.0,
        views_by_source={"unknown": 5},
        signups_by_source={},
        conversion_rate_by_source={"unknown": 0.0},
        warm_network_bias_index=0.0,
        time_on_page_p50_seconds=22,
        time_on_page_p90_seconds=60,
        views_by_day=[2, 1, 1, 1],
        signups_by_day=[0, 0, 0, 0],
        drop_off_signals={},
        data_quality_notes=[],
    )


def build_bimodal_engagement(_experiment_id: UUID) -> AnalyticsAggregate:
    return AnalyticsAggregate(
        days_live=7,
        total_page_views=80,
        unique_visitors=72,
        total_signups=6,
        conversion_rate=0.083,
        views_by_source={"product-hunt": 40, "twitter": 25, "newsletter": 15},
        signups_by_source={"product-hunt": 4, "twitter": 1, "newsletter": 1},
        conversion_rate_by_source={
            "product-hunt": 0.1,
            "twitter": 0.04,
            "newsletter": 0.067,
        },
        warm_network_bias_index=0.3125,
        time_on_page_p50_seconds=0,
        time_on_page_p90_seconds=240,
        views_by_day=[15, 18, 12, 10, 9, 8, 8],
        signups_by_day=[2, 2, 1, 0, 1, 0, 0],
        drop_off_signals={
            "bimodal_engagement": (
                "Engagement distribution is bimodal — half of visitors leave instantly, "
                "the other half spend significant time"
            )
        },
        data_quality_notes=[],
    )


def build_high_warm_high_conversion(_experiment_id: UUID) -> AnalyticsAggregate:
    return AnalyticsAggregate(
        days_live=6,
        total_page_views=60,
        unique_visitors=55,
        total_signups=15,
        conversion_rate=0.273,
        views_by_source={"twitter": 35, "linkedin": 19, "google-search": 6},
        signups_by_source={"twitter": 11, "linkedin": 4, "google-search": 0},
        conversion_rate_by_source={
            "twitter": 0.314,
            "linkedin": 0.211,
            "google-search": 0.0,
        },
        warm_network_bias_index=0.9,
        time_on_page_p50_seconds=88,
        time_on_page_p90_seconds=210,
        views_by_day=[12, 14, 10, 9, 8, 7],
        signups_by_day=[4, 3, 3, 2, 2, 1],
        drop_off_signals={},
        data_quality_notes=[],
    )


SCENARIOS: dict[str, callable] = {
    "warm_only_low_volume": build_warm_only_low_volume,
    "cold_high_volume_no_conversion": build_cold_high_volume_no_conversion,
    "insufficient_data": build_insufficient_data,
    "bimodal_engagement": build_bimodal_engagement,
    "high_warm_high_conversion": build_high_warm_high_conversion,
}


def build_scenario_analytics(scenario_name: str, experiment_id: UUID) -> AnalyticsAggregate:
    if scenario_name not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_name}. Available: {sorted(SCENARIOS)}"
        )
    return SCENARIOS[scenario_name](experiment_id)
