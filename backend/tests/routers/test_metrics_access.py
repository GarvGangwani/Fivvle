"""Router tests for metrics access and free analytics (post metricsAnalysis gate removal)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.db.models.landing_page import LandingPage
from app.services.insight_threshold import (
    MIN_DAYS_LIVE,
    MIN_PAGE_VIEWS,
    MIN_SIGNUPS,
)
from tests.conftest import FAKE_FIREBASE_UID
from tests.routers.test_confirm_and_research_status import _sync_user
from tests.routers.test_landing_page_slug import landing_page_fixture  # noqa: F401
from tests.routers.test_wallet_monetization import (
    _read_wallet_balance,
    _set_wallet_balance,
    monetization_enabled,
)

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _set_live(experiment_id: str, *, days_ago: int = 0) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    live_at = datetime.now(UTC) - timedelta(days=days_ago)

    async def _run() -> None:
        async with sm() as session:
            await session.execute(
                update(LandingPage)
                .where(LandingPage.experiment_id == UUID(experiment_id))
                .values(live_at=live_at)
            )
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.LANDING_LIVE)
            )
            await session.commit()
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _set_status(experiment_id: str, status: ExperimentStatus) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _run() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=status)
            )
            await session.commit()
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _add_page_views(experiment_id: str, count: int) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.page_view import PageView  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    now = datetime.now(UTC)

    async def _run() -> None:
        async with sm() as session:
            for i in range(count):
                session.add(
                    PageView(
                        experiment_id=UUID(experiment_id),
                        source_tag="twitter",
                        ts=now,
                        ip_address=f"10.0.0.{i % 250}",
                        time_on_page_sec=30,
                    )
                )
            await session.commit()
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _add_signups(experiment_id: str, count: int) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.waitlist_signup import WaitlistSignup  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    now = datetime.now(UTC)

    async def _run() -> None:
        async with sm() as session:
            for i in range(count):
                session.add(
                    WaitlistSignup(
                        experiment_id=UUID(experiment_id),
                        email=f"founder{i}@example.com",
                        source_tag="twitter",
                        ts=now,
                    )
                )
            await session.commit()
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def test_analytics_available_without_purchase(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)
    _add_page_views(experiment_id, 12)

    resp = client.get(f"/experiments/{experiment_id}/analytics", headers=_AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_page_views"] == 12
    assert body["insight_threshold_met"] is True
    assert body["insight_progress"]["views_current"] == 12
    assert body["insight_progress"]["views_target"] == MIN_PAGE_VIEWS


def test_analytics_rejects_archived(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)
    _set_status(experiment_id, ExperimentStatus.ARCHIVED)

    resp = client.get(f"/experiments/{experiment_id}/analytics", headers=_AUTH_HEADER)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Archived projects cannot access metrics."


def test_analytics_rejects_not_yet_live(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    # Fixture leaves LANDING_DRAFT / no live_at
    resp = client.get(f"/experiments/{experiment_id}/analytics", headers=_AUTH_HEADER)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Metrics are available after your landing page is live."


def test_unlock_metrics_is_noop_no_debit(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    starting_balance = 100
    _set_wallet_balance(FAKE_FIREBASE_UID, starting_balance)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)

    unlock = client.post(
        f"/experiments/{experiment_id}/unlock-metrics",
        headers=_AUTH_HEADER,
    )
    assert unlock.status_code == 200
    body = unlock.json()
    assert body["unlocked"] is True
    assert body["already_unlocked"] is True
    assert body["credits_balance"] == starting_balance

    unlock_again = client.post(
        f"/experiments/{experiment_id}/unlock-metrics",
        headers=_AUTH_HEADER,
    )
    assert unlock_again.json()["unlocked"] is True
    assert unlock_again.json()["already_unlocked"] is True
    assert _read_wallet_balance(FAKE_FIREBASE_UID) == starting_balance


def test_metrics_access_unlocked_when_live(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)

    access = client.get(
        f"/experiments/{experiment_id}/metrics-access",
        headers=_AUTH_HEADER,
    )
    assert access.status_code == 200
    assert access.json()["unlocked"] is True


def test_analytics_threshold_zero_data(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)

    body = client.get(
        f"/experiments/{experiment_id}/analytics",
        headers=_AUTH_HEADER,
    ).json()
    assert body["insight_threshold_met"] is False
    progress = body["insight_progress"]
    assert progress["views_current"] == 0
    assert progress["views_target"] == MIN_PAGE_VIEWS
    assert progress["signups_current"] == 0
    assert progress["signups_target"] == MIN_SIGNUPS
    assert progress["days_current"] == 0
    assert progress["days_target"] == MIN_DAYS_LIVE


def test_analytics_threshold_views_only_met(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)
    _add_page_views(experiment_id, MIN_PAGE_VIEWS)

    body = client.get(
        f"/experiments/{experiment_id}/analytics",
        headers=_AUTH_HEADER,
    ).json()
    assert body["insight_threshold_met"] is True
    assert body["insight_progress"]["views_current"] == MIN_PAGE_VIEWS


def test_analytics_threshold_signups_only_met(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)
    # Aggregator requires signup source tags ⊆ view source tags.
    _add_page_views(experiment_id, 1)
    _add_signups(experiment_id, MIN_SIGNUPS)

    body = client.get(
        f"/experiments/{experiment_id}/analytics",
        headers=_AUTH_HEADER,
    ).json()
    assert body["insight_threshold_met"] is True
    assert body["insight_progress"]["signups_current"] == MIN_SIGNUPS
    assert body["insight_progress"]["views_current"] == 1
    assert body["insight_progress"]["views_current"] < MIN_PAGE_VIEWS


def test_analytics_threshold_days_only_met(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id, days_ago=MIN_DAYS_LIVE)

    body = client.get(
        f"/experiments/{experiment_id}/analytics",
        headers=_AUTH_HEADER,
    ).json()
    assert body["insight_threshold_met"] is True
    assert body["insight_progress"]["days_current"] >= MIN_DAYS_LIVE
    assert body["insight_progress"]["views_current"] == 0
