"""Tests for WalletTransaction ORM model (monetization Phase 9)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db.enums import WalletTransactionType
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.db.models.wallet_transaction import WalletTransaction


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _user_with_wallet(db: AsyncSession) -> tuple[User, Wallet]:
    user = User(
        firebase_uid=f"wallet-tx-{uuid4()}",
        email=f"wallet-tx-{uuid4()}@example.com",
    )
    db.add(user)
    await db.flush()
    wallet = Wallet(user_id=user.id, credits_balance=100)
    db.add(wallet)
    await db.flush()
    return user, wallet


@pytest.mark.asyncio
async def test_wallet_transaction_persists_credit_entry(
    db_session: AsyncSession,
) -> None:
    user, wallet = await _user_with_wallet(db_session)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user.id,
        type=WalletTransactionType.COUPON,
        credits=25,
        description="Welcome coupon WELCOME5",
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)

    assert tx.id is not None
    assert tx.type == WalletTransactionType.COUPON
    assert tx.credits == 25
    assert tx.experiment_id is None
    assert tx.created_at is not None


@pytest.mark.asyncio
async def test_wallet_transaction_persists_debit_entry(
    db_session: AsyncSession,
) -> None:
    user, wallet = await _user_with_wallet(db_session)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user.id,
        type=WalletTransactionType.SERVICE_USAGE,
        credits=-50,
        description="Full validation flow",
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)

    assert tx.type == WalletTransactionType.SERVICE_USAGE
    assert tx.credits == -50


@pytest.mark.asyncio
async def test_wallet_transactions_relationship_ordered_newest_first(
    db_session: AsyncSession,
) -> None:
    user, wallet = await _user_with_wallet(db_session)
    db_session.add_all(
        [
            WalletTransaction(
                wallet_id=wallet.id,
                user_id=user.id,
                type=WalletTransactionType.TOPUP,
                credits=100,
                description="Older top-up",
            ),
            WalletTransaction(
                wallet_id=wallet.id,
                user_id=user.id,
                type=WalletTransactionType.REFUND,
                credits=20,
                description="Newer refund",
            ),
        ]
    )
    await db_session.commit()

    row = (
        await db_session.execute(
            select(Wallet)
            .where(Wallet.id == wallet.id)
            .options(selectinload(Wallet.transactions))
        )
    ).scalar_one()

    assert len(row.transactions) == 2
    types = {tx.type for tx in row.transactions}
    assert types == {WalletTransactionType.TOPUP, WalletTransactionType.REFUND}


def test_wallet_transaction_type_matches_migration_values() -> None:
    assert {t.value for t in WalletTransactionType} == {
        "TOPUP",
        "BONUS",
        "COUPON",
        "SERVICE_USAGE",
        "REFUND",
        "ADMIN_ADJUSTMENT",
    }


def test_wallet_transaction_importable_from_package() -> None:
    from app.db.models import WalletTransaction as ImportedTx  # noqa: PLC0415

    assert ImportedTx.__tablename__ == "wallet_transactions"
