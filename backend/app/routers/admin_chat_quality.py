"""Admin-only chat-mode quality observability endpoints (planning doc §6.4).

Every route is gated behind get_current_admin_user — non-admin authenticated
users receive 403.
"""

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin_user
from app.db.models.user import User
from app.db.session import get_session
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.chat_observability import (
    DispatchLatencyStatsResponse,
    DispatchTriggerRatioResponse,
    FirstTurnDimensionDistributionResponse,
    RefinementTurnCountDistributionResponse,
    UserReplyLengthStatsResponse,
)
from app.services import chat_observability

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/chat-quality/refinement-turns",
    response_model=RefinementTurnCountDistributionResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_refinement_turn_distribution(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    since: datetime | None = Query(default=None),
) -> RefinementTurnCountDistributionResponse:
    distribution = await chat_observability.refinement_turn_count_distribution(db, since)
    return RefinementTurnCountDistributionResponse(distribution=distribution)


@router.get(
    "/chat-quality/reply-lengths",
    response_model=UserReplyLengthStatsResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_user_reply_length_stats(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    since: datetime | None = Query(default=None),
) -> UserReplyLengthStatsResponse:
    stats = await chat_observability.user_reply_length_stats(db, since)
    return UserReplyLengthStatsResponse(**stats)


@router.get(
    "/chat-quality/dispatch-latency",
    response_model=DispatchLatencyStatsResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_dispatch_latency_stats(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    since: datetime | None = Query(default=None),
) -> DispatchLatencyStatsResponse:
    stats = await chat_observability.dispatch_to_completion_latency_stats(db, since)
    return DispatchLatencyStatsResponse(**stats)


@router.get(
    "/chat-quality/dispatch-triggers",
    response_model=DispatchTriggerRatioResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_dispatch_trigger_ratio(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    since: datetime | None = Query(default=None),
) -> DispatchTriggerRatioResponse:
    ratio = await chat_observability.dispatch_trigger_ratio(db, since)
    return DispatchTriggerRatioResponse(**ratio)


@router.get(
    "/chat-quality/first-turn-dimensions",
    response_model=FirstTurnDimensionDistributionResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_first_turn_dimension_distribution(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    since: datetime | None = Query(default=None),
) -> FirstTurnDimensionDistributionResponse:
    distribution = await chat_observability.first_turn_dimension_distribution(db, since)
    return FirstTurnDimensionDistributionResponse(distribution=distribution)
