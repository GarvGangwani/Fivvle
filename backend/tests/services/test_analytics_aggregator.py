"""Unit tests for app.services.analytics_aggregator."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import structlog.testing
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.db.models.waitlist_signup import WaitlistSignup
from app.services.analytics_aggregator import (
    LandingPageNotLiveError,
    build_analytics_aggregate,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh async session per test; independent of FastAPI lifespan."""
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _persist_experiment(db: AsyncSession) -> Experiment:
    user = User(
        firebase_uid=f"analytics-agg-{uuid4()}",
        email=f"analytics-agg-{uuid4()}@example.com",
        name="Analytics Aggregator Test User",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        raw_idea="A slack bot that answers HR policy questions so ops managers don't have to.",
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


async def _persist_landing_page(
    db: AsyncSession,
    experiment_id: object,
    *,
    live_at: datetime | None,
) -> LandingPage:
    landing_page = LandingPage(
        experiment_id=experiment_id,
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="Test headline for analytics aggregation",
        problem_desc="Problem description for the test landing page fixture.",
        solution_desc="Solution description for the test landing page fixture.",
        cta_text="Join the waitlist",
        cta_type=LandingCtaType.WAITLIST,
        slug=f"agg-test-{uuid4().hex[:12]}",
        live_at=live_at,
    )
    db.add(landing_page)
    await db.commit()
    await db.refresh(landing_page)
    return landing_page


async def _add_page_view(
    db: AsyncSession,
    *,
    experiment_id: object,
    ts: datetime,
    source_tag: str | None = None,
    ip_address: str | None = "10.0.0.1",
    time_on_page_sec: int | None = 30,
) -> None:
    db.add(
        PageView(
            experiment_id=experiment_id,
            source_tag=source_tag,
            ts=ts,
            ip_address=ip_address,
            time_on_page_sec=time_on_page_sec,
        )
    )


async def _add_signup(
    db: AsyncSession,
    *,
    experiment_id: object,
    ts: datetime,
    source_tag: str | None = None,
    email: str | None = None,
) -> None:
    db.add(
        WaitlistSignup(
            experiment_id=experiment_id,
            email=email or f"signup-{uuid4()}@example.com",
            source_tag=source_tag,
            ts=ts,
        )
    )


# ---------------------------------------------------------------------------
# 1. Happy path — balanced traffic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_balanced_traffic_happy_path(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=5)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    # 8 twitter, 8 google, 4 unknown across 20 views (4 per day).
    flat_sources: list[str | None] = (
        ["twitter"] * 8 + ["google"] * 8 + [None] * 4
    )
    live_date = live_at.astimezone(timezone.utc).date()
    for day_idx in range(5):
        day_ts = datetime.combine(
            live_date + timedelta(days=day_idx),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) + timedelta(hours=12)
        for i, source_tag in enumerate(flat_sources[day_idx * 4 : day_idx * 4 + 4]):
            await _add_page_view(
                db_session,
                experiment_id=experiment.id,
                ts=day_ts + timedelta(minutes=i),
                source_tag=source_tag,
                ip_address=f"10.0.0.{day_idx * 4 + i + 1}",
            )

    signup_sources = ["twitter", "twitter", "google", None]
    for i, tag in enumerate(signup_sources):
        signup_ts = datetime.combine(
            live_date + timedelta(days=i),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) + timedelta(hours=14)
        await _add_signup(
            db_session,
            experiment_id=experiment.id,
            ts=signup_ts,
            source_tag=tag,
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)

    assert result.total_page_views == 20
    assert result.total_signups == 4
    assert result.unique_visitors == 20
    assert result.conversion_rate == pytest.approx(0.2)
    assert result.views_by_source == {"twitter": 8, "google": 8, "unknown": 4}
    assert result.signups_by_source == {"twitter": 2, "google": 1, "unknown": 1}
    assert result.conversion_rate_by_source["twitter"] == pytest.approx(0.25)
    assert result.conversion_rate_by_source["google"] == pytest.approx(0.125)
    assert result.conversion_rate_by_source["unknown"] == pytest.approx(0.25)
    assert result.warm_network_bias_index == pytest.approx(0.4)
    assert len(result.views_by_day) == 5
    assert len(result.signups_by_day) == 5
    assert sum(result.views_by_day) == 20
    assert sum(result.signups_by_day) == 4


# ---------------------------------------------------------------------------
# 2. Zero data — landing page just published
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_data_just_published(db_session: AsyncSession) -> None:
    now = _utc_now()
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=now)

    result = await build_analytics_aggregate(db_session, experiment.id)

    assert result.days_live == 0
    assert result.conversion_rate == 0.0
    assert result.views_by_day == []
    assert result.signups_by_day == []
    assert result.total_page_views == 0
    assert result.total_signups == 0


# ---------------------------------------------------------------------------
# 3–4. Landing page guardrails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_landing_page_raises(db_session: AsyncSession) -> None:
    experiment = await _persist_experiment(db_session)

    with pytest.raises(LandingPageNotLiveError):
        await build_analytics_aggregate(db_session, experiment.id)


@pytest.mark.asyncio
async def test_landing_page_not_live_raises(db_session: AsyncSession) -> None:
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=None)

    with pytest.raises(LandingPageNotLiveError):
        await build_analytics_aggregate(db_session, experiment.id)


# ---------------------------------------------------------------------------
# 5–6. Warm-network bias index
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warm_network_bias_pure_warm(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=2)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(5):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(hours=i + 1),
            source_tag="twitter-followers",
            ip_address=f"10.1.0.{i}",
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert result.warm_network_bias_index == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_warm_network_bias_pure_cold(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=2)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(5):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(hours=i + 1),
            source_tag="google-ads",
            ip_address=f"10.2.0.{i}",
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert result.warm_network_bias_index == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 7. High-volume zero-conversion drop-off signal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_volume_zero_conversion_drop_off(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=3)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(60):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(minutes=i),
            source_tag="google",
            ip_address=f"10.3.0.{i % 20}",
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert "zero_conversion" in result.drop_off_signals


# ---------------------------------------------------------------------------
# 8–9. Data quality notes — IP and time_on_page fallbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_null_ips_fallback(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=1)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(10):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(minutes=i),
            source_tag="google",
            ip_address=None,
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert result.unique_visitors == 10
    assert any("IP address" in note for note in result.data_quality_notes)


@pytest.mark.asyncio
async def test_all_null_time_on_page(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=1)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(10):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(minutes=i),
            source_tag="google",
            ip_address=f"10.4.0.{i}",
            time_on_page_sec=None,
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert result.time_on_page_p50_seconds == 0
    assert result.time_on_page_p90_seconds == 0
    assert any("time_on_page" in note for note in result.data_quality_notes)


# ---------------------------------------------------------------------------
# 10. Source concentration warning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_concentration_warning(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=2)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(95):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(minutes=i),
            source_tag="twitter",
            ip_address=f"10.5.0.{i % 30}",
        )
    for i in range(5):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(hours=2, minutes=i),
            source_tag="google",
            ip_address=f"10.5.1.{i}",
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert any("Traffic concentrated" in note and "twitter" in note for note in result.data_quality_notes)


# ---------------------------------------------------------------------------
# 11. Day-array length matches days_live
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_day_arrays_match_days_live(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=7)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    for i in range(14):
        day_idx = i % 7
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(days=day_idx, minutes=i),
            source_tag="google",
            ip_address=f"10.6.{day_idx}.{i}",
        )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)
    assert result.days_live == 7
    assert len(result.views_by_day) == 7
    assert len(result.signups_by_day) == 7
    assert sum(result.views_by_day) == 14


# ---------------------------------------------------------------------------
# 12. Logging is hygienic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logging_is_hygienic(db_session: AsyncSession) -> None:
    now = _utc_now()
    live_at = now - timedelta(days=1)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    await _add_page_view(
        db_session,
        experiment_id=experiment.id,
        ts=live_at + timedelta(hours=1),
        source_tag="twitter",
        ip_address="192.168.1.99",
    )
    await _add_signup(
        db_session,
        experiment_id=experiment.id,
        ts=live_at + timedelta(hours=2),
        source_tag="twitter",
        email="founder-sensitive@example.com",
    )
    await db_session.commit()

    with structlog.testing.capture_logs() as cap:
        await build_analytics_aggregate(db_session, experiment.id)

    events = [e for e in cap if e.get("event") == "analytics aggregate built"]
    assert len(events) == 1
    log_entry = events[0]
    assert log_entry["experiment_id"] == str(experiment.id)
    assert log_entry["unique_source_count"] == 1
    assert "email" not in log_entry
    assert "ip_address" not in log_entry
    assert "source_tag" not in log_entry
    assert "twitter" not in str(log_entry)


# ---------------------------------------------------------------------------
# 13–14. Conversion rate denominator uses total page views (not unique visitors)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_analytics_aggregate_conversion_rate_uses_total_views_not_unique_visitors(
    db_session: AsyncSession,
) -> None:
    """Regression: CineFund case — 4 views from 1 IP + 1 signup → 25%, not 100%."""
    now = _utc_now()
    live_at = now - timedelta(days=1)
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=live_at)

    shared_ip = "203.0.113.42"
    for i in range(4):
        await _add_page_view(
            db_session,
            experiment_id=experiment.id,
            ts=live_at + timedelta(minutes=i),
            source_tag="twitter",
            ip_address=shared_ip,
        )
    await _add_signup(
        db_session,
        experiment_id=experiment.id,
        ts=live_at + timedelta(hours=1),
        source_tag="twitter",
    )
    await db_session.commit()

    result = await build_analytics_aggregate(db_session, experiment.id)

    assert result.total_page_views == 4
    assert result.unique_visitors == 1
    assert result.total_signups == 1
    assert result.conversion_rate == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_build_analytics_aggregate_conversion_rate_zero_views_no_division_error(
    db_session: AsyncSession,
) -> None:
    now = _utc_now()
    experiment = await _persist_experiment(db_session)
    await _persist_landing_page(db_session, experiment.id, live_at=now)

    result = await build_analytics_aggregate(db_session, experiment.id)

    assert result.total_page_views == 0
    assert result.total_signups == 0
    assert result.conversion_rate == 0.0
