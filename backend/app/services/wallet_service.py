"""Wallet business logic — balance, debit, credit, coupon redemption."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.coupon_redemption import CouponRedemption
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.db.models.wallet_transaction import WalletTransaction, WalletTransactionType
from app.pricing import (
    CREDIT_CONVERSION_RATE,
    CREDIT_PACKS,
    SERVICE_LABELS,
    SERVICE_PRICING,
    WELCOME_COUPON_CODE,
    ServiceKey,
    credits_to_usd,
)
from app.schemas.wallet import (
    CreditPackResponse,
    RedeemCouponResponse,
    WalletBalanceResponse,
    WalletTransactionItem,
    WalletTransactionsResponse,
)
from app.services.coupon_service import (
    DEFAULT_DISABLED_MESSAGE,
    DEFAULT_EXPIRED_MESSAGE,
    DEFAULT_INVALID_MESSAGE,
    DEFAULT_LIMIT_REACHED_MESSAGE,
    DEFAULT_NOT_YET_ACTIVE_MESSAGE,
    count_coupon_redemptions,
    get_coupon_for_update,
    is_welcome_coupon_code,
    user_has_redeemed_coupon,
)


class WalletError(Exception):
    """Base wallet error."""


class InsufficientCredits(WalletError):
    """Raised when balance is too low for a debit."""

    def __init__(self, *, available: int, required: int) -> None:
        self.available = available
        self.required = required
        super().__init__(f"Insufficient credits: have {available}, need {required}")


class CouponAlreadyRedeemed(WalletError):
    """User already redeemed this coupon."""

    def __init__(self, message: str = "You have already redeemed this coupon.") -> None:
        self.message = message
        super().__init__(message)


class InvalidCoupon(WalletError):
    """Unknown coupon code."""

    def __init__(self, message: str | None = None) -> None:
        self.message = message or DEFAULT_INVALID_MESSAGE
        super().__init__(self.message)


class CouponRedemptionBlocked(WalletError):
    """Coupon exists but cannot be redeemed right now."""

    def __init__(self, *, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


async def get_or_create_wallet(db: AsyncSession, user_id: UUID) -> Wallet:
    stmt = select(Wallet).where(Wallet.user_id == user_id)
    result = await db.execute(stmt)
    wallet = result.scalar_one_or_none()
    if wallet is not None:
        return wallet

    wallet = Wallet(user_id=user_id)
    db.add(wallet)
    await db.flush()
    return wallet


async def get_wallet_for_update(db: AsyncSession, user_id: UUID) -> Wallet:
    stmt = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    result = await db.execute(stmt)
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(user_id=user_id)
        db.add(wallet)
        await db.flush()
        stmt = select(Wallet).where(Wallet.id == wallet.id).with_for_update()
        result = await db.execute(stmt)
        wallet = result.scalar_one()
    return wallet


async def _record_transaction(
    db: AsyncSession,
    *,
    wallet: Wallet,
    user_id: UUID,
    tx_type: WalletTransactionType,
    credits: int,
    description: str,
    experiment_id: UUID | None = None,
    razorpay_payment_id: str | None = None,
    razorpay_order_id: str | None = None,
) -> WalletTransaction:
    tx = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user_id,
        type=tx_type,
        credits=credits,
        description=description,
        experiment_id=experiment_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id,
    )
    db.add(tx)
    return tx


async def debit_credits(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    description: str,
    experiment_id: UUID | None = None,
) -> WalletTransaction:
    if amount <= 0:
        raise ValueError("debit amount must be positive")

    wallet = await get_wallet_for_update(db, user_id)
    if wallet.credits_balance < amount:
        raise InsufficientCredits(
            available=wallet.credits_balance,
            required=amount,
        )

    wallet.credits_balance -= amount
    wallet.total_credits_consumed += amount
    return await _record_transaction(
        db,
        wallet=wallet,
        user_id=user_id,
        tx_type=WalletTransactionType.SERVICE_USAGE,
        credits=-amount,
        description=description,
        experiment_id=experiment_id,
    )


async def require_and_debit_service(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    experiment_id: UUID | None = None,
) -> WalletTransaction | None:
    """Debit credits for a priced service. No-op when monetization is disabled."""
    if not get_settings().monetization_enabled:
        return None

    amount = SERVICE_PRICING[service]
    description = _service_usage_description(service, experiment_id)

    return await debit_credits(
        db,
        user_id=user_id,
        amount=amount,
        description=description,
        experiment_id=experiment_id,
    )


def _service_usage_description(service: ServiceKey, experiment_id: UUID | None) -> str:
    label = SERVICE_LABELS[service]
    if experiment_id is None:
        return label
    return f"{label} (experiment {experiment_id})"


async def has_purchased_service_for_experiment(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    experiment_id: UUID,
) -> bool:
    """True when this experiment already has a service debit for ``service``."""
    description = _service_usage_description(service, experiment_id)
    stmt = (
        select(WalletTransaction.id)
        .where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.experiment_id == experiment_id,
            WalletTransaction.type == WalletTransactionType.SERVICE_USAGE,
            WalletTransaction.description == description,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_experiments_with_purchased_service(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    experiment_ids: list[UUID],
) -> set[UUID]:
    """Batch check which experiments already purchased ``service``."""
    if not experiment_ids:
        return set()

    label = SERVICE_LABELS[service]
    stmt = (
        select(WalletTransaction.experiment_id)
        .where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.experiment_id.in_(experiment_ids),
            WalletTransaction.type == WalletTransactionType.SERVICE_USAGE,
            WalletTransaction.description.like(f"{label} (experiment %"),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all() if row[0] is not None}


async def purchase_service_for_experiment(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    experiment_id: UUID,
) -> tuple[WalletTransaction | None, bool]:
    """Debit once per experiment+service. Returns (transaction, already_purchased)."""
    if await has_purchased_service_for_experiment(
        db,
        user_id=user_id,
        service=service,
        experiment_id=experiment_id,
    ):
        return None, True

    if not get_settings().monetization_enabled:
        wallet = await get_or_create_wallet(db, user_id)
        tx = await _record_transaction(
            db,
            wallet=wallet,
            user_id=user_id,
            tx_type=WalletTransactionType.SERVICE_USAGE,
            credits=0,
            description=_service_usage_description(service, experiment_id),
            experiment_id=experiment_id,
        )
        return tx, False

    tx = await require_and_debit_service(
        db,
        user_id=user_id,
        service=service,
        experiment_id=experiment_id,
    )
    return tx, False


async def refund_service(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    reason: str,
    experiment_id: UUID | None = None,
) -> WalletTransaction | None:
    """Refund a prior service debit. No-op when monetization is disabled."""
    if not get_settings().monetization_enabled:
        return None

    amount = SERVICE_PRICING[service]
    label = SERVICE_LABELS[service]
    description = f"Refund: {label} — {reason}"
    return await refund_credits(
        db,
        user_id=user_id,
        amount=amount,
        description=description,
        experiment_id=experiment_id,
    )


async def credit_topup(
    db: AsyncSession,
    *,
    user_id: UUID,
    base_credits: int,
    bonus_credits: int,
    description: str,
    razorpay_payment_id: str | None = None,
    razorpay_order_id: str | None = None,
) -> list[WalletTransaction]:
    wallet = await get_wallet_for_update(db, user_id)
    txs: list[WalletTransaction] = []

    if base_credits > 0:
        wallet.credits_balance += base_credits
        wallet.total_credits_purchased += base_credits
        txs.append(
            await _record_transaction(
                db,
                wallet=wallet,
                user_id=user_id,
                tx_type=WalletTransactionType.TOPUP,
                credits=base_credits,
                description=description,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
            )
        )

    if bonus_credits > 0:
        wallet.credits_balance += bonus_credits
        wallet.total_credits_purchased += bonus_credits
        txs.append(
            await _record_transaction(
                db,
                wallet=wallet,
                user_id=user_id,
                tx_type=WalletTransactionType.BONUS,
                credits=bonus_credits,
                description=f"Bonus credits — {description}",
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
            )
        )

    return txs


async def refund_credits(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    description: str,
    experiment_id: UUID | None = None,
) -> WalletTransaction:
    if amount <= 0:
        raise ValueError("refund amount must be positive")

    wallet = await get_wallet_for_update(db, user_id)
    wallet.credits_balance += amount
    if wallet.total_credits_consumed >= amount:
        wallet.total_credits_consumed -= amount
    return await _record_transaction(
        db,
        wallet=wallet,
        user_id=user_id,
        tx_type=WalletTransactionType.REFUND,
        credits=amount,
        description=description,
        experiment_id=experiment_id,
    )


async def redeem_coupon(
    db: AsyncSession,
    *,
    user: User,
    code: str,
) -> WalletTransaction:
    coupon = await get_coupon_for_update(db, code=code)
    if coupon is None:
        raise InvalidCoupon()

    now = datetime.now(timezone.utc)
    if coupon.archived_at is not None:
        raise CouponRedemptionBlocked(
            error_code="coupon_disabled",
            message=coupon.disabled_message or DEFAULT_DISABLED_MESSAGE,
        )
    if not coupon.enabled:
        raise CouponRedemptionBlocked(
            error_code="coupon_disabled",
            message=coupon.disabled_message or DEFAULT_DISABLED_MESSAGE,
        )
    if coupon.starts_at is not None and now < coupon.starts_at:
        raise CouponRedemptionBlocked(
            error_code="coupon_not_yet_active",
            message=coupon.not_yet_active_message or DEFAULT_NOT_YET_ACTIVE_MESSAGE,
        )
    if coupon.ends_at is not None and now > coupon.ends_at:
        raise CouponRedemptionBlocked(
            error_code="coupon_expired",
            message=coupon.expired_message or DEFAULT_EXPIRED_MESSAGE,
        )

    if await user_has_redeemed_coupon(db, coupon_id=coupon.id, user_id=user.id):
        raise CouponAlreadyRedeemed()
    if is_welcome_coupon_code(coupon.code) and user.has_redeemed_welcome_coupon:
        raise CouponAlreadyRedeemed()

    redemption_count = await count_coupon_redemptions(db, coupon_id=coupon.id)
    if coupon.max_redemptions is not None and redemption_count >= coupon.max_redemptions:
        raise CouponRedemptionBlocked(
            error_code="coupon_limit_reached",
            message=coupon.limit_reached_message or DEFAULT_LIMIT_REACHED_MESSAGE,
        )

    wallet = await get_wallet_for_update(db, user.id)
    wallet.credits_balance += coupon.credits
    wallet.total_credits_purchased += coupon.credits
    if is_welcome_coupon_code(coupon.code):
        user.has_redeemed_welcome_coupon = True

    tx = await _record_transaction(
        db,
        wallet=wallet,
        user_id=user.id,
        tx_type=WalletTransactionType.COUPON,
        credits=coupon.credits,
        description=f"{coupon.code} coupon",
    )
    db.add(
        CouponRedemption(
            coupon_id=coupon.id,
            user_id=user.id,
            credits=coupon.credits,
            wallet_transaction_id=tx.id,
        )
    )
    return tx


def _format_usd_equivalent(credits: int) -> str:
    usd = credits_to_usd(credits)
    normalized = usd.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"${text}"


async def get_wallet_balance_snapshot(
    db: AsyncSession,
    *,
    user: User,
) -> WalletBalanceResponse:
    wallet = await get_or_create_wallet(db, user.id)
    packs = [
        CreditPackResponse(
            id=pack.id,
            name=pack.name,
            usd_cents=pack.usd_cents,
            usd_display=pack.usd_display,
            base_credits=pack.base_credits,
            bonus_credits=pack.bonus_credits,
            total_credits=pack.total_credits,
        )
        for pack in CREDIT_PACKS
    ]
    return WalletBalanceResponse(
        credits_balance=wallet.credits_balance,
        usd_equivalent=_format_usd_equivalent(wallet.credits_balance),
        total_credits_purchased=wallet.total_credits_purchased,
        total_credits_consumed=wallet.total_credits_consumed,
        credit_conversion_rate=CREDIT_CONVERSION_RATE,
        has_redeemed_welcome_coupon=user.has_redeemed_welcome_coupon,
        packs=packs,
    )


async def redeem_coupon_for_user(
    db: AsyncSession,
    *,
    user: User,
    code: str,
) -> RedeemCouponResponse:
    tx = await redeem_coupon(db, user=user, code=code)
    wallet = await get_or_create_wallet(db, user.id)
    return RedeemCouponResponse(
        code=code.strip().upper(),
        credits_added=tx.credits,
        new_balance=wallet.credits_balance,
    )


def _format_order_reference(order_id: str) -> str:
    suffix = order_id[-12:] if len(order_id) > 12 else order_id
    return f"Order …{suffix}"


def _transaction_title(tx: WalletTransaction) -> str:
    if tx.type == WalletTransactionType.TOPUP:
        return "Credit pack purchase"
    if tx.type == WalletTransactionType.BONUS:
        return "Pack bonus credits"
    if tx.type == WalletTransactionType.COUPON:
        return "Coupon redeemed"
    if tx.type == WalletTransactionType.REFUND:
        return "Credit refund"
    if tx.type == WalletTransactionType.ADMIN_ADJUSTMENT:
        return "Account adjustment"
    if tx.type == WalletTransactionType.SERVICE_USAGE:
        base = tx.description.split(" (experiment", maxsplit=1)[0].strip()
        for label in SERVICE_LABELS.values():
            if base == label or base.startswith(label):
                return label
        return base or "Service charge"
    return tx.description


def _transaction_detail(
    tx: WalletTransaction,
    *,
    experiment_name: str | None,
) -> str | None:
    if tx.type == WalletTransactionType.REFUND:
        reason = tx.description.removeprefix("Refund: ").strip()
        if experiment_name:
            return f"{experiment_name} — {reason}"
        return reason or None
    if tx.type == WalletTransactionType.SERVICE_USAGE and experiment_name:
        return experiment_name
    if tx.type in {WalletTransactionType.TOPUP, WalletTransactionType.BONUS}:
        detail = tx.description.removeprefix("Bonus credits — ").strip()
        return detail or None
    if tx.type == WalletTransactionType.COUPON:
        return None
    return experiment_name


def _transaction_reference(tx: WalletTransaction) -> str | None:
    if tx.razorpay_order_id:
        return _format_order_reference(tx.razorpay_order_id)
    if tx.type == WalletTransactionType.COUPON:
        code = tx.description.removesuffix(" coupon").strip()
        return code or None
    return None


def _to_transaction_item(
    tx: WalletTransaction,
    *,
    experiment_name: str | None,
    balance_after: int,
) -> WalletTransactionItem:
    return WalletTransactionItem(
        id=tx.id,
        type=tx.type,
        credits=tx.credits,
        title=_transaction_title(tx),
        detail=_transaction_detail(tx, experiment_name=experiment_name),
        reference=_transaction_reference(tx),
        created_at=tx.created_at,
        balance_after=balance_after,
        experiment_id=tx.experiment_id,
        experiment_name=experiment_name,
    )


async def list_wallet_transactions(
    db: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> WalletTransactionsResponse:
    """Return paginated ledger rows newest-first with post-transaction balances."""
    bounded_limit = min(max(limit, 1), 50)
    bounded_offset = max(offset, 0)

    wallet = await get_or_create_wallet(db, user_id)

    total = (
        await db.execute(
            select(func.count())
            .select_from(WalletTransaction)
            .where(WalletTransaction.user_id == user_id)
        )
    ).scalar_one()

    if total == 0:
        return WalletTransactionsResponse(
            transactions=[],
            total=0,
            limit=bounded_limit,
            offset=bounded_offset,
            has_more=False,
            credits_balance=wallet.credits_balance,
            total_credits_purchased=wallet.total_credits_purchased,
            total_credits_consumed=wallet.total_credits_consumed,
        )

    fetch_count = min(bounded_offset + bounded_limit, total)
    result = await db.execute(
        select(WalletTransaction, Experiment.name)
        .outerjoin(Experiment, WalletTransaction.experiment_id == Experiment.id)
        .where(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .limit(fetch_count)
    )
    rows = result.all()

    running_balance = wallet.credits_balance
    computed: list[tuple[WalletTransaction, str | None, int]] = []
    for tx, experiment_name in rows:
        computed.append((tx, experiment_name, running_balance))
        running_balance -= tx.credits

    page_rows = computed[bounded_offset : bounded_offset + bounded_limit]
    items = [
        _to_transaction_item(tx, experiment_name=experiment_name, balance_after=balance_after)
        for tx, experiment_name, balance_after in page_rows
    ]

    return WalletTransactionsResponse(
        transactions=items,
        total=total,
        limit=bounded_limit,
        offset=bounded_offset,
        has_more=bounded_offset + len(items) < total,
        credits_balance=wallet.credits_balance,
        total_credits_purchased=wallet.total_credits_purchased,
        total_credits_consumed=wallet.total_credits_consumed,
    )
