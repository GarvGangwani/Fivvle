"""Tests for waitlist signup geolocation enrichment."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.integrations.ip_geolocation import IpGeolocation
from app.services.analytics_aggregator import build_analytics_aggregate
from app.services.waitlist_service import record_waitlist_signup


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _persist_live_experiment(db: AsyncSession) -> Experiment:
    user = User(
        firebase_uid=f"waitlist-geo-{uuid4()}",
        email=f"waitlist-geo-{uuid4()}@example.com",
        name="Waitlist Geo Test User",
    )
    db.add(user)
    await db.flush()

    experiment = Experiment(
        user_id=user.id,
        raw_idea="Test idea",
        status=ExperimentStatus.LANDING_LIVE,
    )
    db.add(experiment)
    await db.flush()

    live_at = datetime.now(timezone.utc)
    landing_page = LandingPage(
        experiment_id=experiment.id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="Test headline",
        problem_desc="Problem",
        solution_desc="Solution",
        cta_text="Join the waitlist",
        cta_type=LandingCtaType.WAITLIST,
        slug=f"geo-test-{uuid4().hex[:12]}",
        live_at=live_at,
    )
    db.add(landing_page)
    await db.commit()
    await db.refresh(experiment)
    return experiment


@pytest.mark.asyncio
async def test_record_waitlist_signup_stores_geo_fields(db_session: AsyncSession) -> None:
    experiment = await _persist_live_experiment(db_session)
    geo = IpGeolocation(city="Austin", region="Texas", country="United States")

    with patch(
        "app.services.waitlist_service.lookup_ip_geolocation",
        new=AsyncMock(return_value=geo),
    ):
        signup = await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="founder@example.com",
            source_tag="twitter",
            client_ip="8.8.8.8",
        )

    assert signup.geo_city == "Austin"
    assert signup.geo_region == "Texas"
    assert signup.geo_country == "United States"
    assert signup.ip_address == "8.8.8.8"


@pytest.mark.asyncio
async def test_record_waitlist_signup_skips_geo_for_private_ip(
    db_session: AsyncSession,
) -> None:
    experiment = await _persist_live_experiment(db_session)

    with patch(
        "app.services.waitlist_service.lookup_ip_geolocation",
        new=AsyncMock(),
    ) as lookup_mock:
        signup = await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="local@example.com",
            source_tag=None,
            client_ip="127.0.0.1",
        )

    lookup_mock.assert_not_called()
    assert signup.geo_city is None
    assert signup.geo_region is None
    assert signup.geo_country is None
    assert signup.ip_address is None


@pytest.mark.asyncio
async def test_analytics_aggregate_groups_signups_by_location(
    db_session: AsyncSession,
) -> None:
    experiment = await _persist_live_experiment(db_session)
    now = datetime.now(timezone.utc)

    for source_tag in ("twitter", "linkedin", "email"):
        db_session.add(
            PageView(
                experiment_id=experiment.id,
                source_tag=source_tag,
                ip_address="9.9.9.9",
                ts=now,
            )
        )
    await db_session.commit()

    with patch(
        "app.services.waitlist_service.lookup_ip_geolocation",
        side_effect=[
            IpGeolocation(city="Austin", region="Texas", country="United States"),
            IpGeolocation(city="Austin", region="Texas", country="United States"),
            IpGeolocation(city="Toronto", region="Ontario", country="Canada"),
        ],
    ):
        await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="one@example.com",
            source_tag="twitter",
            client_ip="1.1.1.1",
        )
        await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="two@example.com",
            source_tag="linkedin",
            client_ip="2.2.2.2",
        )
        await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="three@example.com",
            source_tag="email",
            client_ip="3.3.3.3",
        )

    aggregate = await build_analytics_aggregate(db_session, experiment.id)
    assert len(aggregate.signups_by_location) == 2
    assert aggregate.signups_by_location[0].count == 2
    assert aggregate.signups_by_location[0].city == "Austin"
    assert aggregate.signups_by_location[1].city == "Toronto"
