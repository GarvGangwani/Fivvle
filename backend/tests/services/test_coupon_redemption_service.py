"""Service tests for admin coupon redemption rules."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.coupon import Coupon
from app.db.models.wallet import Wallet
from app.services.wallet_service import (
    CouponAlreadyRedeemed,
    CouponRedemptionBlocked,
    redeem_coupon,
)
from tests.services.test_wallet_service import _make_user


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
async def test_redeem_coupon_rejects_disabled_with_custom_message(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id, credits_balance=0))
    db_session.add(
        Coupon(
            code="DISABLED10",
            credits=10,
            enabled=False,
            disabled_message="Promo paused until launch day.",
        )
    )
    await db_session.flush()

    with pytest.raises(CouponRedemptionBlocked) as exc_info:
        await redeem_coupon(db_session, user=user, code="DISABLED10")

    assert exc_info.value.error_code == "coupon_disabled"
    assert exc_info.value.message == "Promo paused until launch day."


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_limit_reached(db_session: AsyncSession) -> None:
    first_user = await _make_user(db_session)
    second_user = await _make_user(db_session)
    db_session.add(Wallet(user_id=first_user.id))
    db_session.add(Wallet(user_id=second_user.id))
    code = f"LIMIT1{uuid4().hex[:6].upper()}"
    db_session.add(
        Coupon(
            code=code,
            credits=15,
            enabled=True,
            max_redemptions=1,
            limit_reached_message="Only 1 founder could claim this code.",
        )
    )
    await db_session.flush()

    await redeem_coupon(db_session, user=first_user, code=code)
    await db_session.commit()

    with pytest.raises(CouponRedemptionBlocked) as exc_info:
        await redeem_coupon(db_session, user=second_user, code=code)

    assert exc_info.value.error_code == "coupon_limit_reached"
    assert "Only 1 founder" in exc_info.value.message


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_before_start_time(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id))
    starts_at = datetime.now(timezone.utc) + timedelta(days=2)
    db_session.add(
        Coupon(
            code="FUTURE25",
            credits=25,
            enabled=True,
            starts_at=starts_at,
            not_yet_active_message="Opens on launch day.",
        )
    )
    await db_session.flush()

    with pytest.raises(CouponRedemptionBlocked) as exc_info:
        await redeem_coupon(db_session, user=user, code="FUTURE25")

    assert exc_info.value.error_code == "coupon_not_yet_active"
    assert exc_info.value.message == "Opens on launch day."


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_after_end_time(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id))
    db_session.add(
        Coupon(
            code="EXPIRED25",
            credits=25,
            enabled=True,
            ends_at=datetime.now(timezone.utc) - timedelta(hours=1),
            expired_message="This flash sale ended.",
        )
    )
    await db_session.flush()

    with pytest.raises(CouponRedemptionBlocked) as exc_info:
        await redeem_coupon(db_session, user=user, code="EXPIRED25")

    assert exc_info.value.error_code == "coupon_expired"
    assert exc_info.value.message == "This flash sale ended."


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_archived(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id))
    db_session.add(
        Coupon(
            code="ARCHIVED10",
            credits=10,
            enabled=True,
            archived_at=datetime.now(timezone.utc),
            disabled_message="This promo was retired.",
        )
    )
    await db_session.flush()

    with pytest.raises(CouponRedemptionBlocked) as exc_info:
        await redeem_coupon(db_session, user=user, code="ARCHIVED10")

    assert exc_info.value.error_code == "coupon_disabled"
    assert exc_info.value.message == "This promo was retired."


@pytest.mark.asyncio
async def test_redeem_coupon_rejects_duplicate_user(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(Wallet(user_id=user.id))
    code = f"DUPE10{uuid4().hex[:6].upper()}"
    db_session.add(Coupon(code=code, credits=10, enabled=True))
    await db_session.flush()

    await redeem_coupon(db_session, user=user, code=code)
    await db_session.commit()

    with pytest.raises(CouponAlreadyRedeemed):
        await redeem_coupon(db_session, user=user, code=code)
