"""Unit tests for public landing page status rules."""

from app.db.enums import ExperimentStatus
from app.utils.landing_page_public import (
    PUBLIC_LANDING_PAGE_STATUSES,
    is_landing_page_editable,
    is_public_landing_page_accessible,
)


def test_insight_lifecycle_statuses_remain_public() -> None:
    for status in (
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.COMPLETED,
    ):
        assert is_public_landing_page_accessible(status)


def test_archived_landing_page_not_public() -> None:
    assert not is_public_landing_page_accessible(ExperimentStatus.ARCHIVED)


def test_draft_landing_page_not_public() -> None:
    assert not is_public_landing_page_accessible(ExperimentStatus.LANDING_DRAFT)


def test_public_status_set_includes_analyzing_legacy() -> None:
    assert ExperimentStatus.ANALYZING in PUBLIC_LANDING_PAGE_STATUSES


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
