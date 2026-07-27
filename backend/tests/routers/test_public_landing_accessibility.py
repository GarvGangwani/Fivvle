"""Regression: public landing fetch is artifact-gated, not status-gated."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.user import User
from app.routers.public import _fetch_live_landing_page


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _seed_published(
    db: AsyncSession,
    *,
    status: ExperimentStatus,
    live_at: datetime | None,
) -> tuple[LandingPage, Experiment]:
    user = User(
        firebase_uid=f"public-lp-{uuid4()}",
        email=f"public-lp-{uuid4()}@example.com",
        name="Public LP Test",
    )
    db.add(user)
    await db.flush()

    experiment = Experiment(
        user_id=user.id,
        raw_idea="Test idea",
        status=status,
    )
    db.add(experiment)
    await db.flush()

    slug = f"pub-{uuid4().hex[:12]}"
    landing = LandingPage(
        experiment_id=experiment.id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="Headline",
        problem_desc="Problem",
        solution_desc="Solution",
        cta_text="Join",
        cta_type=LandingCtaType.WAITLIST,
        slug=slug,
        live_at=live_at,
    )
    db.add(landing)
    await db.commit()
    await db.refresh(landing)
    await db.refresh(experiment)
    return landing, experiment


@pytest.mark.asyncio
async def test_fetch_live_returns_row_when_research_ready_and_live_at_set(
    db_session: AsyncSession,
) -> None:
    """Evidence rerun demotes status to RESEARCH_READY but must not 404 a live page."""
    landing, _experiment = await _seed_published(
        db_session,
        status=ExperimentStatus.RESEARCH_READY,
        live_at=datetime.now(timezone.utc),
    )
    row = await _fetch_live_landing_page(db_session, landing.slug)
    assert row is not None
    fetched_lp, fetched_exp = row
    assert fetched_lp.id == landing.id
    assert fetched_exp.status == ExperimentStatus.RESEARCH_READY


@pytest.mark.asyncio
async def test_fetch_live_returns_none_when_archived(
    db_session: AsyncSession,
) -> None:
    landing, _experiment = await _seed_published(
        db_session,
        status=ExperimentStatus.ARCHIVED,
        live_at=datetime.now(timezone.utc),
    )
    row = await _fetch_live_landing_page(db_session, landing.slug)
    assert row is None


@pytest.mark.asyncio
async def test_fetch_live_returns_none_when_live_at_null(
    db_session: AsyncSession,
) -> None:
    landing, _experiment = await _seed_published(
        db_session,
        status=ExperimentStatus.LANDING_LIVE,
        live_at=None,
    )
    row = await _fetch_live_landing_page(db_session, landing.slug)
    assert row is None
