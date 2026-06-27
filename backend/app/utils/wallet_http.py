"""HTTP helpers for wallet errors and service debits."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.pricing import ServiceKey
from app.services.wallet_service import (
    InsufficientCredits,
    refund_service,
    require_and_debit_service,
)


def insufficient_credits_http(exc: InsufficientCredits) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "error": "insufficient_credits",
            "available": exc.available,
            "required": exc.required,
        },
    )


async def debit_for_service_or_raise(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    experiment_id: UUID | None = None,
) -> None:
    try:
        await require_and_debit_service(
            db,
            user_id=user_id,
            service=service,
            experiment_id=experiment_id,
        )
    except InsufficientCredits as exc:
        raise insufficient_credits_http(exc) from exc


async def refund_for_service(
    db: AsyncSession,
    *,
    user_id: UUID,
    service: ServiceKey,
    reason: str,
    experiment_id: UUID | None = None,
) -> None:
    await refund_service(
        db,
        user_id=user_id,
        service=service,
        reason=reason,
        experiment_id=experiment_id,
    )
