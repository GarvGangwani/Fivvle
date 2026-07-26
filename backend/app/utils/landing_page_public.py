"""Which landing pages remain publicly accessible, and when founders may edit them."""

from __future__ import annotations

from datetime import datetime

from app.db.enums import ExperimentStatus

# Founders may edit copy/design while the page is draft through COMPLETED.
# Blocked only when archived or while generation is in flight.
# (Public reachability is artifact-gated via live_at — see
# is_public_landing_page_accessible — and is intentionally separate.)
LANDING_PAGE_EDITABLE_STATUSES: frozenset[ExperimentStatus] = frozenset(
    {
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.COMPLETED,
        ExperimentStatus.ANALYZING,
    }
)


def is_public_landing_page_accessible(
    status: ExperimentStatus,
    live_at: datetime | None,
) -> bool:
    """Public reachability: published artifact exists and experiment is not archived."""
    return status != ExperimentStatus.ARCHIVED and live_at is not None


def is_landing_page_editable(status: ExperimentStatus) -> bool:
    return status in LANDING_PAGE_EDITABLE_STATUSES
