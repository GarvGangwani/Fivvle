"""Tests for ExperimentStatus insight sub-states (B4)."""

from __future__ import annotations

from app.db.enums import ExperimentStatus


def test_insight_substates_are_members() -> None:
    assert ExperimentStatus.INSIGHT_GENERATING in ExperimentStatus
    assert ExperimentStatus.INSIGHT_READY in ExperimentStatus
    assert ExperimentStatus.INSIGHT_FAILED in ExperimentStatus


def test_insight_substates_string_values() -> None:
    assert ExperimentStatus.INSIGHT_GENERATING == "INSIGHT_GENERATING"
    assert ExperimentStatus.INSIGHT_READY == "INSIGHT_READY"
    assert ExperimentStatus.INSIGHT_FAILED == "INSIGHT_FAILED"


def test_existing_states_preserved() -> None:
    assert ExperimentStatus.ANALYZING == "ANALYZING"
    assert ExperimentStatus.COMPLETED == "COMPLETED"
    assert ExperimentStatus.ARCHIVED == "ARCHIVED"
    assert ExperimentStatus.RESEARCHING == "RESEARCHING"
    assert ExperimentStatus.LANDING_LIVE == "LANDING_LIVE"


def test_experiment_status_count() -> None:
    assert len(list(ExperimentStatus)) == 20


def test_models_import_with_new_enum_members() -> None:
    import app.db.models  # noqa: F401
