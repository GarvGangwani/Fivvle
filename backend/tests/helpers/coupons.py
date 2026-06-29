"""Shared helpers for coupon tests."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.coupon import Coupon
from app.pricing import WELCOME_COUPON_CODE, WELCOME_COUPON_CREDITS


async def ensure_welcome_coupon(db: AsyncSession) -> Coupon:
    result = await db.execute(select(Coupon).where(Coupon.code == WELCOME_COUPON_CODE))
    coupon = result.scalar_one_or_none()
    if coupon is not None:
        return coupon

    coupon = Coupon(
        code=WELCOME_COUPON_CODE,
        credits=WELCOME_COUPON_CREDITS,
        enabled=True,
    )
    db.add(coupon)
    await db.flush()
    return coupon
