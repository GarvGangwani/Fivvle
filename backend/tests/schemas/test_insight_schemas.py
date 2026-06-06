"""Unit tests for app.schemas.insight.

Exercises AnalyticsAggregate validators, InsightReportOutputDraft constraints,
Draft/Final sub-schema literals, and extra="forbid" enforcement.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.db.enums import InsightRecommendation
from app.schemas.insight import (
    AnalyticsAggregate,
    ConversionBySourceDraft,
    ConversionSourceCommentaryDraft,
    InsightReportOutputDraft,
    ResearchTakeawayDraft,
    TrafficSummaryDraft,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source_commentary(**overrides: Any) -> ConversionSourceCommentaryDraft:
    defaults: dict[str, Any] = {
        "source_name": "twitter",
        "views": 120,
        "signups": 8,
        "conversion_rate": 0.067,
        "commentary": (
            "Twitter drove the highest cold-traffic conversion at 6.7%, "
            "suggesting the hook resonates on social without warm intros."
        ),
        "confidence": "medium",
    }
    defaults.update(overrides)
    return ConversionSourceCommentaryDraft(**defaults)


def _make_traffic_summary(**overrides: Any) -> TrafficSummaryDraft:
    defaults: dict[str, Any] = {
        "narrative": (
            "Over 14 days the landing page attracted 340 unique visitors with "
            "28 waitlist signups. Cold-traffic sources outperformed warm-network "
            "referrals, an unusual pattern worth monitoring at higher volume."
        ),
        "headline_metric": "8.2% overall conversion (28 signups / 340 views)",
        "confidence": "high",
        "confidence_rationale": (
            "Sample size exceeds minimum thresholds with consistent daily traffic."
        ),
        "source_type": "BEHAVIORAL",
    }
    defaults.update(overrides)
    return TrafficSummaryDraft(**defaults)


def _make_conversion_by_source(**overrides: Any) -> ConversionBySourceDraft:
    defaults: dict[str, Any] = {
        "per_source": [
            _make_source_commentary(),
            _make_source_commentary(
                source_name="linkedin",
                views=80,
                signups=3,
                conversion_rate=0.0375,
                commentary=(
                    "LinkedIn underperformed Twitter despite similar view counts, "
                    "possibly due to a more skeptical professional audience."
                ),
                confidence="low",
            ),
        ],
        "warm_network_bias_commentary": (
            "Warm-network sources (direct, email) account for only 18% of views "
            "but 35% of signups, indicating founder-network skew is moderate."
        ),
        "confidence": "medium",
        "confidence_rationale": (
            "Per-source sample sizes are small; directional signal only."
        ),
    }
    defaults.update(overrides)
    return ConversionBySourceDraft(**defaults)


def _make_research_takeaway(**overrides: Any) -> ResearchTakeawayDraft:
    defaults: dict[str, Any] = {
        "claim": (
            "Cold-traffic conversion exceeds warm-network conversion, inverting "
            "the typical founder-network bias documented in prior experiments."
        ),
        "cited_finding_ids": ["q1-f1"],
        "source_type": "SYNTHESIZED",
        "confidence": "high",
        "confidence_rationale": (
            "Behavioral data and research finding q1-f1 both support this pattern."
        ),
    }
    defaults.update(overrides)
    return ResearchTakeawayDraft(**defaults)


def _make_insight_report_draft(**overrides: Any) -> InsightReportOutputDraft:
    defaults: dict[str, Any] = {
        "traffic_summary": _make_traffic_summary(),
        "conversion_by_source": _make_conversion_by_source(),
        "research_takeaways": [
            _make_research_takeaway(),
            _make_research_takeaway(
                claim=(
                    "Competitor Guru already solves Slack policy Q&A for mid-market "
                    "HR teams, narrowing the differentiation window."
                ),
                cited_finding_ids=["q2-f1", "q2-f2"],
                source_type="COGNITIVE",
                confidence="medium",
                confidence_rationale=(
                    "Backed by two independent findings from the validation report."
                ),
            ),
            _make_research_takeaway(
                claim=(
                    "Time-on-page p90 of 92 seconds suggests visitors read the full "
                    "value proposition before bouncing or signing up."
                ),
                cited_finding_ids=["behavioral-p90"],
                source_type="BEHAVIORAL",
                confidence="low",
                confidence_rationale=(
                    "Single metric with no cohort comparison; directional only."
                ),
            ),
        ],
        "recommendation_type": InsightRecommendation.ITERATE,
        "recommendation": (
            "The experiment shows promising cold-traffic conversion (8.2%) but "
            "faces a narrow differentiation gap against Guru. Iterate on a specific "
            "wedge — automated policy staleness detection — before scaling distribution. "
            "Current signup volume (28) is insufficient to confirm reproducibility."
        ),
        "recommendation_confidence": "medium",
        "recommendation_rationale": (
            "Behavioral conversion is strong but cognitive research reveals direct "
            "competition. Evidence supports iterate, not proceed or kill."
        ),
        "what_would_change_this": (
            "If cold-traffic signups exceed 50 with conversion above 10% over the "
            "next 14 days, upgrade to PROCEED. If conversion drops below 3%, PIVOT."
        ),
    }
    defaults.update(overrides)
    return InsightReportOutputDraft(**defaults)


def _make_analytics_aggregate(**overrides: Any) -> AnalyticsAggregate:
    defaults: dict[str, Any] = {
        "days_live": 3,
        "total_page_views": 150,
        "unique_visitors": 120,
        "total_signups": 12,
        "conversion_rate": 0.08,
        "views_by_source": {"twitter": 80, "linkedin": 50, "direct": 20},
        "signups_by_source": {"twitter": 8, "linkedin": 3, "direct": 1},
        "conversion_rate_by_source": {
            "twitter": 0.10,
            "linkedin": 0.06,
            "direct": 0.05,
        },
        "warm_network_bias_index": 0.18,
        "time_on_page_p50_seconds": 45,
        "time_on_page_p90_seconds": 92,
        "signups_by_day": [3, 5, 4],
        "views_by_day": [40, 55, 55],
        "drop_off_signals": {"hero_bounce": "62% exit before scroll"},
        "data_quality_notes": ["No anomalies detected in traffic patterns."],
    }
    defaults.update(overrides)
    return AnalyticsAggregate(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_analytics_aggregate_happy_path_round_trip() -> None:
    agg = _make_analytics_aggregate()
    restored = AnalyticsAggregate.model_validate_json(agg.model_dump_json())
    assert restored == agg


def test_analytics_aggregate_rejects_signup_source_without_views() -> None:
    with pytest.raises(ValidationError):
        _make_analytics_aggregate(
            views_by_source={"twitter": 80},
            signups_by_source={"twitter": 8, "linkedin": 3},
        )


def test_analytics_aggregate_rejects_mismatched_day_array_lengths() -> None:
    with pytest.raises(ValidationError):
        _make_analytics_aggregate(
            days_live=3,
            views_by_day=[40, 55],
            signups_by_day=[3, 5, 4],
        )


def test_insight_report_output_draft_happy_path() -> None:
    report = _make_insight_report_draft()
    assert len(report.research_takeaways) == 3
    assert report.traffic_summary.confidence == "high"
    assert report.traffic_summary.source_type == "BEHAVIORAL"
    for takeaway in report.research_takeaways:
        assert takeaway.confidence in ("high", "medium", "low")
        assert takeaway.source_type in ("BEHAVIORAL", "COGNITIVE", "SYNTHESIZED")


def test_insight_report_output_draft_rejects_empty_takeaways() -> None:
    with pytest.raises(ValidationError):
        _make_insight_report_draft(research_takeaways=[])


def test_insight_report_output_draft_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        InsightReportOutputDraft(
            **_make_insight_report_draft().model_dump(),
            unexpected_field="nope",
        )


def test_research_takeaway_draft_rejects_empty_cited_finding_ids() -> None:
    with pytest.raises(ValidationError):
        _make_research_takeaway(cited_finding_ids=[])


@pytest.mark.parametrize("confidence", ["high", "medium", "low"])
def test_confidence_label_accepts_valid_values(confidence: str) -> None:
    summary = _make_traffic_summary(confidence=confidence)
    assert summary.confidence == confidence


@pytest.mark.parametrize("bad_confidence", ["HIGH", "none", ""])
def test_confidence_label_rejects_invalid_values(bad_confidence: str) -> None:
    with pytest.raises(ValidationError):
        _make_traffic_summary(confidence=bad_confidence)


@pytest.mark.parametrize("source_type", ["BEHAVIORAL", "COGNITIVE", "SYNTHESIZED"])
def test_source_type_accepts_valid_values(source_type: str) -> None:
    summary = _make_traffic_summary(source_type=source_type)
    assert summary.source_type == source_type


@pytest.mark.parametrize("bad_source_type", ["behavioral", "MIXED", ""])
def test_source_type_rejects_invalid_values(bad_source_type: str) -> None:
    with pytest.raises(ValidationError):
        _make_traffic_summary(source_type=bad_source_type)


def test_schema_version_frozen_at_one() -> None:
    with pytest.raises(ValidationError):
        _make_traffic_summary(schema_version=2)

    with pytest.raises(ValidationError):
        _make_analytics_aggregate(schema_version=2)

    with pytest.raises(ValidationError):
        _make_insight_report_draft(schema_version=2)
