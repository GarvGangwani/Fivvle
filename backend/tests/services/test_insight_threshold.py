"""Unit tests for server-authoritative insight min-data threshold."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.db.models.waitlist_signup import WaitlistSignup
from app.services.insight_threshold import (
    MIN_DAYS_LIVE,
    MIN_PAGE_VIEWS,
    MIN_SIGNUPS,
    compute_insight_threshold,
)

# Verbatim 409 detail from generate_insight — keep in sync with experiments.py.
_GENERATE_INSIGHT_INSUFFICIENT_DETAIL = (
    "Insufficient data for insight generation. Need at least one of: "
    "10 page views, 1 signup, or 7 days since landing page went live. "
    "Current: {page_view_count} views, {signup_count} signups, "
    "{days_live} day(s) live."
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _live_experiment(
    db: AsyncSession,
    *,
    days_ago: int = 0,
) -> Experiment:
    user = User(
        firebase_uid=f"threshold-{uuid4()}",
        email=f"threshold-{uuid4()}@example.com",
        name="Threshold User",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        slug=f"thr-{uuid4().hex[:8]}",
        name="Threshold test",
        raw_idea="A long enough raw idea for insight threshold service tests.",
        status=ExperimentStatus.LANDING_LIVE,
        refinement_count=0,
    )
    db.add(experiment)
    await db.flush()
    live_at = datetime.now(UTC) - timedelta(days=days_ago)
    landing = LandingPage(
        experiment_id=experiment.id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="Test headline for threshold",
        problem_desc="Problem description for threshold fixture.",
        solution_desc="Solution description for threshold fixture.",
        cta_text="Join the waitlist",
        cta_type=LandingCtaType.WAITLIST,
        slug=f"thr-lp-{uuid4().hex[:12]}",
        live_at=live_at,
    )
    db.add(landing)
    await db.flush()
    db.add(
        LandingPagePublish(
            landing_page_id=landing.id,
            publish_number=1,
            published_at=live_at,
            ended_at=None,
        )
    )
    await db.commit()
    return experiment


@pytest.mark.asyncio
async def test_compute_insight_threshold_zero_data(db_session: AsyncSession) -> None:
    experiment = await _live_experiment(db_session)
    state = await compute_insight_threshold(db_session, experiment.id)
    assert state.met is False
    assert state.views_current == 0
    assert state.views_target == MIN_PAGE_VIEWS
    assert state.signups_current == 0
    assert state.signups_target == MIN_SIGNUPS
    assert state.days_current == 0
    assert state.days_target == MIN_DAYS_LIVE


@pytest.mark.asyncio
async def test_compute_insight_threshold_views_only(db_session: AsyncSession) -> None:
    from app.services.landing_page_publish_service import get_open_cohort_for_experiment

    experiment = await _live_experiment(db_session)
    cohort = await get_open_cohort_for_experiment(db_session, experiment.id)
    assert cohort is not None
    for i in range(MIN_PAGE_VIEWS):
        db_session.add(
            PageView(
                experiment_id=experiment.id,
                publish_id=cohort.id,
                source_tag="direct",
                ip_address=f"10.1.0.{i}",
            )
        )
    await db_session.commit()
    state = await compute_insight_threshold(db_session, experiment.id)
    assert state.met is True
    assert state.views_current == MIN_PAGE_VIEWS


@pytest.mark.asyncio
async def test_compute_insight_threshold_signups_only(db_session: AsyncSession) -> None:
    from app.services.landing_page_publish_service import get_open_cohort_for_experiment

    experiment = await _live_experiment(db_session)
    cohort = await get_open_cohort_for_experiment(db_session, experiment.id)
    assert cohort is not None
    db_session.add(
        PageView(
            experiment_id=experiment.id,
            publish_id=cohort.id,
            source_tag="direct",
            ip_address="10.1.0.1",
        )
    )
    db_session.add(
        WaitlistSignup(
            experiment_id=experiment.id,
            publish_id=cohort.id,
            email="alone@example.com",
            source_tag="direct",
        )
    )
    await db_session.commit()
    state = await compute_insight_threshold(db_session, experiment.id)
    assert state.met is True
    assert state.signups_current == MIN_SIGNUPS
    assert state.views_current == 1
    assert state.views_current < MIN_PAGE_VIEWS


@pytest.mark.asyncio
async def test_compute_insight_threshold_days_only(db_session: AsyncSession) -> None:
    experiment = await _live_experiment(db_session, days_ago=MIN_DAYS_LIVE)
    state = await compute_insight_threshold(db_session, experiment.id)
    assert state.met is True
    assert state.days_current >= MIN_DAYS_LIVE
    assert state.views_current == 0
    assert state.signups_current == 0


def test_generate_insight_409_copy_matches_threshold_constants() -> None:
    """Guard: threshold constant changed but the 409 copy did not."""
    sample = _GENERATE_INSIGHT_INSUFFICIENT_DETAIL.format(
        page_view_count=0,
        signup_count=0,
        days_live=0,
    )
    assert str(MIN_PAGE_VIEWS) in sample, (
        "threshold constant changed but the 409 copy did not "
        f"(expected views target {MIN_PAGE_VIEWS!r} in message)"
    )
    assert str(MIN_SIGNUPS) in sample, (
        "threshold constant changed but the 409 copy did not "
        f"(expected signups target {MIN_SIGNUPS!r} in message)"
    )
    assert str(MIN_DAYS_LIVE) in sample, (
        "threshold constant changed but the 409 copy did not "
        f"(expected days target {MIN_DAYS_LIVE!r} in message)"
    )
