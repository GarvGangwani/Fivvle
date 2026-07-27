"""Tests that page-view ingest stamps publish_id (PR-3 Step 4)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.services.landing_page_publish_service import get_open_cohort


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _seed_live_landing(
    db: AsyncSession,
    *,
    with_cohort: bool,
) -> tuple[Experiment, LandingPage]:
    user = User(
        firebase_uid=f"pv-pub-{uuid4()}",
        email=f"pv-pub-{uuid4()}@example.com",
        name="PageView Publish Test",
    )
    db.add(user)
    await db.flush()

    experiment = Experiment(
        user_id=user.id,
        raw_idea="Test",
        status=ExperimentStatus.LANDING_LIVE,
    )
    db.add(experiment)
    await db.flush()

    now = datetime.now(timezone.utc)
    landing = LandingPage(
        experiment_id=experiment.id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="H",
        problem_desc="P",
        solution_desc="S",
        cta_text="Join",
        cta_type=LandingCtaType.WAITLIST,
        slug=f"pvpub-{uuid4().hex[:10]}",
        live_at=now,
    )
    db.add(landing)
    await db.flush()
    if with_cohort:
        db.add(
            LandingPagePublish(
                landing_page_id=landing.id,
                publish_number=1,
                published_at=now,
                ended_at=None,
            )
        )
    await db.commit()
    await db.refresh(experiment)
    await db.refresh(landing)
    return experiment, landing


async def _ingest_page_view(
    db: AsyncSession,
    *,
    experiment_id,
    landing_page_id,
) -> PageView:
    """Mirror public.record_page_view cohort-stamping without HTTP/INET issues."""
    cohort = await get_open_cohort(db, landing_page_id)
    publish_id = cohort.id if cohort is not None else None
    page_view = PageView(
        experiment_id=experiment_id,
        publish_id=publish_id,
        source_tag="twitter",
        time_on_page_sec=12,
        ip_address="8.8.8.8",
    )
    db.add(page_view)
    await db.commit()
    await db.refresh(page_view)
    return page_view


@pytest.mark.asyncio
async def test_page_view_stamps_publish_id_when_cohort_open(
    db_session: AsyncSession,
) -> None:
    experiment, landing = await _seed_live_landing(db_session, with_cohort=True)
    cohort = (
        await db_session.execute(
            select(LandingPagePublish).where(
                LandingPagePublish.landing_page_id == landing.id,
                LandingPagePublish.ended_at.is_(None),
            ),
        )
    ).scalar_one()

    pv = await _ingest_page_view(
        db_session,
        experiment_id=experiment.id,
        landing_page_id=landing.id,
    )
    assert pv.publish_id == cohort.id


@pytest.mark.asyncio
async def test_page_view_stamps_none_when_no_open_cohort(
    db_session: AsyncSession,
) -> None:
    experiment, landing = await _seed_live_landing(db_session, with_cohort=False)
    with patch("app.routers.public.get_logger"):
        pv = await _ingest_page_view(
            db_session,
            experiment_id=experiment.id,
            landing_page_id=landing.id,
        )
    assert pv.publish_id is None
