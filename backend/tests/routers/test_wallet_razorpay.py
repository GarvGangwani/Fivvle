"""Router tests for wallet Razorpay endpoints (Phase 11)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.integrations.razorpay import RazorpayOrderResult, reset_client_for_tests
from app.services.payment_service import CreatedPaymentOrder

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
    resp = client.post("/users/sync", json={"name": "Wallet Buyer"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def test_create_order_unknown_pack_returns_400(
    client: TestClient,
    mock_firebase: None,
    razorpay_credentials: None,
) -> None:
    _sync_user(client)
    resp = client.post(
        "/wallet/orders",
        json={"packId": "not-a-pack"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unknown credit pack"


def test_create_order_returns_server_pricing(
    client: TestClient,
    mock_firebase: None,
    razorpay_credentials: None,
) -> None:
    _sync_user(client)
    fake = CreatedPaymentOrder(
        payment_order_id=UUID("00000000-0000-4000-8000-000000000001"),
        pack_id="starter",
        pack_name="Starter",
        usd_cents=500,
        base_credits=25,
        bonus_credits=0,
        total_credits=25,
        amount_inr_paise=41500,
        currency="INR",
        razorpay_key_id="rzp_test_key_id",
        razorpay_order_id="order_router_1",
        receipt="receipt1",
    )

    with patch(
        "app.routers.wallet.create_credit_pack_order",
        AsyncMock(return_value=fake),
    ):
        resp = client.post(
            "/wallet/orders",
            json={"packId": "starter"},
            headers=_AUTH_HEADER,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["pack_id"] == "starter"
    assert body["base_credits"] == 25
    assert body["razorpay_key_id"] == "rzp_test_key_id"
    assert body["razorpay_order_id"] == "order_router_1"
    assert "razorpay_key_secret" not in body


def test_create_order_without_credentials_returns_503(
    client: TestClient,
    mock_firebase: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAZORPAY_KEY_ID", "")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "")
    get_settings.cache_clear()
    reset_client_for_tests()

    _sync_user(client)
    resp = client.post(
        "/wallet/orders",
        json={"packId": "starter"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 503


def test_verify_payment_invalid_signature_returns_400(
    client: TestClient,
    mock_firebase: None,
    razorpay_credentials: None,
) -> None:
    from app.integrations.razorpay import RazorpaySignatureError

    _sync_user(client)

    with patch(
        "app.routers.wallet.verify_and_fulfill_payment",
        AsyncMock(side_effect=RazorpaySignatureError("bad sig")),
    ):
        resp = client.post(
            "/wallet/payments/verify",
            json={
                "razorpayPaymentId": "pay_bad",
                "razorpayOrderId": "order_bad",
                "razorpaySignature": "invalid",
            },
            headers=_AUTH_HEADER,
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid payment signature"


def test_verify_payment_happy_path(
    client: TestClient,
    mock_firebase: None,
    razorpay_credentials: None,
) -> None:
    from app.services.payment_service import FulfilledPayment

    _sync_user(client)
    fulfilled = FulfilledPayment(
        payment_order_id=UUID("00000000-0000-4000-8000-000000000002"),
        credits_added=25,
        bonus_credits=0,
        new_balance=25,
        already_processed=False,
        razorpay_payment_id="pay_ok",
        razorpay_order_id="order_ok",
    )

    with patch(
        "app.routers.wallet.verify_and_fulfill_payment",
        AsyncMock(return_value=fulfilled),
    ):
        resp = client.post(
            "/wallet/payments/verify",
            json={
                "razorpayPaymentId": "pay_ok",
                "razorpayOrderId": "order_ok",
                "razorpaySignature": "valid-sig",
            },
            headers=_AUTH_HEADER,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["credits_added"] == 25
    assert body["new_balance"] == 25
    assert body["already_processed"] is False


def test_create_order_integration_mocked_razorpay(
    client: TestClient,
    mock_firebase: None,
    razorpay_credentials: None,
) -> None:
    _sync_user(client)
    fake_order = RazorpayOrderResult(
        order_id="order_integration_1",
        amount_paise=41500,
        currency="INR",
        receipt="rcpt",
    )

    with patch(
        "app.services.payment_service.create_order",
        AsyncMock(return_value=fake_order),
    ):
        resp = client.post(
            "/wallet/orders",
            json={"packId": "founder"},
            headers=_AUTH_HEADER,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["pack_id"] == "founder"
    assert body["base_credits"] == 125
    assert body["bonus_credits"] == 20
    assert body["total_credits"] == 145
