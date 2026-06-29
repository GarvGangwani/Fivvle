"""Razorpay credit-pack order creation and payment fulfillment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.enums import PaymentOrderStatus
from app.db.models.payment_order import PaymentOrder
from app.db.models.processed_webhook import ProcessedWebhook
from app.db.models.wallet import Wallet
from app.integrations.razorpay import (
    RAZORPAY_CURRENCY,
    RAZORPAY_PROVIDER,
    RazorpayNotConfiguredError,
    RazorpaySignatureError,
    convert_usd_cents_to_inr_paise,
    create_order,
    verify_payment_signature,
)
from app.pricing import CreditPack, get_pack
from app.services.wallet_service import credit_topup, get_or_create_wallet


class PaymentError(Exception):
    """Base payment error."""


class PaymentOrderNotFound(PaymentError):
    """No payment order for the given Razorpay order id."""


class PaymentOrderConflict(PaymentError):
    """Order already fulfilled with a different payment id."""


class DuplicatePayment(PaymentError):
    """Payment id was already processed for another order."""


@dataclass(frozen=True, slots=True)
class CreatedPaymentOrder:
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


@dataclass(frozen=True, slots=True)
class FulfilledPayment:
    payment_order_id: UUID
    credits_added: int
    bonus_credits: int
    new_balance: int
    already_processed: bool
    razorpay_payment_id: str
    razorpay_order_id: str


async def create_credit_pack_order(
    db: AsyncSession,
    *,
    user_id: UUID,
    pack_id: str,
) -> CreatedPaymentOrder:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise RazorpayNotConfiguredError("Razorpay credentials are not configured")

    pack = get_pack(pack_id)
    await get_or_create_wallet(db, user_id)

    payment_order_id = uuid4()
    receipt = payment_order_id.hex
    amount_inr_paise = convert_usd_cents_to_inr_paise(
        pack.usd_cents,
        settings.usd_inr_rate,
    )

    razorpay_order = await create_order(
        amount_paise=amount_inr_paise,
        receipt=receipt,
        settings=settings,
    )

    order_row = PaymentOrder(
        id=payment_order_id,
        user_id=user_id,
        pack_id=pack.id,
        usd_cents=pack.usd_cents,
        credits_base=pack.base_credits,
        credits_bonus=pack.bonus_credits,
        amount_inr_paise=razorpay_order.amount_paise,
        razorpay_order_id=razorpay_order.order_id,
        status=PaymentOrderStatus.CREATED,
    )
    db.add(order_row)
    await db.flush()

    return CreatedPaymentOrder(
        payment_order_id=order_row.id,
        pack_id=pack.id,
        pack_name=pack.name,
        usd_cents=pack.usd_cents,
        base_credits=pack.base_credits,
        bonus_credits=pack.bonus_credits,
        total_credits=pack.total_credits,
        amount_inr_paise=razorpay_order.amount_paise,
        currency=RAZORPAY_CURRENCY,
        razorpay_key_id=settings.razorpay_key_id,
        razorpay_order_id=razorpay_order.order_id,
        receipt=receipt,
    )


async def _get_order_for_update(
    db: AsyncSession,
    *,
    razorpay_order_id: str,
) -> PaymentOrder:
    stmt = (
        select(PaymentOrder)
        .where(PaymentOrder.razorpay_order_id == razorpay_order_id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise PaymentOrderNotFound("Payment order not found")
    return order


async def _payment_id_already_processed(
    db: AsyncSession,
    *,
    razorpay_payment_id: str,
) -> PaymentOrder | None:
    stmt = select(PaymentOrder).where(
        PaymentOrder.razorpay_payment_id == razorpay_payment_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _wallet_balance(db: AsyncSession, user_id: UUID) -> int:
    stmt = select(Wallet.credits_balance).where(Wallet.user_id == user_id)
    result = await db.execute(stmt)
    balance = result.scalar_one_or_none()
    return balance if balance is not None else 0


async def verify_and_fulfill_payment(
    db: AsyncSession,
    *,
    user_id: UUID,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
) -> FulfilledPayment:
    order = await _get_order_for_update(db, razorpay_order_id=razorpay_order_id)

    if order.user_id != user_id:
        raise PaymentOrderNotFound("Payment order not found")

    if order.status == PaymentOrderStatus.PAID:
        if order.razorpay_payment_id == razorpay_payment_id:
            return FulfilledPayment(
                payment_order_id=order.id,
                credits_added=order.credits_base,
                bonus_credits=order.credits_bonus,
                new_balance=await _wallet_balance(db, user_id),
                already_processed=True,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
            )
        raise PaymentOrderConflict("Payment order already fulfilled")

    existing = await _payment_id_already_processed(
        db,
        razorpay_payment_id=razorpay_payment_id,
    )
    if existing is not None:
        if existing.id == order.id:
            return FulfilledPayment(
                payment_order_id=order.id,
                credits_added=order.credits_base,
                bonus_credits=order.credits_bonus,
                new_balance=await _wallet_balance(db, user_id),
                already_processed=True,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
            )
        raise DuplicatePayment("Payment already processed")

    webhook_stmt = select(ProcessedWebhook).where(
        ProcessedWebhook.provider == RAZORPAY_PROVIDER,
        ProcessedWebhook.event_id == razorpay_payment_id,
    )
    if (await db.execute(webhook_stmt)).scalar_one_or_none() is not None:
        return FulfilledPayment(
            payment_order_id=order.id,
            credits_added=order.credits_base,
            bonus_credits=order.credits_bonus,
            new_balance=await _wallet_balance(db, user_id),
            already_processed=True,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
        )

    await verify_payment_signature(
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
    )

    pack = get_pack(order.pack_id)
    description = f"{pack.name} credit pack"

    db.add(
        ProcessedWebhook(
            provider=RAZORPAY_PROVIDER,
            event_id=razorpay_payment_id,
        )
    )

    await credit_topup(
        db,
        user_id=user_id,
        base_credits=order.credits_base,
        bonus_credits=order.credits_bonus,
        description=description,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id,
    )

    order.status = PaymentOrderStatus.PAID
    order.razorpay_payment_id = razorpay_payment_id
    order.paid_at = datetime.now(timezone.utc)

    await db.flush()

    return FulfilledPayment(
        payment_order_id=order.id,
        credits_added=order.credits_base,
        bonus_credits=order.credits_bonus,
        new_balance=await _wallet_balance(db, user_id),
        already_processed=False,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id,
    )


def pack_summary(pack: CreditPack) -> dict[str, int | str]:
    return {
        "pack_id": pack.id,
        "name": pack.name,
        "usd_cents": pack.usd_cents,
        "base_credits": pack.base_credits,
        "bonus_credits": pack.bonus_credits,
        "total_credits": pack.total_credits,
    }
