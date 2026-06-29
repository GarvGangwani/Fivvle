"""Admin coupon CRUD and redemption analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.coupon import Coupon
from app.db.models.coupon_redemption import CouponRedemption
from app.pricing import CREDIT_CONVERSION_RATE, WELCOME_COUPON_CODE, credits_to_usd
from app.schemas.admin_coupon import (
    AdminCouponCreateRequest,
    AdminCouponListResponse,
    AdminCouponSummary,
    AdminCouponUpdateRequest,
)


class CouponServiceError(Exception):
    """Base coupon service error."""


class DuplicateCouponCode(CouponServiceError):
    """Coupon code already exists."""


class CouponNotFound(CouponServiceError):
    """Coupon id not found."""


class CouponHasRedemptions(CouponServiceError):
    """Coupon cannot be deleted while redemptions exist."""


def normalize_coupon_code(code: str) -> str:
    normalized = code.strip().upper()
    if not normalized:
        raise ValueError("Coupon code cannot be empty.")
    return normalized


def format_usd_from_credits(credits: int) -> str:
    usd = credits_to_usd(credits)
    normalized = usd.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"${text}"


def _remaining_redemptions(coupon: Coupon, redemption_count: int) -> int | None:
    if coupon.max_redemptions is None:
        return None
    return max(coupon.max_redemptions - redemption_count, 0)


async def _redemption_stats(
    db: AsyncSession,
    coupon_ids: list[UUID],
) -> dict[UUID, tuple[int, int]]:
    if not coupon_ids:
        return {}
    result = await db.execute(
        select(
            CouponRedemption.coupon_id,
            func.count(CouponRedemption.id),
            func.coalesce(func.sum(CouponRedemption.credits), 0),
        )
        .where(CouponRedemption.coupon_id.in_(coupon_ids))
        .group_by(CouponRedemption.coupon_id)
    )
    return {
        coupon_id: (int(count), int(total_credits))
        for coupon_id, count, total_credits in result.all()
    }


def _to_summary(
    coupon: Coupon,
    *,
    redemption_count: int,
    total_credits_gifted: int,
) -> AdminCouponSummary:
    return AdminCouponSummary(
        id=coupon.id,
        code=coupon.code,
        credits=coupon.credits,
        enabled=coupon.enabled,
        max_redemptions=coupon.max_redemptions,
        redemption_count=redemption_count,
        remaining_redemptions=_remaining_redemptions(coupon, redemption_count),
        total_credits_gifted=total_credits_gifted,
        total_usd_gifted=format_usd_from_credits(total_credits_gifted),
        starts_at=coupon.starts_at,
        ends_at=coupon.ends_at,
        limit_reached_message=coupon.limit_reached_message,
        not_yet_active_message=coupon.not_yet_active_message,
        expired_message=coupon.expired_message,
        disabled_message=coupon.disabled_message,
        archived_at=coupon.archived_at,
        created_at=coupon.created_at,
        updated_at=coupon.updated_at,
    )


async def _get_coupon_or_raise(db: AsyncSession, coupon_id: UUID) -> Coupon:
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if coupon is None:
        raise CouponNotFound(f"Coupon not found: {coupon_id}")
    return coupon


async def list_admin_coupons(
    db: AsyncSession,
    *,
    include_archived: bool = False,
) -> AdminCouponListResponse:
    query = select(Coupon).order_by(Coupon.created_at.desc())
    if not include_archived:
        query = query.where(Coupon.archived_at.is_(None))
    result = await db.execute(query)
    coupons = result.scalars().all()
    stats = await _redemption_stats(db, [coupon.id for coupon in coupons])

    summaries: list[AdminCouponSummary] = []
    total_credits_all = 0
    for coupon in coupons:
        count, gifted = stats.get(coupon.id, (0, 0))
        total_credits_all += gifted
        summaries.append(
            _to_summary(
                coupon,
                redemption_count=count,
                total_credits_gifted=gifted,
            )
        )

    return AdminCouponListResponse(
        coupons=summaries,
        total_usd_gifted_all_coupons=format_usd_from_credits(total_credits_all),
    )


async def create_admin_coupon(
    db: AsyncSession,
    *,
    body: AdminCouponCreateRequest,
) -> AdminCouponSummary:
    existing = await db.execute(select(Coupon.id).where(Coupon.code == body.code))
    if existing.scalar_one_or_none() is not None:
        raise DuplicateCouponCode(f"Coupon code already exists: {body.code}")

    coupon = Coupon(
        code=body.code,
        credits=body.credits,
        enabled=body.enabled,
        max_redemptions=body.max_redemptions,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        limit_reached_message=body.limit_reached_message,
        not_yet_active_message=body.not_yet_active_message,
        expired_message=body.expired_message,
        disabled_message=body.disabled_message,
    )
    db.add(coupon)
    await db.flush()
    return _to_summary(coupon, redemption_count=0, total_credits_gifted=0)


async def update_admin_coupon(
    db: AsyncSession,
    *,
    coupon_id: UUID,
    body: AdminCouponUpdateRequest,
) -> AdminCouponSummary:
    coupon = await _get_coupon_or_raise(db, coupon_id)

    if body.credits is not None:
        coupon.credits = body.credits
    if body.enabled is not None:
        coupon.enabled = body.enabled
    if body.max_redemptions is not None:
        coupon.max_redemptions = body.max_redemptions
    if body.clear_starts_at:
        coupon.starts_at = None
    elif body.starts_at is not None:
        coupon.starts_at = body.starts_at
    if body.clear_ends_at:
        coupon.ends_at = None
    elif body.ends_at is not None:
        coupon.ends_at = body.ends_at
    if body.clear_limit_reached_message:
        coupon.limit_reached_message = None
    elif body.limit_reached_message is not None:
        coupon.limit_reached_message = body.limit_reached_message
    if body.clear_not_yet_active_message:
        coupon.not_yet_active_message = None
    elif body.not_yet_active_message is not None:
        coupon.not_yet_active_message = body.not_yet_active_message
    if body.clear_expired_message:
        coupon.expired_message = None
    elif body.expired_message is not None:
        coupon.expired_message = body.expired_message
    if body.clear_disabled_message:
        coupon.disabled_message = None
    elif body.disabled_message is not None:
        coupon.disabled_message = body.disabled_message

    coupon.updated_at = datetime.now(timezone.utc)
    await db.flush()

    stats = await _redemption_stats(db, [coupon.id])
    count, gifted = stats.get(coupon.id, (0, 0))
    return _to_summary(coupon, redemption_count=count, total_credits_gifted=gifted)


async def archive_admin_coupon(db: AsyncSession, *, coupon_id: UUID) -> AdminCouponSummary:
    coupon = await _get_coupon_or_raise(db, coupon_id)
    now = datetime.now(timezone.utc)
    coupon.archived_at = now
    coupon.enabled = False
    coupon.updated_at = now
    await db.flush()

    stats = await _redemption_stats(db, [coupon.id])
    count, gifted = stats.get(coupon.id, (0, 0))
    return _to_summary(coupon, redemption_count=count, total_credits_gifted=gifted)


async def restore_admin_coupon(db: AsyncSession, *, coupon_id: UUID) -> AdminCouponSummary:
    coupon = await _get_coupon_or_raise(db, coupon_id)
    now = datetime.now(timezone.utc)
    coupon.archived_at = None
    coupon.updated_at = now
    await db.flush()

    stats = await _redemption_stats(db, [coupon.id])
    count, gifted = stats.get(coupon.id, (0, 0))
    return _to_summary(coupon, redemption_count=count, total_credits_gifted=gifted)


async def delete_admin_coupon(db: AsyncSession, *, coupon_id: UUID) -> None:
    coupon = await _get_coupon_or_raise(db, coupon_id)
    redemption_count = await count_coupon_redemptions(db, coupon_id=coupon.id)
    if redemption_count > 0:
        raise CouponHasRedemptions(
            f"Coupon {coupon_id} has {redemption_count} redemptions and cannot be deleted."
        )
    await db.execute(delete(Coupon).where(Coupon.id == coupon_id))
    await db.flush()


async def get_coupon_for_update(
    db: AsyncSession,
    *,
    code: str,
) -> Coupon | None:
    normalized = normalize_coupon_code(code)
    result = await db.execute(
        select(Coupon).where(Coupon.code == normalized).with_for_update()
    )
    return result.scalar_one_or_none()


async def count_coupon_redemptions(db: AsyncSession, *, coupon_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(CouponRedemption)
        .where(CouponRedemption.coupon_id == coupon_id)
    )
    return int(result.scalar_one())


async def user_has_redeemed_coupon(
    db: AsyncSession,
    *,
    coupon_id: UUID,
    user_id: UUID,
) -> bool:
    result = await db.execute(
        select(CouponRedemption.id).where(
            CouponRedemption.coupon_id == coupon_id,
            CouponRedemption.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


def is_welcome_coupon_code(code: str) -> bool:
    return normalize_coupon_code(code) == WELCOME_COUPON_CODE


DEFAULT_LIMIT_REACHED_MESSAGE = (
    "This coupon has reached its redemption limit and is no longer available."
)
DEFAULT_NOT_YET_ACTIVE_MESSAGE = "This coupon is not active yet. Please try again later."
DEFAULT_EXPIRED_MESSAGE = "This coupon has expired."
DEFAULT_DISABLED_MESSAGE = "This coupon is no longer available."
DEFAULT_INVALID_MESSAGE = "This coupon code is not valid."
