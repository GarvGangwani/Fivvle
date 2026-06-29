"""Tests for wallet debit, refund, and coupon logic (monetization Phase 10)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import WalletTransactionType
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.db.models.wallet_transaction import WalletTransaction
from app.services.wallet_service import (
    CouponAlreadyRedeemed,
    InsufficientCredits,
    InvalidCoupon,
    debit_credits,
    get_or_create_wallet,
    redeem_coupon,
    refund_credits,
    refund_service,
    require_and_debit_service,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
def monetization_enabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("MONETIZATION_ENABLED", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("MONETIZATION_ENABLED", raising=False)
    get_settings.cache_clear()


async def _make_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"wallet-svc-{uuid4()}",
        email=f"wallet-svc-{uuid4()}@example.com",
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_get_or_create_wallet_idempotent(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    first = await get_or_create_wallet(db_session, user.id)
    second = await get_or_create_wallet(db_session, user.id)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_debit_credits_reduces_balance_and_records_tx(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    wallet = Wallet(user_id=user.id, credits_balance=100)
    db_session.add(wallet)
    await db_session.flush()

    tx = await debit_credits(
        db_session,
        user_id=user.id,
        amount=30,
        description="Test debit",
    )
    await db_session.commit()
    await db_session.refresh(wallet)

    assert wallet.credits_balance == 70
    assert wallet.total_credits_consumed == 30
    assert tx.credits == -30
    assert tx.type == WalletTransactionType.SERVICE_USAGE


@pytest.mark.asyncio
async def test_debit_credits_raises_when_insufficient(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id, credits_balance=10))
    await db_session.flush()

    with pytest.raises(InsufficientCredits) as exc_info:
        await debit_credits(
            db_session,
            user_id=user.id,
            amount=50,
            description="Too much",
        )

    assert exc_info.value.available == 10
    assert exc_info.value.required == 50


@pytest.mark.asyncio
async def test_require_and_debit_service_no_op_when_monetization_disabled(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id, credits_balance=0))
    await db_session.flush()

    result = await require_and_debit_service(
        db_session,
        user_id=user.id,
        service="fullValidationFlow",
    )

    assert result is None
    wallet = (
        await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    ).scalar_one()
    assert wallet.credits_balance == 0


@pytest.mark.asyncio
async def test_require_and_debit_service_debits_when_enabled(
    db_session: AsyncSession,
    monetization_enabled: None,
) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id, credits_balance=50))
    await db_session.flush()

    tx = await require_and_debit_service(
        db_session,
        user_id=user.id,
        service="fullValidationFlow",
    )
    await db_session.commit()

    assert tx is not None
    assert tx.credits == -50
    wallet = (
        await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    ).scalar_one()
    assert wallet.credits_balance == 0


@pytest.mark.asyncio
async def test_refund_service_restores_balance(
    db_session: AsyncSession,
    monetization_enabled: None,
) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id, credits_balance=50))
    await db_session.flush()

    await require_and_debit_service(
        db_session,
        user_id=user.id,
        service="insightReport",
    )
    await refund_service(
        db_session,
        user_id=user.id,
        service="insightReport",
        reason="dispatch failed",
    )
    await db_session.commit()

    wallet = (
        await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    ).scalar_one()
    assert wallet.credits_balance == 50
    assert wallet.total_credits_consumed == 0


@pytest.mark.asyncio
async def test_refund_credits_increments_balance(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    wallet = Wallet(user_id=user.id, credits_balance=10, total_credits_consumed=20)
    db_session.add(wallet)
    await db_session.flush()

    tx = await refund_credits(
        db_session,
        user_id=user.id,
        amount=20,
        description="Manual refund",
    )
    await db_session.commit()
    await db_session.refresh(wallet)

    assert wallet.credits_balance == 30
    assert wallet.total_credits_consumed == 0
    assert tx.type == WalletTransactionType.REFUND


@pytest.mark.asyncio
async def test_redeem_welcome_coupon_credits_wallet(db_session: AsyncSession) -> None:
    from tests.helpers.coupons import ensure_welcome_coupon

    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id, credits_balance=0))
    await ensure_welcome_coupon(db_session)
    await db_session.flush()

    tx = await redeem_coupon(db_session, user=user, code="welcome5")
    await db_session.commit()

    wallet = (
        await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    ).scalar_one()
    assert wallet.credits_balance == 25
    assert user.has_redeemed_welcome_coupon is True
    assert tx.type == WalletTransactionType.COUPON


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_unknown_code(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    with pytest.raises(InvalidCoupon):
        await redeem_coupon(db_session, user=user, code="NOTREAL")


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_second_redemption(db_session: AsyncSession) -> None:
    from tests.helpers.coupons import ensure_welcome_coupon

    user = await _make_user(db_session)
    await ensure_welcome_coupon(db_session)
    user.has_redeemed_welcome_coupon = True
    db_session.add(Wallet(user_id=user.id))
    await db_session.flush()

    with pytest.raises(CouponAlreadyRedeemed):
        await redeem_coupon(db_session, user=user, code="WELCOME5")
