"""Which experiment statuses keep a published landing page publicly accessible."""

from app.db.enums import ExperimentStatus

# Published pages stay live while insight runs and after the report is ready.
# ARCHIVED experiments are intentionally excluded (AGENTS.md).
PUBLIC_LANDING_PAGE_STATUSES: frozenset[ExperimentStatus] = frozenset(
    {
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.COMPLETED,
        ExperimentStatus.ANALYZING,
    }
)

# Founders may edit copy/design while the page is live through COMPLETED.
# Blocked only when archived or while generation is in flight.
LANDING_PAGE_EDITABLE_STATUSES: frozenset[ExperimentStatus] = frozenset(
    {
        ExperimentStatus.LANDING_DRAFT,
        *PUBLIC_LANDING_PAGE_STATUSES,
    }
)


def is_public_landing_page_accessible(status: ExperimentStatus) -> bool:
    return status in PUBLIC_LANDING_PAGE_STATUSES


def is_landing_page_editable(status: ExperimentStatus) -> bool:
    return status in LANDING_PAGE_EDITABLE_STATUSES
