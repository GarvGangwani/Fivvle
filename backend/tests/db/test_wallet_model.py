"""Tests for Wallet ORM model (monetization Phase 8)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db.models.user import User
from app.db.models.wallet import Wallet


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_wallet_persists_with_defaults(db_session: AsyncSession) -> None:
    user = User(
        firebase_uid=f"wallet-model-{uuid4()}",
        email=f"wallet-model-{uuid4()}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    wallet = Wallet(user_id=user.id)
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)

    assert wallet.id is not None
    assert wallet.credits_balance == 0
    assert wallet.total_credits_purchased == 0
    assert wallet.total_credits_consumed == 0
    assert wallet.created_at is not None
    assert wallet.updated_at is not None


@pytest.mark.asyncio
async def test_wallet_one_per_user_enforced(db_session: AsyncSession) -> None:
    user = User(
        firebase_uid=f"wallet-dup-{uuid4()}",
        email=f"wallet-dup-{uuid4()}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(Wallet(user_id=user.id, credits_balance=10))
    db_session.add(Wallet(user_id=user.id, credits_balance=20))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_wallet_relationship(db_session: AsyncSession) -> None:
    user = User(
        firebase_uid=f"wallet-rel-{uuid4()}",
        email=f"wallet-rel-{uuid4()}@example.com",
        has_redeemed_welcome_coupon=False,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Wallet(user_id=user.id, credits_balance=145))
    await db_session.commit()

    row = (
        await db_session.execute(
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.wallet))
        )
    ).scalar_one()
    assert row.wallet is not None
    assert row.wallet.credits_balance == 145
    assert row.has_redeemed_welcome_coupon is False


def test_wallet_model_importable_from_package() -> None:
    from app.db.models import Wallet as ImportedWallet  # noqa: PLC0415

    assert ImportedWallet.__tablename__ == "wallets"
