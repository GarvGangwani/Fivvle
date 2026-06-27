"""Pydantic schemas for wallet / Razorpay credit-pack endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import WalletTransactionType


class CreditPackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    usd_cents: int
    usd_display: str
    base_credits: int
    bonus_credits: int
    total_credits: int


class WalletBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credits_balance: int
    usd_equivalent: str
    total_credits_purchased: int
    total_credits_consumed: int
    credit_conversion_rate: int
    has_redeemed_welcome_coupon: bool
    packs: list[CreditPackResponse]


class RedeemCouponRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)


class RedeemCouponResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    credits_added: int
    new_balance: int


class CreateCreditPackOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    pack_id: str = Field(alias="packId", min_length=1, max_length=32)


class CreateCreditPackOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_order_id: UUID
    pack_id: str
    pack_name: str
    usd_cents: int
    base_credits: int
    bonus_credits: int
    total_credits: int
    amount_inr_paise: int
    currency: str
    razorpay_key_id: str
    razorpay_order_id: str
    receipt: str


class VerifyPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    razorpay_payment_id: str = Field(alias="razorpayPaymentId", min_length=1, max_length=64)
    razorpay_order_id: str = Field(alias="razorpayOrderId", min_length=1, max_length=64)
    razorpay_signature: str = Field(alias="razorpaySignature", min_length=1, max_length=256)


class VerifyPaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_order_id: UUID
    credits_added: int
    bonus_credits: int
    new_balance: int
    already_processed: bool
    razorpay_payment_id: str
    razorpay_order_id: str


class WalletTransactionItem(BaseModel):
    """Single ledger row for GET /wallet/transactions."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    type: WalletTransactionType
    credits: int = Field(
        description="Signed credit delta: positive adds, negative debits."
    )
    title: str
    detail: str | None = None
    reference: str | None = Field(
        default=None,
        description="Order id, coupon code, or other user-facing reference.",
    )
    created_at: datetime
    balance_after: int = Field(ge=0)
    experiment_id: UUID | None = None
    experiment_name: str | None = None


class WalletTransactionsResponse(BaseModel):
    """Paginated wallet ledger for billing history in settings."""

    model_config = ConfigDict(extra="forbid")

    transactions: list[WalletTransactionItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
    credits_balance: int = Field(ge=0)
    total_credits_purchased: int = Field(ge=0)
    total_credits_consumed: int = Field(ge=0)
