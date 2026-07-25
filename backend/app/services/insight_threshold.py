"""Server-authoritative min-data threshold for Insight generation.

Single source of truth for the ratchet (≥MIN_PAGE_VIEWS views OR ≥MIN_SIGNUPS
signups OR ≥MIN_DAYS_LIVE days live). Routers and analytics must call
``compute_insight_threshold`` — do not re-encode these numbers elsewhere.
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
    """Compute threshold state from page views, signups, and landing live_at.

    ``days_current`` is 0 when LandingPage is missing or ``live_at`` is None —
    defensive; callers that require a live page should gate earlier.
    """
    views_stmt = select(func.count(PageView.id)).where(
        PageView.experiment_id == experiment_id
    )
    signups_stmt = select(func.count(WaitlistSignup.id)).where(
        WaitlistSignup.experiment_id == experiment_id
    )
    landing_stmt = select(LandingPage.live_at).where(
        LandingPage.experiment_id == experiment_id
    )

    views_result = await db.execute(views_stmt)
    signups_result = await db.execute(signups_stmt)
    landing_result = await db.execute(landing_stmt)

    views_current = int(views_result.scalar_one() or 0)
    signups_current = int(signups_result.scalar_one() or 0)
    live_at = landing_result.scalar_one_or_none()

    if live_at is None:
        days_current = 0
    else:
        days_current = max((datetime.now(timezone.utc) - live_at).days, 0)

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
