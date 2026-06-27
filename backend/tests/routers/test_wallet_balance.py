"""Router tests for GET /wallet and coupon redemption (Phase 12)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.integrations.razorpay import reset_client_for_tests

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


@pytest.fixture
def razorpay_credentials(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_key_id")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "rzp_test_key_secret")
    get_settings.cache_clear()
    reset_client_for_tests()
    yield
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    get_settings.cache_clear()
    reset_client_for_tests()


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Wallet User"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def test_get_wallet_returns_balance_and_packs(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.get("/wallet", headers=_AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert "credits_balance" in body
    assert body["credit_conversion_rate"] == 5
    assert len(body["packs"]) == 5
    assert body["packs"][0]["id"] == "starter"
    assert body["packs"][0]["total_credits"] == 25


def test_redeem_coupon_credits_wallet(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.post(
        "/wallet/coupons/redeem",
        json={"code": "WELCOME5"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["credits_added"] == 25
    assert body["new_balance"] >= 25

    wallet = client.get("/wallet", headers=_AUTH_HEADER).json()
    assert wallet["has_redeemed_welcome_coupon"] is True


def test_redeem_coupon_twice_returns_409(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    first = client.post(
        "/wallet/coupons/redeem",
        json={"code": "WELCOME5"},
        headers=_AUTH_HEADER,
    )
    assert first.status_code == 200

    second = client.post(
        "/wallet/coupons/redeem",
        json={"code": "WELCOME5"},
        headers=_AUTH_HEADER,
    )
    assert second.status_code == 409


def test_redeem_invalid_coupon_returns_400(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.post(
        "/wallet/coupons/redeem",
        json={"code": "NOTREAL"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 400
