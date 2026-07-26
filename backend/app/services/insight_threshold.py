"""Server-authoritative min-data threshold for Insight generation.

Single source of truth for the ratchet (≥MIN_PAGE_VIEWS views OR ≥MIN_SIGNUPS
signups OR ≥MIN_DAYS_LIVE days live). Routers and analytics must call
``compute_insight_threshold`` — do not re-encode these numbers elsewhere.

Counts and days_live default to the current (open) publish cohort.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.services.landing_page_publish_service import get_open_cohort

MIN_PAGE_VIEWS = 10
MIN_SIGNUPS = 1
MIN_DAYS_LIVE = 7


@dataclass(frozen=True, slots=True)
class InsightThresholdState:
    """Current progress toward the Insight min-data threshold."""

    met: bool
    views_current: int
    views_target: int
    signups_current: int
    signups_target: int
    days_current: int
    days_target: int


async def compute_insight_threshold(
    db: AsyncSession,
    experiment_id: UUID,
) -> InsightThresholdState:
    """Compute threshold state for the current open publish cohort.

    ``days_current`` is 0 when LandingPage is missing, ``live_at`` is None, or
    no open cohort exists — defensive; callers that require a live page should
    gate earlier.
    """
    landing = (
        await db.execute(
            select(LandingPage).where(LandingPage.experiment_id == experiment_id),
        )
    ).scalar_one_or_none()

    if landing is None or landing.live_at is None:
        return InsightThresholdState(
            met=False,
            views_current=0,
            views_target=MIN_PAGE_VIEWS,
            signups_current=0,
            signups_target=MIN_SIGNUPS,
            days_current=0,
            days_target=MIN_DAYS_LIVE,
        )

    cohort = await get_open_cohort(db, landing.id)
    if cohort is None:
        return InsightThresholdState(
            met=False,
            views_current=0,
            views_target=MIN_PAGE_VIEWS,
            signups_current=0,
            signups_target=MIN_SIGNUPS,
            days_current=0,
            days_target=MIN_DAYS_LIVE,
        )

    views_stmt = select(func.count(PageView.id)).where(
        PageView.experiment_id == experiment_id,
        PageView.publish_id == cohort.id,
    )
    signups_stmt = select(func.count(WaitlistSignup.id)).where(
        WaitlistSignup.experiment_id == experiment_id,
        WaitlistSignup.publish_id == cohort.id,
    )

    views_current = int((await db.execute(views_stmt)).scalar_one() or 0)
    signups_current = int((await db.execute(signups_stmt)).scalar_one() or 0)

    now = datetime.now(timezone.utc)
    period_end = cohort.ended_at or now
    days_current = max((period_end - cohort.published_at).days, 0)

    met = (
        views_current >= MIN_PAGE_VIEWS
        or signups_current >= MIN_SIGNUPS
        or days_current >= MIN_DAYS_LIVE
    )

    return InsightThresholdState(
        met=met,
        views_current=views_current,
        views_target=MIN_PAGE_VIEWS,
        signups_current=signups_current,
        signups_target=MIN_SIGNUPS,
        days_current=days_current,
        days_target=MIN_DAYS_LIVE,
    )
