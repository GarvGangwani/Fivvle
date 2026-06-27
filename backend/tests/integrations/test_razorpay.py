"""Unit tests for Razorpay integration helpers."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from app.integrations.razorpay import (
    RazorpaySignatureError,
    convert_usd_cents_to_inr_paise,
    verify_payment_signature_sync,
)


def test_convert_usd_cents_to_inr_paise_starter_pack() -> None:
    # $5.00 at 83.0 INR/USD = 415.00 INR = 41500 paise
    assert convert_usd_cents_to_inr_paise(500, 83.0) == 41500


def test_convert_usd_cents_to_inr_paise_minimum_one_inr() -> None:
    assert convert_usd_cents_to_inr_paise(1, 1.0) == 100


def test_verify_payment_signature_accepts_valid_hmac(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test_secret")
    get_settings.cache_clear()

    order_id = "order_abc"
    payment_id = "pay_xyz"
    signature = hmac.new(
        b"test_secret",
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    verify_payment_signature_sync(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
    )


def test_verify_payment_signature_rejects_invalid_hmac(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test_secret")
    get_settings.cache_clear()

    with pytest.raises(RazorpaySignatureError):
        verify_payment_signature_sync(
            razorpay_order_id="order_abc",
            razorpay_payment_id="pay_xyz",
            razorpay_signature="not-valid",
        )
