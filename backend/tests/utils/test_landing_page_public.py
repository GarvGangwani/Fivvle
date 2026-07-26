"""Unit tests for public landing page accessibility rules."""

from datetime import datetime, timezone

from app.db.enums import ExperimentStatus
from app.utils.landing_page_public import (
    is_landing_page_editable,
    is_public_landing_page_accessible,
)

_NOW = datetime.now(timezone.utc)


def test_live_page_accessible_across_non_archived_statuses() -> None:
    for status in (
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.COMPLETED,
        ExperimentStatus.ANALYZING,
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.LANDING_DRAFT,
    ):
        assert is_public_landing_page_accessible(status, _NOW)


def test_archived_landing_page_not_public_even_with_live_at() -> None:
    assert not is_public_landing_page_accessible(ExperimentStatus.ARCHIVED, _NOW)


def test_not_public_when_live_at_missing() -> None:
    assert not is_public_landing_page_accessible(
        ExperimentStatus.LANDING_LIVE, None
    )
    assert not is_public_landing_page_accessible(
        ExperimentStatus.RESEARCH_READY, None
    )


def test_editable_through_completed_not_archived() -> None:
    for status in (
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.COMPLETED,
    ):
        assert is_landing_page_editable(status)
    assert not is_landing_page_editable(ExperimentStatus.ARCHIVED)
    assert not is_landing_page_editable(ExperimentStatus.LANDING_GENERATING)
