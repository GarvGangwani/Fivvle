"""Router tests for GET /wallet/transactions."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.enums import WalletTransactionType
from app.dispatchers.dependencies import get_dispatcher_dep
from app.main import app
from app.pricing import SERVICE_PRICING
from tests.conftest import FAKE_FIREBASE_UID
from tests.routers.test_confirm_and_research_status import (
    FakeDispatcher,
    _create_refined_experiment,
    _sync_user,
)
from tests.routers.test_wallet_monetization import (
    _read_wallet_balance,
    _set_wallet_balance,
    monetization_enabled,
)

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def test_get_wallet_transactions_empty_for_new_user(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.get("/wallet/transactions", headers=_AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["transactions"] == []
    assert body["total"] == 0
    assert body["has_more"] is False
    assert body["credits_balance"] == 0


def test_get_wallet_transactions_includes_coupon_redemption(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    redeem = client.post(
        "/wallet/coupons/redeem",
        json={"code": "WELCOME5"},
        headers=_AUTH_HEADER,
    )
    assert redeem.status_code == 200

    resp = client.get("/wallet/transactions", headers=_AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    tx = body["transactions"][0]
    assert tx["type"] == WalletTransactionType.COUPON
    assert tx["credits"] == 25
    assert tx["title"] == "Coupon redeemed"
    assert tx["reference"] == "WELCOME5"
    assert tx["balance_after"] == 25


def test_get_wallet_transactions_includes_service_debit(
    client: TestClient,
    mock_firebase: None,
    monetization_enabled: None,
) -> None:
    cost = SERVICE_PRICING["fullValidationFlow"]
    _sync_user(client)
    _set_wallet_balance(FAKE_FIREBASE_UID, cost + 10)
    experiment_id = _create_refined_experiment(client)

    fd = FakeDispatcher()
    app.dependency_overrides[get_dispatcher_dep] = lambda: fd
    try:
        confirm = client.post(
            f"/experiments/{experiment_id}/confirm",
            headers=_AUTH_HEADER,
        )
        assert confirm.status_code == 202
    finally:
        app.dependency_overrides.pop(get_dispatcher_dep, None)

    resp = client.get("/wallet/transactions", headers=_AUTH_HEADER)
    body = resp.json()
    assert body["total"] >= 1
    usage = next(tx for tx in body["transactions"] if tx["type"] == "SERVICE_USAGE")
    assert usage["credits"] == -cost
    assert usage["title"] == "Full validation flow"
    assert usage["balance_after"] == 10
    assert _read_wallet_balance(FAKE_FIREBASE_UID) == 10


def test_get_wallet_transactions_pagination(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    client.post(
        "/wallet/coupons/redeem",
        json={"code": "WELCOME5"},
        headers=_AUTH_HEADER,
    )

    first = client.get("/wallet/transactions?limit=1&offset=0", headers=_AUTH_HEADER)
    assert first.status_code == 200
    page = first.json()
    assert len(page["transactions"]) == 1
    assert page["has_more"] is False
    assert page["total"] == 1

    empty = client.get("/wallet/transactions?limit=20&offset=5", headers=_AUTH_HEADER)
    assert empty.json()["transactions"] == []


def test_get_wallet_transactions_unauthenticated_returns_401(
    client: TestClient,
) -> None:
    resp = client.get("/wallet/transactions")
    assert resp.status_code == 401
