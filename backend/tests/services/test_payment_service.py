"""Tests for Razorpay credit-pack payment service (Phase 11)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import PaymentOrderStatus, WalletTransactionType
from app.db.models.payment_order import PaymentOrder
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.db.models.wallet_transaction import WalletTransaction
from app.integrations.razorpay import RazorpayOrderResult, reset_client_for_tests
from app.services.payment_service import (
    DuplicatePayment,
    PaymentOrderConflict,
    create_credit_pack_order,
    verify_and_fulfill_payment,
)
from app.services.wallet_service import get_or_create_wallet


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


async def _make_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"pay-svc-{uuid4()}",
        email=f"pay-svc-{uuid4()}@example.com",
    )
    db.add(user)
    await db.flush()
    await get_or_create_wallet(db, user.id)
    return user


@pytest.mark.asyncio
async def test_create_credit_pack_order_persists_row(
    db_session: AsyncSession,
    razorpay_credentials: None,
) -> None:
    user = await _make_user(db_session)
    fake_order = RazorpayOrderResult(
        order_id="order_test_123",
        amount_paise=41500,
        currency="INR",
        receipt="abc123",
    )

    with patch(
        "app.services.payment_service.create_order",
        AsyncMock(return_value=fake_order),
    ):
        created = await create_credit_pack_order(
            db_session,
            user_id=user.id,
            pack_id="starter",
        )
        await db_session.commit()

    assert created.pack_id == "starter"
    assert created.base_credits == 25
    assert created.razorpay_order_id == "order_test_123"

    row = (
        await db_session.execute(
            select(PaymentOrder).where(PaymentOrder.id == created.payment_order_id)
        )
    ).scalar_one()
    assert row.status == PaymentOrderStatus.CREATED
    assert row.usd_cents == 500


@pytest.mark.asyncio
async def test_verify_and_fulfill_credits_wallet(
    db_session: AsyncSession,
    razorpay_credentials: None,
) -> None:
    user = await _make_user(db_session)
    fake_order = RazorpayOrderResult(
        order_id="order_fulfill_1",
        amount_paise=41500,
        currency="INR",
        receipt="receipt1",
    )

    with patch(
        "app.services.payment_service.create_order",
        AsyncMock(return_value=fake_order),
    ):
        created = await create_credit_pack_order(
            db_session,
            user_id=user.id,
            pack_id="builder",
        )
        await db_session.commit()

    with patch(
        "app.services.payment_service.verify_payment_signature",
        AsyncMock(return_value=None),
    ):
        fulfilled = await verify_and_fulfill_payment(
            db_session,
            user_id=user.id,
            razorpay_payment_id="pay_test_abc",
            razorpay_order_id=created.razorpay_order_id,
            razorpay_signature="sig_test",
        )
        await db_session.commit()

    assert fulfilled.already_processed is False
    assert fulfilled.credits_added == 50
    assert fulfilled.bonus_credits == 5
    assert fulfilled.new_balance == 55

    txs = (
        await db_session.execute(
            select(WalletTransaction)
            .where(WalletTransaction.user_id == user.id)
            .order_by(WalletTransaction.created_at)
        )
    ).scalars().all()
    assert len(txs) == 2
    assert txs[0].type == WalletTransactionType.TOPUP
    assert txs[0].credits == 50
    assert txs[0].razorpay_payment_id == "pay_test_abc"
    assert txs[1].type == WalletTransactionType.BONUS
    assert txs[1].credits == 5


@pytest.mark.asyncio
async def test_verify_is_idempotent_for_same_payment(
    db_session: AsyncSession,
    razorpay_credentials: None,
) -> None:
    user = await _make_user(db_session)
    fake_order = RazorpayOrderResult(
        order_id="order_idempotent",
        amount_paise=41500,
        currency="INR",
        receipt="receipt2",
    )

    with patch(
        "app.services.payment_service.create_order",
        AsyncMock(return_value=fake_order),
    ):
        created = await create_credit_pack_order(
            db_session,
            user_id=user.id,
            pack_id="starter",
        )
        await db_session.commit()

    with patch(
        "app.services.payment_service.verify_payment_signature",
        AsyncMock(return_value=None),
    ):
        first = await verify_and_fulfill_payment(
            db_session,
            user_id=user.id,
            razorpay_payment_id="pay_idem_1",
            razorpay_order_id=created.razorpay_order_id,
            razorpay_signature="sig",
        )
        await db_session.commit()

        second = await verify_and_fulfill_payment(
            db_session,
            user_id=user.id,
            razorpay_payment_id="pay_idem_1",
            razorpay_order_id=created.razorpay_order_id,
            razorpay_signature="sig",
        )

    assert first.already_processed is False
    assert second.already_processed is True
    assert second.new_balance == 25

    wallet = (
        await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    ).scalar_one()
    assert wallet.credits_balance == 25


@pytest.mark.asyncio
async def test_verify_rejects_conflicting_payment_on_paid_order(
    db_session: AsyncSession,
    razorpay_credentials: None,
) -> None:
    user = await _make_user(db_session)
    fake_order = RazorpayOrderResult(
        order_id="order_conflict",
        amount_paise=41500,
        currency="INR",
        receipt="receipt3",
    )

    with patch(
        "app.services.payment_service.create_order",
        AsyncMock(return_value=fake_order),
    ):
        created = await create_credit_pack_order(
            db_session,
            user_id=user.id,
            pack_id="starter",
        )
        await db_session.commit()

    with patch(
        "app.services.payment_service.verify_payment_signature",
        AsyncMock(return_value=None),
    ):
        await verify_and_fulfill_payment(
            db_session,
            user_id=user.id,
            razorpay_payment_id="pay_first",
            razorpay_order_id=created.razorpay_order_id,
            razorpay_signature="sig",
        )
        await db_session.commit()

        with pytest.raises(PaymentOrderConflict):
            await verify_and_fulfill_payment(
                db_session,
                user_id=user.id,
                razorpay_payment_id="pay_second",
                razorpay_order_id=created.razorpay_order_id,
                razorpay_signature="sig",
            )


@pytest.mark.asyncio
async def test_verify_rejects_duplicate_payment_id_on_different_order(
    db_session: AsyncSession,
    razorpay_credentials: None,
) -> None:
    user = await _make_user(db_session)

    async def _create(pack_id: str, order_id: str) -> str:
        fake = RazorpayOrderResult(
            order_id=order_id,
            amount_paise=41500,
            currency="INR",
            receipt=order_id,
        )
        with patch(
            "app.services.payment_service.create_order",
            AsyncMock(return_value=fake),
        ):
            created = await create_credit_pack_order(
                db_session,
                user_id=user.id,
                pack_id=pack_id,
            )
            await db_session.commit()
            return created.razorpay_order_id

    order_a = await _create("starter", "order_dup_a")
    order_b = await _create("starter", "order_dup_b")

    with patch(
        "app.services.payment_service.verify_payment_signature",
        AsyncMock(return_value=None),
    ):
        await verify_and_fulfill_payment(
            db_session,
            user_id=user.id,
            razorpay_payment_id="pay_shared",
            razorpay_order_id=order_a,
            razorpay_signature="sig",
        )
        await db_session.commit()

        with pytest.raises(DuplicatePayment):
            await verify_and_fulfill_payment(
                db_session,
                user_id=user.id,
                razorpay_payment_id="pay_shared",
                razorpay_order_id=order_b,
                razorpay_signature="sig",
            )
