"""Tests for dashboard experiment card stats."""

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
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.db.models.waitlist_signup import WaitlistSignup
from app.services.experiment_dashboard_stats import build_experiment_card_stats_map
from app.services.wallet_service import purchase_service_for_experiment


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _experiment(
    db: AsyncSession,
    *,
    status: ExperimentStatus,
) -> tuple[User, Experiment]:
    user = User(
        firebase_uid=f"card-stats-{uuid4()}",
        email=f"card-stats-{uuid4()}@example.com",
        name="Card Stats User",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        slug=f"proj-{uuid4().hex[:8]}",
        name="Stats test",
        raw_idea="A long enough raw idea for validation tests in dashboard stats.",
        status=status,
        refinement_count=0,
    )
    db.add(experiment)
    await db.flush()
    return user, experiment


@pytest.mark.asyncio
async def test_build_experiment_card_stats_map_requires_metrics_unlock(
    db_session: AsyncSession,
) -> None:
    user, live = await _experiment(db_session, status=ExperimentStatus.LANDING_LIVE)
    _user2, draft = await _experiment(db_session, status=ExperimentStatus.LANDING_DRAFT)

    now = datetime.now(timezone.utc)
    landing = LandingPage(
        experiment_id=live.id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="H",
        problem_desc="P",
        solution_desc="S",
        cta_text="Join",
        cta_type=LandingCtaType.WAITLIST,
        slug=f"card-{uuid4().hex[:10]}",
        live_at=now,
    )
    db_session.add(landing)
    await db_session.flush()
    cohort = LandingPagePublish(
        landing_page_id=landing.id,
        publish_number=1,
        published_at=now,
        ended_at=None,
    )
    db_session.add(cohort)
    await db_session.flush()

    db_session.add_all(
        [
            PageView(
                experiment_id=live.id,
                publish_id=cohort.id,
                source_tag="direct",
            ),
            PageView(
                experiment_id=live.id,
                publish_id=cohort.id,
                source_tag="twitter",
            ),
            WaitlistSignup(
                experiment_id=live.id,
                publish_id=cohort.id,
                email="founder@example.com",
                source_tag="direct",
            ),
        ]
    )
    await db_session.commit()

    locked_map = await build_experiment_card_stats_map(
        db_session,
        [live, draft],
        user_id=user.id,
    )
    assert locked_map == {}

    await purchase_service_for_experiment(
        db_session,
        user_id=user.id,
        service="metricsAnalysis",
        experiment_id=live.id,
    )
    await db_session.commit()

    stats_map = await build_experiment_card_stats_map(
        db_session,
        [live, draft],
        user_id=user.id,
    )

    assert live.id in stats_map
    assert stats_map[live.id].page_views == 2
    assert stats_map[live.id].waitlist_signups == 1
    assert draft.id not in stats_map
