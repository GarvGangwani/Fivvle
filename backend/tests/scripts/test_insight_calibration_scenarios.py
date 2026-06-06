"""Unit tests for synthetic insight calibration AnalyticsAggregate fixtures."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.insight_calibration_scenarios import (  # noqa: E402
    SCENARIOS,
    build_scenario_analytics,
)


@pytest.mark.parametrize("scenario_name", list(SCENARIOS))
def test_each_scenario_constructs_valid_analytics_aggregate(scenario_name: str) -> None:
    exp_id = uuid4()
    aggregate = build_scenario_analytics(scenario_name, exp_id)
    round_tripped = type(aggregate).model_validate(aggregate.model_dump())
    assert round_tripped == aggregate


def test_warm_only_low_volume_warm_network_bias() -> None:
    agg = build_scenario_analytics("warm_only_low_volume", uuid4())
    assert agg.warm_network_bias_index == 1.0


def test_cold_high_volume_no_conversion_drop_off_signal() -> None:
    agg = build_scenario_analytics("cold_high_volume_no_conversion", uuid4())
    assert "zero_conversion" in agg.drop_off_signals


def test_insufficient_data_low_volume_and_short_live() -> None:
    agg = build_scenario_analytics("insufficient_data", uuid4())
    assert agg.days_live < 7
    assert agg.total_page_views < 10


def test_bimodal_engagement_drop_off_signal() -> None:
    agg = build_scenario_analytics("bimodal_engagement", uuid4())
    assert "bimodal_engagement" in agg.drop_off_signals


def test_high_warm_high_conversion_bias_and_rate() -> None:
    agg = build_scenario_analytics("high_warm_high_conversion", uuid4())
    assert agg.warm_network_bias_index > 0.5
    assert agg.conversion_rate > 0.2


def test_build_scenario_analytics_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown scenario"):
        build_scenario_analytics("not_a_real_scenario", uuid4())


@pytest.mark.parametrize("scenario_name", list(SCENARIOS))
def test_views_by_day_length_matches_days_live(scenario_name: str) -> None:
    agg = build_scenario_analytics(scenario_name, uuid4())
    assert len(agg.views_by_day) == agg.days_live


@pytest.mark.parametrize("scenario_name", list(SCENARIOS))
def test_signups_by_day_length_matches_days_live(scenario_name: str) -> None:
    agg = build_scenario_analytics(scenario_name, uuid4())
    assert len(agg.signups_by_day) == agg.days_live
