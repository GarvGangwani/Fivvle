"""Publish cohort helpers for landing pages (Signal analytics isolation)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.landing_page_publish import LandingPagePublish


async def get_open_cohort(
    db: AsyncSession,
    landing_page_id: UUID,
) -> LandingPagePublish | None:
    """Return the open cohort for a landing page (`ended_at IS NULL`), if any."""
    result = await db.execute(
        select(LandingPagePublish)
        .where(
            LandingPagePublish.landing_page_id == landing_page_id,
            LandingPagePublish.ended_at.is_(None),
        )
        .order_by(LandingPagePublish.publish_number.desc())
        .limit(1),
    )
    return result.scalar_one_or_none()


async def get_open_cohort_for_experiment(
    db: AsyncSession,
    experiment_id: UUID,
) -> LandingPagePublish | None:
    """Return the open cohort for an experiment's landing page, if any."""
    from app.db.models.landing_page import LandingPage  # noqa: PLC0415

    lp_id = (
        await db.execute(
            select(LandingPage.id).where(LandingPage.experiment_id == experiment_id),
        )
    ).scalar_one_or_none()
    if lp_id is None:
        return None
    return await get_open_cohort(db, lp_id)


async def count_publishes_for_landing(
    db: AsyncSession,
    landing_page_id: UUID,
) -> int:
    from sqlalchemy import func  # noqa: PLC0415

    result = await db.execute(
        select(func.count())
        .select_from(LandingPagePublish)
        .where(LandingPagePublish.landing_page_id == landing_page_id),
    )
    return int(result.scalar_one() or 0)


async def get_cohort_by_id(
    db: AsyncSession,
    publish_id: UUID,
) -> LandingPagePublish | None:
    result = await db.execute(
        select(LandingPagePublish).where(LandingPagePublish.id == publish_id),
    )
    return result.scalar_one_or_none()


async def create_first_cohort(
    db: AsyncSession,
    landing_page_id: UUID,
) -> LandingPagePublish:
    """Insert cohort #1 for a first-time publish. Caller commits."""
    cohort = LandingPagePublish(
        landing_page_id=landing_page_id,
        publish_number=1,
        ended_at=None,
    )
    db.add(cohort)
    await db.flush()
    return cohort


async def close_and_open_next_cohort(
    db: AsyncSession,
    landing_page_id: UUID,
) -> LandingPagePublish:
    """Close the open cohort and open the next publish number. Caller commits.

    Raises:
        ValueError: if no open cohort exists.
    """
    open_cohort = await get_open_cohort(db, landing_page_id)
    if open_cohort is None:
        raise ValueError("No open publish cohort")

    now = datetime.now(timezone.utc)
    open_cohort.ended_at = now
    next_cohort = LandingPagePublish(
        landing_page_id=landing_page_id,
        publish_number=open_cohort.publish_number + 1,
        published_at=now,
        ended_at=None,
    )
    db.add(next_cohort)
    await db.flush()
    return next_cohort
