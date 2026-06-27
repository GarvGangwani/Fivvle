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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth.dependencies import get_current_admin_user
from app.cost.category import category_label
from app.cost.rollup import (
    TavilyCostSummary,
    aggregate_cost_by_category,
    aggregate_per_provider_costs,
    aggregate_per_user_costs,
    aggregate_top_experiments_by_cost,
    aggregate_user_experiment_cost_breakdown,
    compute_experiment_cost_stats,
    summarize_tavily_cost,
)
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.db.models.experiment import Experiment
from app.db.models.external_api_call import ExternalAPICall
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.admin import (
    CostInsightsResponse,
    CostSummaryResponse,
    DailyCostResponse,
    DailyCostRow,
    ExperimentCostResponse,
    ExperimentCostStatsRow,
    PerPhaseCostResponse,
    PerProductCostResponse,
    PerProviderCostResponse,
    PerUserCostResponse,
    PhaseCostRow,
    ProductCostRow,
    ProviderCostRow,
    TopExperimentCostRow,
    UserCostInsightRow,
    UserCostResponse,
    UserExperimentCostRow,
    UserExperimentsCostResponse,
    ExperimentPhaseCostRow,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_ZERO = Decimal("0")
_TAVILY = "tavily"


async def _build_cost_summary(
    db: AsyncSession,
    *,
    days: int,
    since: datetime,
    user_id: UUID | None = None,
) -> CostSummaryResponse:
    """Aggregate headline metrics for the admin dashboard."""
    exp_scope = None
    if user_id is not None:
        exp_scope = select(Experiment.id).where(Experiment.user_id == user_id).scalar_subquery()

    llm_filters = [LLMCall.called_at >= since]
    ext_filters = [ExternalAPICall.called_at >= since]
    if exp_scope is not None:
        llm_filters.append(LLMCall.experiment_id.in_(exp_scope))
        ext_filters.append(ExternalAPICall.experiment_id.in_(exp_scope))

    llm_stmt = select(
        func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
        func.count(LLMCall.id).label("cnt"),
    ).where(*llm_filters)
    ext_stmt = select(
        func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
        func.count(ExternalAPICall.id).label("cnt"),
    ).where(*ext_filters)

    llm_row = (await db.execute(llm_stmt)).one()
    ext_row = (await db.execute(ext_stmt)).one()

    llm_cost = Decimal(str(llm_row.cost))
    ext_cost = Decimal(str(ext_row.cost))

    settings = get_settings()
    if user_id is None:
        tavily_summary = await summarize_tavily_cost(
            db,
            since=since,
            usd_per_credit=settings.tavily_usd_per_credit,
        )
    else:
        tavily_filters = [
            ExternalAPICall.provider == _TAVILY,
            ExternalAPICall.called_at >= since,
            ExternalAPICall.experiment_id.in_(exp_scope),
        ]
        tavily_row = (
            await db.execute(
                select(
                    func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
                    func.coalesce(func.sum(ExternalAPICall.api_credits), 0).label("credits"),
                ).where(*tavily_filters)
            )
        ).one()
        tavily_summary = TavilyCostSummary(
            logged_cost_usd=Decimal(str(tavily_row.cost)),
            logged_credits=int(tavily_row.credits or 0),
            estimated_gap_cost_usd=_ZERO,
            estimated_gap_credits=0,
            unlogged_experiment_count=0,
        )

    per_user = await aggregate_per_user_costs(db, since=since)
    experiment_stats = await compute_experiment_cost_stats(
        db,
        since=since,
        user_id=user_id,
    )

    return CostSummaryResponse(
        days_back=days,
        total_cost_usd=llm_cost + ext_cost,
        llm_cost_usd=llm_cost,
        external_api_cost_usd=ext_cost,
        tavily_logged_cost_usd=tavily_summary.logged_cost_usd,
        tavily_estimated_gap_usd=tavily_summary.estimated_gap_cost_usd,
        tavily_total_cost_usd=tavily_summary.total_cost_usd,
        tavily_logged_credits=tavily_summary.logged_credits,
        tavily_estimated_gap_credits=tavily_summary.estimated_gap_credits,
        tavily_unlogged_experiment_count=tavily_summary.unlogged_experiment_count,
        llm_call_count=llm_row.cnt,
        external_api_call_count=ext_row.cnt,
        active_user_count=len(per_user),
        experiment_stats=ExperimentCostStatsRow(
            experiment_count=experiment_stats.experiment_count,
            avg_cost_usd=experiment_stats.avg_cost_usd,
            min_cost_usd=experiment_stats.min_cost_usd,
            max_cost_usd=experiment_stats.max_cost_usd,
            median_cost_usd=experiment_stats.median_cost_usd,
        ),
        tavily_usd_per_credit=settings.tavily_usd_per_credit,
    )


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

    product_totals = await aggregate_cost_by_category(
        db,
        experiment_id=experiment_id,
    )

    return ExperimentCostResponse(
        experiment_id=experiment_id,
        llm_cost_usd=llm_cost,
        external_api_cost_usd=ext_cost,
        total_cost_usd=llm_cost + ext_cost,
        llm_call_count=llm_row.call_count,
        external_api_call_count=ext_row.call_count,
        products=[
            ProductCostRow(
                cost_category=row.cost_category,
                label=category_label(row.cost_category),
                llm_cost_usd=row.llm_cost_usd,
                external_api_cost_usd=row.external_api_cost_usd,
                total_cost_usd=row.total_cost_usd,
                llm_call_count=row.llm_call_count,
                external_api_call_count=row.external_api_call_count,
            )
            for row in product_totals
        ],
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
    user_id: UUID | None = Query(default=None),
) -> DailyCostResponse:
    """Return daily cost totals for the last N days (default 30, max 365).

    Results are ordered newest-first. Days with no activity are omitted.

    When user_id is provided, scopes the query to that user's experiments only.
    Default (no user_id) returns global aggregation across all experiments.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # Optional user filter: scope to experiments owned by the given user_id
    user_exp_ids_subq = None
    if user_id is not None:
        user_exp_ids_subq = (
            select(Experiment.id).where(Experiment.user_id == user_id).scalar_subquery()
        )

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
    if user_exp_ids_subq is not None:
        llm_stmt = llm_stmt.where(LLMCall.experiment_id.in_(user_exp_ids_subq))
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
    if user_exp_ids_subq is not None:
        ext_stmt = ext_stmt.where(ExternalAPICall.experiment_id.in_(user_exp_ids_subq))
    ext_rows = (await db.execute(ext_stmt)).all()
    ext_by_day: dict[date, tuple[Decimal, int]] = {
        r.day.date(): (Decimal(str(r.cost)), r.cnt) for r in ext_rows
    }

    # Daily Tavily-only aggregation (subset of external API spend)
    tavily_day_col = func.date_trunc("day", ExternalAPICall.called_at).label("day")
    tavily_stmt = (
        select(
            tavily_day_col,
            func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
        )
        .where(ExternalAPICall.called_at >= since)
        .where(ExternalAPICall.provider == _TAVILY)
        .group_by(tavily_day_col)
    )
    if user_exp_ids_subq is not None:
        tavily_stmt = tavily_stmt.where(ExternalAPICall.experiment_id.in_(user_exp_ids_subq))
    tavily_rows = (await db.execute(tavily_stmt)).all()
    tavily_by_day: dict[date, Decimal] = {
        r.day.date(): Decimal(str(r.cost)) for r in tavily_rows
    }

    # Merge on day — union of days seen in either table
    all_days = sorted(llm_by_day.keys() | ext_by_day.keys(), reverse=True)
    result_rows = []
    for day in all_days:
        llm_cost, llm_cnt = llm_by_day.get(day, (_ZERO, 0))
        ext_cost, ext_cnt = ext_by_day.get(day, (_ZERO, 0))
        tavily_cost = tavily_by_day.get(day, _ZERO)
        result_rows.append(
            DailyCostRow(
                day=day,
                llm_cost_usd=llm_cost,
                external_api_cost_usd=ext_cost,
                tavily_cost_usd=tavily_cost,
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
    user_id: UUID | None = Query(default=None),
) -> PerPhaseCostResponse:
    """Return per-phase LLM cost breakdown for the last N days.

    Groups by LLMCall.phase. NULL phase (system-level calls not tied to a
    workflow phase) is included as phase=None. ExternalAPICall has no phase
    column, so this endpoint only queries LLMCall.

    When user_id is provided, scopes the query to that user's experiments only.
    Default (no user_id) returns global aggregation across all experiments.
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

    if user_id is not None:
        user_exp_ids_subq = (
            select(Experiment.id).where(Experiment.user_id == user_id).scalar_subquery()
        )
        stmt = stmt.where(LLMCall.experiment_id.in_(user_exp_ids_subq))

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


# ---------------------------------------------------------------------------
# GET /admin/cost/per-product?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/per-product",
    response_model=PerProductCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_per_product_cost(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
    user_id: UUID | None = Query(default=None),
) -> PerProductCostResponse:
    """Return per-product cost breakdown for the last N days.

    Groups LLMCall and ExternalAPICall rows by cost_category (refinement,
    cognitive_validation, landing_page, insight, platform).

    When user_id is provided, scopes the query to that user's experiments only.
    Default (no user_id) returns global aggregation across all experiments.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    product_totals = await aggregate_cost_by_category(
        db,
        user_id=user_id,
        since=since,
    )

    return PerProductCostResponse(
        days_back=days,
        rows=[
            ProductCostRow(
                cost_category=row.cost_category,
                label=category_label(row.cost_category),
                llm_cost_usd=row.llm_cost_usd,
                external_api_cost_usd=row.external_api_cost_usd,
                total_cost_usd=row.total_cost_usd,
                llm_call_count=row.llm_call_count,
                external_api_call_count=row.external_api_call_count,
            )
            for row in product_totals
        ],
    )


# ---------------------------------------------------------------------------
# GET /admin/cost/insights?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/insights",
    response_model=CostInsightsResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_cost_insights(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
) -> CostInsightsResponse:
    """Bundled admin dashboard metrics: summary, users, providers, phases, top experiments."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    summary = await _build_cost_summary(db, days=days, since=since)
    per_user_rows = await aggregate_per_user_costs(db, since=since)
    per_provider_rows = await aggregate_per_provider_costs(db, since=since)
    top_experiments = await aggregate_top_experiments_by_cost(db, since=since)

    phase_stmt = (
        select(
            LLMCall.phase,
            func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
            func.count(LLMCall.id).label("cnt"),
        )
        .where(LLMCall.called_at >= since)
        .group_by(LLMCall.phase)
        .order_by(func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).desc())
    )
    phase_rows = (await db.execute(phase_stmt)).all()

    return CostInsightsResponse(
        days_back=days,
        summary=summary,
        per_user=[
            UserCostInsightRow(
                user_id=row.user_id,
                email=row.email,
                name=row.name,
                experiment_count=row.experiment_count,
                llm_cost_usd=row.llm_cost_usd,
                external_api_cost_usd=row.external_api_cost_usd,
                total_cost_usd=row.total_cost_usd,
                llm_call_count=row.llm_call_count,
                external_api_call_count=row.external_api_call_count,
            )
            for row in per_user_rows
        ],
        per_provider=[
            ProviderCostRow(
                provider=row.provider,
                source=row.source,
                cost_usd=row.cost_usd,
                call_count=row.call_count,
            )
            for row in per_provider_rows
        ],
        per_phase=[
            PhaseCostRow(
                phase=r.phase,
                llm_cost_usd=Decimal(str(r.cost)),
                call_count=r.cnt,
            )
            for r in phase_rows
        ],
        top_experiments=[
            TopExperimentCostRow(
                experiment_id=row.experiment_id,
                label=row.label,
                total_cost_usd=row.total_cost_usd,
                llm_cost_usd=row.llm_cost_usd,
                external_api_cost_usd=row.external_api_cost_usd,
            )
            for row in top_experiments
        ],
    )


# ---------------------------------------------------------------------------
# GET /admin/cost/per-user?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/per-user",
    response_model=PerUserCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_per_user_cost(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
) -> PerUserCostResponse:
    """Return per-user spend for the last N days."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    rows = await aggregate_per_user_costs(db, since=since)
    return PerUserCostResponse(
        days_back=days,
        rows=[
            UserCostInsightRow(
                user_id=row.user_id,
                email=row.email,
                name=row.name,
                experiment_count=row.experiment_count,
                llm_cost_usd=row.llm_cost_usd,
                external_api_cost_usd=row.external_api_cost_usd,
                total_cost_usd=row.total_cost_usd,
                llm_call_count=row.llm_call_count,
                external_api_call_count=row.external_api_call_count,
            )
            for row in rows
        ],
    )


# ---------------------------------------------------------------------------
# GET /admin/cost/per-provider?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/per-provider",
    response_model=PerProviderCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_per_provider_cost(
    request: Request,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
    user_id: UUID | None = Query(default=None),
) -> PerProviderCostResponse:
    """Return spend grouped by provider (anthropic, tavily, reddit, etc.)."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    rows = await aggregate_per_provider_costs(db, since=since, user_id=user_id)
    return PerProviderCostResponse(
        days_back=days,
        rows=[
            ProviderCostRow(
                provider=row.provider,
                source=row.source,
                cost_usd=row.cost_usd,
                call_count=row.call_count,
            )
            for row in rows
        ],
    )


# ---------------------------------------------------------------------------
# GET /admin/cost/user/{user_id}/experiments?days=30
# ---------------------------------------------------------------------------


@router.get(
    "/cost/user/{user_id}/experiments",
    response_model=UserExperimentsCostResponse,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_user_experiment_costs(
    request: Request,
    user_id: UUID,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
    days: int = Query(default=30, ge=1, le=365),
) -> UserExperimentsCostResponse:
    """Return each project for a user with per-phase LLM and external API costs."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    user_exists = (
        await db.execute(select(User.id).where(User.id == user_id))
    ).scalar_one_or_none()
    if user_exists is None:
        raise HTTPException(status_code=404, detail="User not found")

    email, name, experiments = await aggregate_user_experiment_cost_breakdown(
        db,
        user_id,
        since=since,
    )

    return UserExperimentsCostResponse(
        user_id=user_id,
        email=email,
        name=name,
        days_back=days,
        experiments=[
            UserExperimentCostRow(
                experiment_id=row.experiment_id,
                label=row.label,
                name=row.name,
                status=row.status,
                total_cost_usd=row.total_cost_usd,
                llm_cost_usd=row.llm_cost_usd,
                external_api_cost_usd=row.external_api_cost_usd,
                phases=[
                    ExperimentPhaseCostRow(
                        phase=phase.phase,
                        label=phase.label,
                        source=phase.source,
                        cost_usd=phase.cost_usd,
                        call_count=phase.call_count,
                    )
                    for phase in row.phases
                ],
            )
            for row in experiments
        ],
    )
