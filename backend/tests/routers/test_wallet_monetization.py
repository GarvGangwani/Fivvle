"""Router tests for credit debits when monetization is enabled (Phase 10)."""

from __future__ import annotations

import asyncio
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.dispatchers.dependencies import get_dispatcher_dep, get_insight_dispatcher_dep
from app.dispatchers.protocol import DispatchError
from app.main import app
from app.pricing import SERVICE_PRICING
from tests.conftest import FAKE_FIREBASE_UID
from tests.routers.test_confirm_and_research_status import (
    FakeDispatcher,
    _create_refined_experiment,
    _sync_user,
)
from tests.routers.test_generate_insight_endpoint import (
    FakeInsightDispatcher,
    _post_generate_insight,
    _seed_insight_fixture,
)

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


@pytest.fixture
def monetization_enabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("MONETIZATION_ENABLED", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("MONETIZATION_ENABLED", raising=False)
    get_settings.cache_clear()


def _set_wallet_balance(firebase_uid: str, balance: int) -> None:
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                user = (
                    await session.execute(
                        select(User).where(User.firebase_uid == firebase_uid)
                    )
                ).scalar_one()
                wallet = (
                    await session.execute(select(Wallet).where(Wallet.user_id == user.id))
                ).scalar_one()
                wallet.credits_balance = balance
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _read_wallet_balance(firebase_uid: str) -> int:
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    result: dict[str, int] = {}

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                user = (
                    await session.execute(
                        select(User).where(User.firebase_uid == firebase_uid)
                    )
                ).scalar_one()
                wallet = (
                    await session.execute(select(Wallet).where(Wallet.user_id == user.id))
                ).scalar_one()
                result["balance"] = wallet.credits_balance
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())
    return result["balance"]


def test_confirm_returns_402_when_insufficient_credits(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)

    resp = client.post(f"/experiments/{experiment_id}/confirm", headers=_AUTH_HEADER)

    assert resp.status_code == 402
    body = resp.json()["detail"]
    assert body["error"] == "insufficient_credits"
    assert body["available"] == 0
    assert body["required"] == SERVICE_PRICING["fullValidationFlow"]


def test_confirm_debits_and_refunds_on_dispatch_failure(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    cost = SERVICE_PRICING["fullValidationFlow"]
    _sync_user(client)
    _set_wallet_balance(FAKE_FIREBASE_UID, cost)
    experiment_id = _create_refined_experiment(client)

    class FailingDispatcher:
        async def dispatch(self, experiment_id: object) -> None:
            raise DispatchError("simulated failure")

    app.dependency_overrides[get_dispatcher_dep] = lambda: FailingDispatcher()
    try:
        resp = client.post(f"/experiments/{experiment_id}/confirm", headers=_AUTH_HEADER)
        assert resp.status_code == 502
        assert _read_wallet_balance(FAKE_FIREBASE_UID) == cost
    finally:
        app.dependency_overrides.pop(get_dispatcher_dep, None)


def test_confirm_succeeds_when_balance_sufficient(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    cost = SERVICE_PRICING["fullValidationFlow"]
    _sync_user(client)
    _set_wallet_balance(FAKE_FIREBASE_UID, cost)
    experiment_id = _create_refined_experiment(client)

    fd = FakeDispatcher()
    app.dependency_overrides[get_dispatcher_dep] = lambda: fd
    try:
        resp = client.post(f"/experiments/{experiment_id}/confirm", headers=_AUTH_HEADER)
        assert resp.status_code == 202
        assert resp.json()["credits_balance"] == 0
        assert _read_wallet_balance(FAKE_FIREBASE_UID) == 0
        assert fd.dispatched == [experiment_id]
    finally:
        app.dependency_overrides.pop(get_dispatcher_dep, None)


def test_generate_insight_returns_402_when_insufficient_credits(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=15,
        days_live=3,
    )

    resp = _post_generate_insight(client, experiment_id)

    assert resp.status_code == 402
    body = resp.json()["detail"]
    assert body["required"] == SERVICE_PRICING["insightReport"]


def test_generate_insight_refunds_on_dispatch_failure(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    cost = SERVICE_PRICING["insightReport"]
    _sync_user(client)
    _set_wallet_balance(FAKE_FIREBASE_UID, cost)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=15,
        days_live=3,
    )

    class FailingInsightDispatcher:
        async def dispatch(self, experiment_id: object) -> None:
            raise DispatchError("simulated failure")

    app.dependency_overrides[get_insight_dispatcher_dep] = lambda: FailingInsightDispatcher()
    try:
        resp = _post_generate_insight(client, experiment_id)
        assert resp.status_code == 502
        assert _read_wallet_balance(FAKE_FIREBASE_UID) == cost
    finally:
        app.dependency_overrides.pop(get_insight_dispatcher_dep, None)


def test_generate_insight_second_call_while_generating_does_not_debit_again(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    cost = SERVICE_PRICING["insightReport"]
    _sync_user(client)
    _set_wallet_balance(FAKE_FIREBASE_UID, cost + 50)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.INSIGHT_READY,
        page_view_count=15,
        days_live=3,
        with_insight_report=True,
    )

    fd = FakeInsightDispatcher()
    app.dependency_overrides[get_insight_dispatcher_dep] = lambda: fd
    try:
        first = _post_generate_insight(client, experiment_id)
        second = _post_generate_insight(client, experiment_id)
        assert first.status_code == 202
        assert second.status_code == 202
        assert second.json()["status"] == "INSIGHT_GENERATING"
        assert _read_wallet_balance(FAKE_FIREBASE_UID) == 50
    finally:
        app.dependency_overrides.pop(get_insight_dispatcher_dep, None)
