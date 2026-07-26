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


async def _persist_live_experiment(
    db: AsyncSession,
    *,
    with_cohort: bool = False,
) -> tuple[Experiment, LandingPage]:
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
    await db.flush()
    if with_cohort:
        from app.db.models.landing_page_publish import LandingPagePublish

        db.add(
            LandingPagePublish(
                landing_page_id=landing_page.id,
                publish_number=1,
                published_at=live_at,
                ended_at=None,
            )
        )
    await db.commit()
    await db.refresh(experiment)
    await db.refresh(landing_page)
    return experiment, landing_page


@pytest.mark.asyncio
async def test_record_waitlist_signup_stores_geo_fields(db_session: AsyncSession) -> None:
    experiment, landing_page = await _persist_live_experiment(db_session)
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
            landing_page_id=landing_page.id,
        )

    assert signup.geo_city == "Austin"
    assert signup.geo_region == "Texas"
    assert signup.geo_country == "United States"
    assert signup.ip_address == "8.8.8.8"


@pytest.mark.asyncio
async def test_record_waitlist_signup_skips_geo_for_private_ip(
    db_session: AsyncSession,
) -> None:
    experiment, landing_page = await _persist_live_experiment(db_session)

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
            landing_page_id=landing_page.id,
        )

    lookup_mock.assert_not_called()
    assert signup.geo_city is None
    assert signup.geo_region is None
    assert signup.geo_country is None
    assert signup.ip_address is None


@pytest.mark.asyncio
async def test_record_waitlist_signup_stamps_publish_id_when_cohort_open(
    db_session: AsyncSession,
) -> None:
    experiment, landing_page = await _persist_live_experiment(
        db_session,
        with_cohort=True,
    )
    from app.db.models.landing_page_publish import LandingPagePublish
    from sqlalchemy import select

    cohort = (
        await db_session.execute(
            select(LandingPagePublish).where(
                LandingPagePublish.landing_page_id == landing_page.id,
                LandingPagePublish.ended_at.is_(None),
            ),
        )
    ).scalar_one()

    signup = await record_waitlist_signup(
        db_session,
        experiment_id=experiment.id,
        email="cohort@example.com",
        source_tag="twitter",
        client_ip=None,
        landing_page_id=landing_page.id,
    )
    assert signup.publish_id == cohort.id


@pytest.mark.asyncio
async def test_record_waitlist_signup_stamps_none_when_no_open_cohort(
    db_session: AsyncSession,
) -> None:
    experiment, landing_page = await _persist_live_experiment(
        db_session,
        with_cohort=False,
    )
    signup = await record_waitlist_signup(
        db_session,
        experiment_id=experiment.id,
        email="nocohort@example.com",
        source_tag=None,
        client_ip=None,
        landing_page_id=landing_page.id,
    )
    assert signup.publish_id is None


@pytest.mark.asyncio
async def test_analytics_aggregate_groups_signups_by_location(
    db_session: AsyncSession,
) -> None:
    experiment, landing_page = await _persist_live_experiment(
        db_session,
        with_cohort=True,
    )
    now = datetime.now(timezone.utc)
    from app.db.models.landing_page_publish import LandingPagePublish
    from sqlalchemy import select

    cohort = (
        await db_session.execute(
            select(LandingPagePublish).where(
                LandingPagePublish.landing_page_id == landing_page.id,
                LandingPagePublish.ended_at.is_(None),
            ),
        )
    ).scalar_one()

    for source_tag in ("twitter", "linkedin", "email"):
        db_session.add(
            PageView(
                experiment_id=experiment.id,
                publish_id=cohort.id,
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
            landing_page_id=landing_page.id,
        )
        await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="two@example.com",
            source_tag="linkedin",
            client_ip="2.2.2.2",
            landing_page_id=landing_page.id,
        )
        await record_waitlist_signup(
            db_session,
            experiment_id=experiment.id,
            email="three@example.com",
            source_tag="email",
            client_ip="3.3.3.3",
            landing_page_id=landing_page.id,
        )

    aggregate = await build_analytics_aggregate(db_session, experiment.id)
    assert len(aggregate.signups_by_location) == 2
    assert aggregate.signups_by_location[0].count == 2
    assert aggregate.signups_by_location[0].city == "Austin"
    assert aggregate.signups_by_location[1].city == "Toronto"
