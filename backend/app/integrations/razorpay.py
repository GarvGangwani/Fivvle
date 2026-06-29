"""Razorpay integration — order creation and payment signature verification.

All Razorpay HTTP calls live here per `.cursorrules` integration pattern.
Never call Razorpay directly from routers or services.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

_logger = get_logger(__name__)

RAZORPAY_PROVIDER = "razorpay"
RAZORPAY_CURRENCY = "INR"
_RAZORPAY_API_BASE = "https://api.razorpay.com/v1"
_TIMEOUT_SECONDS = 30


class RazorpayNotConfiguredError(RuntimeError):
    """Raised when Razorpay credentials are missing."""


class RazorpayApiError(RuntimeError):
    """Raised when Razorpay returns a non-success HTTP response."""


class RazorpaySignatureError(Exception):
    """Raised when payment signature verification fails."""


@dataclass(frozen=True, slots=True)
class RazorpayOrderResult:
    order_id: str
    amount_paise: int
    currency: str
    receipt: str


def _require_credentials(settings: Settings) -> tuple[str, str]:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RazorpayNotConfiguredError("Razorpay credentials are not configured")
    return settings.razorpay_key_id, settings.razorpay_key_secret


def reset_client_for_tests() -> None:
    """No-op — kept for test fixtures that clear integration state."""


def convert_usd_cents_to_inr_paise(usd_cents: int, usd_inr_rate: float) -> int:
    """Convert pack USD cents to INR paise for Razorpay settlement."""
    usd = Decimal(usd_cents) / Decimal(100)
    inr = usd * Decimal(str(usd_inr_rate))
    paise = int((inr * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(paise, 100)


async def _post_json(
    path: str,
    payload: dict[str, Any],
    *,
    settings: Settings,
) -> dict[str, Any]:
    key_id, key_secret = _require_credentials(settings)
    url = f"{_RAZORPAY_API_BASE}{path}"
    breaker = get_breaker("razorpay")

    async def _call() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json=payload,
                auth=(key_id, key_secret),
            )
        if response.status_code >= 400:
            _logger.warning(
                "razorpay api error",
                status_code=response.status_code,
                path=path,
            )
            raise RazorpayApiError("Razorpay order creation failed")
        data = response.json()
        if not isinstance(data, dict):
            raise RazorpayApiError("Unexpected Razorpay response shape")
        return data

    @retry_async()
    async def _call_with_retry() -> dict[str, Any]:
        return await breaker.call(_call)

    return await _call_with_retry()


async def create_order(
    *,
    amount_paise: int,
    receipt: str,
    settings: Settings | None = None,
) -> RazorpayOrderResult:
    settings = settings or get_settings()
    payload: dict[str, Any] = {
        "amount": amount_paise,
        "currency": RAZORPAY_CURRENCY,
        "receipt": receipt,
        "payment_capture": 1,
    }
    response = await _post_json("/orders", payload, settings=settings)
    return RazorpayOrderResult(
        order_id=str(response["id"]),
        amount_paise=int(response["amount"]),
        currency=str(response["currency"]),
        receipt=str(response["receipt"]),
    )


def verify_payment_signature_sync(
    *,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    _, key_secret = _require_credentials(settings)
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        key_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, razorpay_signature):
        _logger.warning(
            "razorpay signature verification failed",
            razorpay_order_id=razorpay_order_id,
        )
        raise RazorpaySignatureError("Invalid payment signature")


async def verify_payment_signature(
    *,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    settings: Settings | None = None,
) -> None:
    verify_payment_signature_sync(
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        settings=settings,
    )
