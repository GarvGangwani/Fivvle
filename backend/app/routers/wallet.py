"""Wallet routes — balance, coupons, and Razorpay credit-pack purchases."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_session
from app.integrations.razorpay import (
    RazorpayApiError,
    RazorpayNotConfiguredError,
    RazorpaySignatureError,
)
from app.pricing import get_pack
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.wallet import (
    CreateCreditPackOrderRequest,
    CreateCreditPackOrderResponse,
    RedeemCouponRequest,
    RedeemCouponResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    WalletBalanceResponse,
    WalletTransactionsResponse,
)
from app.services.payment_service import (
    DuplicatePayment,
    PaymentOrderConflict,
    PaymentOrderNotFound,
    create_credit_pack_order,
    verify_and_fulfill_payment,
)
from app.services.wallet_service import (
    CouponAlreadyRedeemed,
    CouponRedemptionBlocked,
    InvalidCoupon,
    get_wallet_balance_snapshot,
    list_wallet_transactions,
    redeem_coupon_for_user,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("", response_model=WalletBalanceResponse)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_wallet(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WalletBalanceResponse:
    """Return wallet balance and server-authoritative credit pack catalog."""
    return await get_wallet_balance_snapshot(db, user=current_user)


@router.get("/transactions", response_model=WalletTransactionsResponse)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_wallet_transactions(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WalletTransactionsResponse:
    """Paginated credit ledger — purchases, coupons, service charges, refunds."""
    return await list_wallet_transactions(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/coupons/redeem",
    response_model=RedeemCouponResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def redeem_wallet_coupon(
    request: Request,
    response: Response,
    body: RedeemCouponRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RedeemCouponResponse:
    try:
        return await redeem_coupon_for_user(db, user=current_user, code=body.code)
    except InvalidCoupon as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_coupon", "message": exc.message},
        ) from exc
    except CouponAlreadyRedeemed as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "coupon_already_redeemed", "message": exc.message},
        ) from exc
    except CouponRedemptionBlocked as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": exc.error_code, "message": exc.message},
        ) from exc


@router.post(
    "/orders",
    response_model=CreateCreditPackOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def create_wallet_order(
    request: Request,
    response: Response,
    body: CreateCreditPackOrderRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CreateCreditPackOrderResponse:
    """Create a Razorpay order for a predefined credit pack.

    The client sends only ``packId``; all prices and credit amounts are
    resolved server-side from ``app.pricing``.
    """
    try:
        get_pack(body.pack_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown credit pack",
        ) from exc

    try:
        created = await create_credit_pack_order(
            db,
            user_id=current_user.id,
            pack_id=body.pack_id,
        )
    except RazorpayNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments are not configured",
        ) from exc
    except RazorpayApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create payment order, please try again",
        ) from exc

    return CreateCreditPackOrderResponse(
        payment_order_id=created.payment_order_id,
        pack_id=created.pack_id,
        pack_name=created.pack_name,
        usd_cents=created.usd_cents,
        base_credits=created.base_credits,
        bonus_credits=created.bonus_credits,
        total_credits=created.total_credits,
        amount_inr_paise=created.amount_inr_paise,
        currency=created.currency,
        razorpay_key_id=created.razorpay_key_id,
        razorpay_order_id=created.razorpay_order_id,
        receipt=created.receipt,
    )


@router.post(
    "/payments/verify",
    response_model=VerifyPaymentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def verify_wallet_payment(
    request: Request,
    response: Response,
    body: VerifyPaymentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VerifyPaymentResponse:
    """Verify Razorpay payment signature and credit the user's wallet."""
    try:
        fulfilled = await verify_and_fulfill_payment(
            db,
            user_id=current_user.id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_order_id=body.razorpay_order_id,
            razorpay_signature=body.razorpay_signature,
        )
    except PaymentOrderNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order not found",
        ) from exc
    except RazorpaySignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        ) from exc
    except (PaymentOrderConflict, DuplicatePayment) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment already processed",
        ) from exc

    return VerifyPaymentResponse(
        payment_order_id=fulfilled.payment_order_id,
        credits_added=fulfilled.credits_added,
        bonus_credits=fulfilled.bonus_credits,
        new_balance=fulfilled.new_balance,
        already_processed=fulfilled.already_processed,
        razorpay_payment_id=fulfilled.razorpay_payment_id,
        razorpay_order_id=fulfilled.razorpay_order_id,
    )
