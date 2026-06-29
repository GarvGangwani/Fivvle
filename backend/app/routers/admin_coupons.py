"""Admin-only coupon management routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin_user
from app.db.models.user import User
from app.db.session import get_session
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.admin_coupon import (
    AdminCouponCreateRequest,
    AdminCouponListResponse,
    AdminCouponSummary,
    AdminCouponUpdateRequest,
)
from app.services.coupon_service import (
    CouponHasRedemptions,
    CouponNotFound,
    DuplicateCouponCode,
    archive_admin_coupon,
    create_admin_coupon,
    delete_admin_coupon,
    list_admin_coupons,
    restore_admin_coupon,
    update_admin_coupon,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/coupons", response_model=AdminCouponListResponse)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_admin_coupons(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(get_current_admin_user)],
    include_archived: Annotated[bool, Query()] = False,
) -> AdminCouponListResponse:
    return await list_admin_coupons(db, include_archived=include_archived)


@router.post(
    "/coupons",
    response_model=AdminCouponSummary,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def post_admin_coupon(
    request: Request,
    response: Response,
    body: AdminCouponCreateRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(get_current_admin_user)],
) -> AdminCouponSummary:
    try:
        created = await create_admin_coupon(db, body=body)
    except DuplicateCouponCode as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A coupon with this code already exists.",
        ) from exc
    await db.commit()
    return created


@router.patch("/coupons/{coupon_id}", response_model=AdminCouponSummary)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def patch_admin_coupon(
    request: Request,
    response: Response,
    coupon_id: UUID,
    body: AdminCouponUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(get_current_admin_user)],
) -> AdminCouponSummary:
    try:
        updated = await update_admin_coupon(db, coupon_id=coupon_id, body=body)
    except CouponNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        ) from exc
    await db.commit()
    return updated


@router.post("/coupons/{coupon_id}/archive", response_model=AdminCouponSummary)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def post_archive_admin_coupon(
    request: Request,
    response: Response,
    coupon_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(get_current_admin_user)],
) -> AdminCouponSummary:
    try:
        archived = await archive_admin_coupon(db, coupon_id=coupon_id)
    except CouponNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        ) from exc
    await db.commit()
    return archived


@router.post("/coupons/{coupon_id}/restore", response_model=AdminCouponSummary)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def post_restore_admin_coupon(
    request: Request,
    response: Response,
    coupon_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(get_current_admin_user)],
) -> AdminCouponSummary:
    try:
        restored = await restore_admin_coupon(db, coupon_id=coupon_id)
    except CouponNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        ) from exc
    await db.commit()
    return restored


@router.delete("/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def delete_admin_coupon_route(
    request: Request,
    response: Response,
    coupon_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(get_current_admin_user)],
) -> Response:
    try:
        await delete_admin_coupon(db, coupon_id=coupon_id)
    except CouponNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        ) from exc
    except CouponHasRedemptions as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This coupon has redemptions and cannot be deleted. "
                "Archive it instead to keep redemption history."
            ),
        ) from exc
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
