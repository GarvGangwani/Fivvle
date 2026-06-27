"""Router tests for metrics unlock and analytics gating."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.pricing import SERVICE_PRICING
from tests.conftest import FAKE_FIREBASE_UID
from tests.routers.test_confirm_and_research_status import _sync_user
from tests.routers.test_landing_page_slug import landing_page_fixture  # noqa: F401
from tests.routers.test_wallet_monetization import (
    _read_wallet_balance,
    _set_wallet_balance,
    monetization_enabled,
)

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _set_live(experiment_id: str) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    now = datetime.now(UTC)

    async def _run() -> None:
        async with sm() as session:
            await session.execute(
                update(LandingPage)
                .where(LandingPage.experiment_id == UUID(experiment_id))
                .values(live_at=now)
            )
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.LANDING_LIVE)
            )
            await session.commit()
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _add_page_views(experiment_id: str, count: int) -> None:
    from uuid import uuid4  # noqa: PLC0415

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


def test_analytics_requires_unlock(
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
    assert resp.status_code == 402
    assert resp.json()["detail"]["error"] == "metrics_not_unlocked"


def test_unlock_metrics_debits_once(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
    monetization_enabled: None,
) -> None:
    cost = SERVICE_PRICING["metricsAnalysis"]
    _sync_user(client)
    _set_wallet_balance(FAKE_FIREBASE_UID, cost + 50)
    experiment_id, _slug = landing_page_fixture
    _set_live(experiment_id)
    _add_page_views(experiment_id, 12)

    unlock = client.post(
        f"/experiments/{experiment_id}/unlock-metrics",
        headers=_AUTH_HEADER,
    )
    assert unlock.status_code == 200
    body = unlock.json()
    assert body["unlocked"] is True
    assert body["already_unlocked"] is False
    assert body["credits_balance"] == 50

    access = client.get(
        f"/experiments/{experiment_id}/metrics-access",
        headers=_AUTH_HEADER,
    )
    assert access.json()["unlocked"] is True

    analytics = client.get(
        f"/experiments/{experiment_id}/analytics",
        headers=_AUTH_HEADER,
    )
    assert analytics.status_code == 200

    unlock_again = client.post(
        f"/experiments/{experiment_id}/unlock-metrics",
        headers=_AUTH_HEADER,
    )
    assert unlock_again.json()["already_unlocked"] is True
    assert _read_wallet_balance(FAKE_FIREBASE_UID) == 50
