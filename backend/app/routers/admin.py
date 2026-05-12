"""Admin-only operational endpoints.

NEVER exposed to founders. Every route in this router is gated behind
get_current_admin_user — a non-admin authenticated user gets 403.

Per `.cursorrules`, admin endpoints under /admin/cost/* exist for operating
the platform, not for founder-facing features.

Per AGENTS.md "Authentication and authorization":
- Admin role is determined server-side from User.is_admin (DB column).
- Never from a header, query parameter, or JWT claim the client could spoof.
- Non-admin authenticated users get 403, not 401.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin_user
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.db.models.experiment import Experiment
from app.db.models.external_api_call import ExternalAPICall
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.admin import (
    DailyCostResponse,
    DailyCostRow,
    ExperimentCostResponse,
    PerPhaseCostResponse,
    PhaseCostRow,
    UserCostResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# GET /admin/cost/experiment/{experiment_id}
# ---------------------------------------------------------------------------


@router.get(
    "/cost/experiment/{experiment_id}",
    response_model=ExperimentCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_experiment_cost(
    request: Request,
    experiment_id: UUID,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> ExperimentCostResponse:
    """Return cost totals for a single experiment.

    Returns zeros (not 404) when the experiment has no calls recorded.
    This keeps the endpoint deterministic — "zero cost" is a meaningful answer.
    """
    # LLM cost for this experiment
    llm_stmt = select(
        func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("total_cost"),
        func.count(LLMCall.id).label("call_count"),
    ).where(LLMCall.experiment_id == experiment_id)
    llm_row = (await db.execute(llm_stmt)).one()

    # External API cost for this experiment
    ext_stmt = select(
        func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("total_cost"),
        func.count(ExternalAPICall.id).label("call_count"),
    ).where(ExternalAPICall.experiment_id == experiment_id)
    ext_row = (await db.execute(ext_stmt)).one()

    llm_cost = Decimal(str(llm_row.total_cost))
    ext_cost = Decimal(str(ext_row.total_cost))

    return ExperimentCostResponse(
        experiment_id=experiment_id,
        llm_cost_usd=llm_cost,
        external_api_cost_usd=ext_cost,
        total_cost_usd=llm_cost + ext_cost,
        llm_call_count=llm_row.call_count,
        external_api_call_count=ext_row.call_count,
    )


# ---------------------------------------------------------------------------
# GET /admin/cost/user/{user_id}
# ---------------------------------------------------------------------------


@router.get(
    "/cost/user/{user_id}",
    response_model=UserCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_user_cost(
    request: Request,
    user_id: UUID,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> UserCostResponse:
    """Return cost totals rolled up across all of a user's experiments.

    Joins through the Experiment table to attribute calls to the user.
    LLMCall / ExternalAPICall rows with NULL experiment_id (SET NULL after
    experiment deletion) are NOT counted — they have no owner.
    Returns zeros when the user has no experiments or no recorded calls.
    """
    # Subquery: experiment IDs owned by this user
    exp_ids_subq = select(Experiment.id).where(Experiment.user_id == user_id).scalar_subquery()

    llm_stmt = select(
        func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("total_cost"),
        func.count(LLMCall.id).label("call_count"),
    ).where(LLMCall.experiment_id.in_(exp_ids_subq))
    llm_row = (await db.execute(llm_stmt)).one()

    ext_stmt = select(
        func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("total_cost"),
        func.count(ExternalAPICall.id).label("call_count"),
    ).where(ExternalAPICall.experiment_id.in_(exp_ids_subq))
    ext_row = (await db.execute(ext_stmt)).one()

    llm_cost = Decimal(str(llm_row.total_cost))
    ext_cost = Decimal(str(ext_row.total_cost))

    return UserCostResponse(
        user_id=user_id,
        llm_cost_usd=llm_cost,
        external_api_cost_usd=ext_cost,
        total_cost_usd=llm_cost + ext_cost,
        llm_call_count=llm_row.call_count,
        external_api_call_count=ext_row.call_count,
    )


# ---------------------------------------------------------------------------
# GET /admin/cost/daily?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/daily",
    response_model=DailyCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_daily_cost(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
) -> DailyCostResponse:
    """Return daily cost totals for the last N days (default 30, max 365).

    Results are ordered newest-first. Days with no activity are omitted.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # Daily LLM aggregation
    llm_day_col = func.date_trunc("day", LLMCall.called_at).label("day")
    llm_stmt = (
        select(
            llm_day_col,
            func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
            func.count(LLMCall.id).label("cnt"),
        )
        .where(LLMCall.called_at >= since)
        .group_by(llm_day_col)
    )
    llm_rows = (await db.execute(llm_stmt)).all()
    llm_by_day: dict[date, tuple[Decimal, int]] = {
        r.day.date(): (Decimal(str(r.cost)), r.cnt) for r in llm_rows
    }

    # Daily external API aggregation
    ext_day_col = func.date_trunc("day", ExternalAPICall.called_at).label("day")
    ext_stmt = (
        select(
            ext_day_col,
            func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
            func.count(ExternalAPICall.id).label("cnt"),
        )
        .where(ExternalAPICall.called_at >= since)
        .group_by(ext_day_col)
    )
    ext_rows = (await db.execute(ext_stmt)).all()
    ext_by_day: dict[date, tuple[Decimal, int]] = {
        r.day.date(): (Decimal(str(r.cost)), r.cnt) for r in ext_rows
    }

    # Merge on day — union of days seen in either table
    all_days = sorted(llm_by_day.keys() | ext_by_day.keys(), reverse=True)
    result_rows = []
    for day in all_days:
        llm_cost, llm_cnt = llm_by_day.get(day, (_ZERO, 0))
        ext_cost, ext_cnt = ext_by_day.get(day, (_ZERO, 0))
        result_rows.append(
            DailyCostRow(
                day=day,
                llm_cost_usd=llm_cost,
                external_api_cost_usd=ext_cost,
                total_cost_usd=llm_cost + ext_cost,
                llm_call_count=llm_cnt,
                external_api_call_count=ext_cnt,
            )
        )

    return DailyCostResponse(days_back=days, rows=result_rows)


# ---------------------------------------------------------------------------
# GET /admin/cost/per-phase?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/per-phase",
    response_model=PerPhaseCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_per_phase_cost(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
) -> PerPhaseCostResponse:
    """Return per-phase LLM cost breakdown for the last N days.

    Groups by LLMCall.phase. NULL phase (system-level calls not tied to a
    workflow phase) is included as phase=None. ExternalAPICall has no phase
    column, so this endpoint only queries LLMCall.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            LLMCall.phase,
            func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
            func.count(LLMCall.id).label("cnt"),
        )
        .where(LLMCall.called_at >= since)
        .group_by(LLMCall.phase)
        .order_by(func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).desc())
    )
    rows = (await db.execute(stmt)).all()

    return PerPhaseCostResponse(
        days_back=days,
        rows=[
            PhaseCostRow(
                phase=r.phase,
                llm_cost_usd=Decimal(str(r.cost)),
                call_count=r.cnt,
            )
            for r in rows
        ],
    )
