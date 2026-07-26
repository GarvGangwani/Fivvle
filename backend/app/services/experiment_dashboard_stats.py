"""Batch behavioral metrics for dashboard experiment cards."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.schemas.experiment import ExperimentCardStats
from app.services.wallet_service import list_experiments_with_purchased_service

_LIVE_LANDING_STATUSES = frozenset(
    {
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.COMPLETED,
    }
)


async def build_experiment_card_stats_map(
    db: AsyncSession,
    experiments: list[Experiment],
    *,
    user_id: UUID,
) -> dict[UUID, ExperimentCardStats]:
    """Return page-view and waitlist counts for live projects with metrics unlocked.

    Counts are scoped to each experiment's current (open) publish cohort.
    """
    live_ids = [exp.id for exp in experiments if exp.status in _LIVE_LANDING_STATUSES]
    if not live_ids:
        return {}

    unlocked_ids = await list_experiments_with_purchased_service(
        db,
        user_id=user_id,
        service="metricsAnalysis",
        experiment_ids=live_ids,
    )
    if not unlocked_ids:
        return {}

    open_cohort_rows = (
        await db.execute(
            select(LandingPage.experiment_id, LandingPagePublish.id)
            .join(
                LandingPagePublish,
                LandingPagePublish.landing_page_id == LandingPage.id,
            )
            .where(
                LandingPage.experiment_id.in_(unlocked_ids),
                LandingPagePublish.ended_at.is_(None),
            ),
        )
    ).all()
    open_by_experiment = {row[0]: row[1] for row in open_cohort_rows}
    open_publish_ids = list(open_by_experiment.values())
    if not open_publish_ids:
        return {
            experiment_id: ExperimentCardStats(page_views=0, waitlist_signups=0)
            for experiment_id in unlocked_ids
        }

    views_stmt = (
        select(PageView.experiment_id, func.count(PageView.id))
        .where(PageView.publish_id.in_(open_publish_ids))
        .group_by(PageView.experiment_id)
    )
    signups_stmt = (
        select(WaitlistSignup.experiment_id, func.count(WaitlistSignup.id))
        .where(WaitlistSignup.publish_id.in_(open_publish_ids))
        .group_by(WaitlistSignup.experiment_id)
    )

    views_result = await db.execute(views_stmt)
    signups_result = await db.execute(signups_stmt)

    views_by_id = {row[0]: int(row[1]) for row in views_result.all()}
    signups_by_id = {row[0]: int(row[1]) for row in signups_result.all()}

    stats: dict[UUID, ExperimentCardStats] = {}
    for experiment_id in unlocked_ids:
        stats[experiment_id] = ExperimentCardStats(
            page_views=views_by_id.get(experiment_id, 0),
            waitlist_signups=signups_by_id.get(experiment_id, 0),
        )
    return stats
