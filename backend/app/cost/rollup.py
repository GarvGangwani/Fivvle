"""Shared SQL aggregation helpers for admin cost rollups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost.category import COST_CATEGORY_ORDER, CostCategory, category_label
from app.cost.tavily import estimate_research_tavily_credits, tavily_cost_usd
from app.db.models.experiment import Experiment
from app.db.models.external_api_call import ExternalAPICall
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport

_ZERO = Decimal("0")


@dataclass(frozen=True)
class CategoryCostTotals:
    cost_category: str
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int

    @property
    def total_cost_usd(self) -> Decimal:
        return self.llm_cost_usd + self.external_api_cost_usd


async def aggregate_cost_by_category(
    db: AsyncSession,
    *,
    experiment_id: UUID | None = None,
    user_id: UUID | None = None,
    since: datetime | None = None,
) -> list[CategoryCostTotals]:
    """Roll up LLM + external API spend grouped by cost_category.

    Exactly one of ``experiment_id`` or global scope applies. When ``user_id``
    is set, restricts to that user's experiments (ignored if experiment_id set).
    """
    llm_filters = []
    ext_filters = []

    if experiment_id is not None:
        llm_filters.append(LLMCall.experiment_id == experiment_id)
        ext_filters.append(ExternalAPICall.experiment_id == experiment_id)
    elif user_id is not None:
        exp_ids = select(Experiment.id).where(Experiment.user_id == user_id).scalar_subquery()
        llm_filters.append(LLMCall.experiment_id.in_(exp_ids))
        ext_filters.append(ExternalAPICall.experiment_id.in_(exp_ids))

    if since is not None:
        llm_filters.append(LLMCall.called_at >= since)
        ext_filters.append(ExternalAPICall.called_at >= since)

    llm_stmt = select(
        LLMCall.cost_category,
        func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
        func.count(LLMCall.id).label("cnt"),
    ).group_by(LLMCall.cost_category)
    for clause in llm_filters:
        llm_stmt = llm_stmt.where(clause)

    ext_stmt = select(
        ExternalAPICall.cost_category,
        func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
        func.count(ExternalAPICall.id).label("cnt"),
    ).group_by(ExternalAPICall.cost_category)
    for clause in ext_filters:
        ext_stmt = ext_stmt.where(clause)

    llm_rows = (await db.execute(llm_stmt)).all()
    ext_rows = (await db.execute(ext_stmt)).all()

    merged: dict[str, CategoryCostTotals] = {}

    for row in llm_rows:
        cat = row.cost_category or CostCategory.PLATFORM.value
        merged[cat] = CategoryCostTotals(
            cost_category=cat,
            llm_cost_usd=Decimal(str(row.cost)),
            external_api_cost_usd=_ZERO,
            llm_call_count=row.cnt,
            external_api_call_count=0,
        )

    for row in ext_rows:
        cat = row.cost_category or CostCategory.PLATFORM.value
        existing = merged.get(cat)
        ext_cost = Decimal(str(row.cost))
        if existing is None:
            merged[cat] = CategoryCostTotals(
                cost_category=cat,
                llm_cost_usd=_ZERO,
                external_api_cost_usd=ext_cost,
                llm_call_count=0,
                external_api_call_count=row.cnt,
            )
        else:
            merged[cat] = CategoryCostTotals(
                cost_category=cat,
                llm_cost_usd=existing.llm_cost_usd,
                external_api_cost_usd=existing.external_api_cost_usd + ext_cost,
                llm_call_count=existing.llm_call_count,
                external_api_call_count=existing.external_api_call_count + row.cnt,
            )

    def sort_key(item: CategoryCostTotals) -> tuple[int, str]:
        try:
            idx = COST_CATEGORY_ORDER.index(CostCategory(item.cost_category))
        except ValueError:
            idx = len(COST_CATEGORY_ORDER)
        return (idx, item.cost_category)

    return sorted(merged.values(), key=sort_key)


def category_totals_to_product_rows(
    totals: list[CategoryCostTotals],
) -> list[dict[str, object]]:
    """Serialize category totals for Pydantic response models."""
    return [
        {
            "cost_category": row.cost_category,
            "label": category_label(row.cost_category),
            "llm_cost_usd": row.llm_cost_usd,
            "external_api_cost_usd": row.external_api_cost_usd,
            "total_cost_usd": row.total_cost_usd,
            "llm_call_count": row.llm_call_count,
            "external_api_call_count": row.external_api_call_count,
        }
        for row in totals
    ]


@dataclass(frozen=True)
class UserCostTotals:
    user_id: UUID
    email: str
    name: str | None
    experiment_count: int
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    llm_call_count: int
    external_api_call_count: int

    @property
    def total_cost_usd(self) -> Decimal:
        return self.llm_cost_usd + self.external_api_cost_usd


@dataclass(frozen=True)
class ProviderCostTotals:
    provider: str
    source: str
    cost_usd: Decimal
    call_count: int


@dataclass(frozen=True)
class ExperimentCostStats:
    experiment_count: int
    avg_cost_usd: Decimal
    min_cost_usd: Decimal
    max_cost_usd: Decimal
    median_cost_usd: Decimal


@dataclass(frozen=True)
class TopExperimentCost:
    experiment_id: UUID
    label: str
    total_cost_usd: Decimal
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal


def _experiment_scope_subq(user_id: UUID | None):
    if user_id is None:
        return None
    return select(Experiment.id).where(Experiment.user_id == user_id).scalar_subquery()


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return _ZERO
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")


async def _experiment_cost_components(
    db: AsyncSession,
    *,
    since: datetime | None = None,
    user_id: UUID | None = None,
) -> dict[UUID, tuple[Decimal, Decimal]]:
    """Map experiment_id -> (llm_cost, external_api_cost)."""
    llm_filters = [LLMCall.experiment_id.is_not(None)]
    ext_filters = [ExternalAPICall.experiment_id.is_not(None)]

    exp_scope = _experiment_scope_subq(user_id)
    if exp_scope is not None:
        llm_filters.append(LLMCall.experiment_id.in_(exp_scope))
        ext_filters.append(ExternalAPICall.experiment_id.in_(exp_scope))

    if since is not None:
        llm_filters.append(LLMCall.called_at >= since)
        ext_filters.append(ExternalAPICall.called_at >= since)

    llm_stmt = (
        select(
            LLMCall.experiment_id,
            func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
        )
        .where(*llm_filters)
        .group_by(LLMCall.experiment_id)
    )
    ext_stmt = (
        select(
            ExternalAPICall.experiment_id,
            func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
        )
        .where(*ext_filters)
        .group_by(ExternalAPICall.experiment_id)
    )

    llm_rows = (await db.execute(llm_stmt)).all()
    ext_rows = (await db.execute(ext_stmt)).all()

    merged: dict[UUID, tuple[Decimal, Decimal]] = {}
    for row in llm_rows:
        if row.experiment_id is None:
            continue
        merged[row.experiment_id] = (Decimal(str(row.cost)), _ZERO)

    for row in ext_rows:
        if row.experiment_id is None:
            continue
        ext_cost = Decimal(str(row.cost))
        existing = merged.get(row.experiment_id)
        if existing is None:
            merged[row.experiment_id] = (_ZERO, ext_cost)
        else:
            merged[row.experiment_id] = (existing[0], existing[1] + ext_cost)

    return merged


async def compute_experiment_cost_stats(
    db: AsyncSession,
    *,
    since: datetime | None = None,
    user_id: UUID | None = None,
) -> ExperimentCostStats:
    """Min/avg/max/median cost per experiment with recorded spend."""
    components = await _experiment_cost_components(db, since=since, user_id=user_id)
    totals = [llm + ext for llm, ext in components.values() if llm + ext > _ZERO]
    if not totals:
        return ExperimentCostStats(
            experiment_count=0,
            avg_cost_usd=_ZERO,
            min_cost_usd=_ZERO,
            max_cost_usd=_ZERO,
            median_cost_usd=_ZERO,
        )

    total_sum = sum(totals, _ZERO)
    return ExperimentCostStats(
        experiment_count=len(totals),
        avg_cost_usd=total_sum / Decimal(len(totals)),
        min_cost_usd=min(totals),
        max_cost_usd=max(totals),
        median_cost_usd=_median(totals),
    )


async def aggregate_top_experiments_by_cost(
    db: AsyncSession,
    *,
    since: datetime | None = None,
    user_id: UUID | None = None,
    limit: int = 8,
) -> list[TopExperimentCost]:
    """Return the most expensive experiments in the period."""
    components = await _experiment_cost_components(db, since=since, user_id=user_id)
    ranked = sorted(
        (
            (exp_id, llm, ext, llm + ext)
            for exp_id, (llm, ext) in components.items()
            if llm + ext > _ZERO
        ),
        key=lambda item: item[3],
        reverse=True,
    )[:limit]

    if not ranked:
        return []

    exp_ids = [item[0] for item in ranked]
    exp_rows = (
        await db.execute(select(Experiment).where(Experiment.id.in_(exp_ids)))
    ).scalars().all()
    labels = {
        exp.id: (exp.name or exp.raw_idea[:60] + ("…" if len(exp.raw_idea) > 60 else ""))
        for exp in exp_rows
    }

    return [
        TopExperimentCost(
            experiment_id=exp_id,
            label=labels.get(exp_id, str(exp_id)),
            total_cost_usd=total,
            llm_cost_usd=llm,
            external_api_cost_usd=ext,
        )
        for exp_id, llm, ext, total in ranked
    ]


async def aggregate_per_user_costs(
    db: AsyncSession,
    *,
    since: datetime | None = None,
) -> list[UserCostTotals]:
    """Roll up spend by user across their experiments."""
    llm_filters = [LLMCall.experiment_id.is_not(None)]
    ext_filters = [ExternalAPICall.experiment_id.is_not(None)]
    if since is not None:
        llm_filters.append(LLMCall.called_at >= since)
        ext_filters.append(ExternalAPICall.called_at >= since)

    llm_stmt = (
        select(
            Experiment.user_id,
            func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
            func.count(LLMCall.id).label("cnt"),
            func.count(func.distinct(LLMCall.experiment_id)).label("exp_cnt"),
        )
        .join(Experiment, Experiment.id == LLMCall.experiment_id)
        .where(*llm_filters)
        .group_by(Experiment.user_id)
    )
    ext_stmt = (
        select(
            Experiment.user_id,
            func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
            func.count(ExternalAPICall.id).label("cnt"),
            func.count(func.distinct(ExternalAPICall.experiment_id)).label("exp_cnt"),
        )
        .join(Experiment, Experiment.id == ExternalAPICall.experiment_id)
        .where(*ext_filters)
        .group_by(Experiment.user_id)
    )

    llm_rows = (await db.execute(llm_stmt)).all()
    ext_rows = (await db.execute(ext_stmt)).all()

    merged: dict[UUID, dict[str, Decimal | int]] = {}
    for row in llm_rows:
        merged[row.user_id] = {
            "llm_cost": Decimal(str(row.cost)),
            "ext_cost": _ZERO,
            "llm_cnt": row.cnt,
            "ext_cnt": 0,
            "exp_cnt": row.exp_cnt,
        }

    for row in ext_rows:
        existing = merged.get(row.user_id)
        ext_cost = Decimal(str(row.cost))
        if existing is None:
            merged[row.user_id] = {
                "llm_cost": _ZERO,
                "ext_cost": ext_cost,
                "llm_cnt": 0,
                "ext_cnt": row.cnt,
                "exp_cnt": row.exp_cnt,
            }
        else:
            existing["ext_cost"] = Decimal(str(existing["ext_cost"])) + ext_cost
            existing["ext_cnt"] = int(existing["ext_cnt"]) + row.cnt
            existing["exp_cnt"] = max(int(existing["exp_cnt"]), row.exp_cnt)

    if not merged:
        return []

    user_rows = (
        await db.execute(select(User).where(User.id.in_(merged.keys())))
    ).scalars().all()
    users_by_id = {user.id: user for user in user_rows}

    results = [
        UserCostTotals(
            user_id=user_id,
            email=users_by_id[user_id].email if user_id in users_by_id else "",
            name=users_by_id[user_id].name if user_id in users_by_id else None,
            experiment_count=int(data["exp_cnt"]),
            llm_cost_usd=Decimal(str(data["llm_cost"])),
            external_api_cost_usd=Decimal(str(data["ext_cost"])),
            llm_call_count=int(data["llm_cnt"]),
            external_api_call_count=int(data["ext_cnt"]),
        )
        for user_id, data in merged.items()
    ]
    return sorted(results, key=lambda row: row.total_cost_usd, reverse=True)


async def aggregate_per_provider_costs(
    db: AsyncSession,
    *,
    since: datetime | None = None,
    user_id: UUID | None = None,
) -> list[ProviderCostTotals]:
    """Roll up LLM and external API spend by provider slug."""
    llm_filters = []
    ext_filters = []

    exp_scope = _experiment_scope_subq(user_id)
    if exp_scope is not None:
        llm_filters.append(LLMCall.experiment_id.in_(exp_scope))
        ext_filters.append(ExternalAPICall.experiment_id.in_(exp_scope))

    if since is not None:
        llm_filters.append(LLMCall.called_at >= since)
        ext_filters.append(ExternalAPICall.called_at >= since)

    llm_stmt = select(
        LLMCall.provider,
        func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
        func.count(LLMCall.id).label("cnt"),
    ).group_by(LLMCall.provider)
    for clause in llm_filters:
        llm_stmt = llm_stmt.where(clause)

    ext_stmt = select(
        ExternalAPICall.provider,
        func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
        func.count(ExternalAPICall.id).label("cnt"),
    ).group_by(ExternalAPICall.provider)
    for clause in ext_filters:
        ext_stmt = ext_stmt.where(clause)

    llm_rows = (await db.execute(llm_stmt)).all()
    ext_rows = (await db.execute(ext_stmt)).all()

    results = [
        ProviderCostTotals(
            provider=row.provider,
            source="llm",
            cost_usd=Decimal(str(row.cost)),
            call_count=row.cnt,
        )
        for row in llm_rows
        if row.cnt > 0
    ]
    results.extend(
        ProviderCostTotals(
            provider=row.provider,
            source="external",
            cost_usd=Decimal(str(row.cost)),
            call_count=row.cnt,
        )
        for row in ext_rows
        if row.cnt > 0
    )
    return sorted(results, key=lambda row: row.cost_usd, reverse=True)


@dataclass(frozen=True)
class TavilyCostSummary:
    logged_cost_usd: Decimal
    logged_credits: int
    estimated_gap_cost_usd: Decimal
    estimated_gap_credits: int
    unlogged_experiment_count: int

    @property
    def total_cost_usd(self) -> Decimal:
        return self.logged_cost_usd + self.estimated_gap_cost_usd

    @property
    def total_credits(self) -> int:
        return self.logged_credits + self.estimated_gap_credits


async def summarize_tavily_cost(
    db: AsyncSession,
    *,
    since: datetime | None = None,
    usd_per_credit: Decimal,
) -> TavilyCostSummary:
    """Logged Tavily spend plus estimates for research with no audit rows."""
    tavily_filters = [ExternalAPICall.provider == "tavily"]
    if since is not None:
        tavily_filters.append(ExternalAPICall.called_at >= since)

    logged_stmt = select(
        func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
    ).where(*tavily_filters)
    logged_row = (await db.execute(logged_stmt)).one()
    logged_cost = Decimal(str(logged_row.cost))

    credit_rows = (
        await db.execute(
            select(ExternalAPICall.cost_usd, ExternalAPICall.api_credits).where(
                *tavily_filters
            )
        )
    ).all()
    logged_credits = 0
    for cost, credits in credit_rows:
        if credits is not None and credits > 0:
            logged_credits += int(credits)
        elif cost and Decimal(str(cost)) > _ZERO:
            logged_credits += int(Decimal(str(cost)) / usd_per_credit)

    report_filters = []
    if since is not None:
        report_filters.append(ValidationReport.generated_at >= since)

    reports_stmt = select(
        ValidationReport.experiment_id,
        ValidationReport.reflection_loops_used,
    )
    for clause in report_filters:
        reports_stmt = reports_stmt.where(clause)

    reports = (await db.execute(reports_stmt)).all()
    if not reports:
        return TavilyCostSummary(
            logged_cost_usd=logged_cost,
            logged_credits=logged_credits,
            estimated_gap_cost_usd=_ZERO,
            estimated_gap_credits=0,
            unlogged_experiment_count=0,
        )

    exp_ids = [row.experiment_id for row in reports]
    logged_by_exp_stmt = (
        select(
            ExternalAPICall.experiment_id,
            func.count(ExternalAPICall.id).label("cnt"),
        )
        .where(
            ExternalAPICall.provider == "tavily",
            ExternalAPICall.experiment_id.in_(exp_ids),
        )
        .group_by(ExternalAPICall.experiment_id)
    )
    if since is not None:
        logged_by_exp_stmt = logged_by_exp_stmt.where(
            ExternalAPICall.called_at >= since
        )
    logged_by_exp = {
        row.experiment_id: row.cnt
        for row in (await db.execute(logged_by_exp_stmt)).all()
    }

    gap_credits = 0
    unlogged_count = 0
    for row in reports:
        if logged_by_exp.get(row.experiment_id, 0) > 0:
            continue
        unlogged_count += 1
        gap_credits += estimate_research_tavily_credits(
            reflection_loops_used=row.reflection_loops_used or 0,
        )

    gap_cost = tavily_cost_usd(gap_credits, usd_per_credit) if gap_credits else _ZERO

    return TavilyCostSummary(
        logged_cost_usd=logged_cost,
        logged_credits=logged_credits,
        estimated_gap_cost_usd=gap_cost,
        estimated_gap_credits=gap_credits,
        unlogged_experiment_count=unlogged_count,
    )


_EXTERNAL_PROVIDER_LABELS: dict[str, str] = {
    "tavily": "Tavily search",
    "pytrends": "Google Trends",
    "reddit": "Reddit research",
    "ipwho": "IP geolocation",
}

_LLM_PHASE_LABELS: dict[str, str] = {
    "refinement": "Refinement",
    "refinement_chat": "Refinement chat",
    "chat_discussion": "Chat discussion",
    "chat_normal": "Chat",
    "chat_attachment": "Chat attachment",
    "planner": "Research — Planner",
    "reader": "Research — Reader",
    "reflector": "Research — Reflector",
    "synthesizer": "Research — Synthesizer",
    "landing_page": "Landing page",
    "insight": "Insight report",
}

_PHASE_SORT_ORDER: tuple[str, ...] = (
    "refinement",
    "refinement_chat",
    "chat_discussion",
    "chat_normal",
    "chat_attachment",
    "planner",
    "tavily",
    "pytrends",
    "reddit",
    "reader",
    "reflector",
    "synthesizer",
    "landing_page",
    "insight",
    "ipwho",
    "__unscoped__",
)


def workflow_phase_label(phase_key: str, source: str) -> str:
    if source == "external":
        return _EXTERNAL_PROVIDER_LABELS.get(phase_key, phase_key)
    if phase_key == "__unscoped__":
        return "Unscoped"
    return _LLM_PHASE_LABELS.get(
        phase_key,
        phase_key.replace("_", " ").title(),
    )


def _phase_sort_key(phase_key: str) -> tuple[int, str]:
    try:
        idx = _PHASE_SORT_ORDER.index(phase_key)
    except ValueError:
        idx = len(_PHASE_SORT_ORDER)
    return (idx, phase_key)


@dataclass(frozen=True)
class ExperimentPhaseCost:
    phase: str
    label: str
    source: str
    cost_usd: Decimal
    call_count: int


@dataclass(frozen=True)
class UserExperimentCostBreakdown:
    experiment_id: UUID
    label: str
    name: str | None
    status: str
    total_cost_usd: Decimal
    llm_cost_usd: Decimal
    external_api_cost_usd: Decimal
    phases: list[ExperimentPhaseCost]


async def aggregate_user_experiment_cost_breakdown(
    db: AsyncSession,
    user_id: UUID,
    *,
    since: datetime | None = None,
) -> tuple[str, str | None, list[UserExperimentCostBreakdown]]:
    """Per-project cost with workflow phase breakdown for one user."""
    user_row = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user_row is None:
        return "", None, []

    experiments = (
        await db.execute(
            select(Experiment)
            .where(Experiment.user_id == user_id)
            .order_by(Experiment.created_at.desc())
        )
    ).scalars().all()

    if not experiments:
        return user_row.email, user_row.name, []

    exp_by_id = {exp.id: exp for exp in experiments}
    exp_ids = list(exp_by_id.keys())

    llm_filters = [
        LLMCall.experiment_id.in_(exp_ids),
        LLMCall.experiment_id.is_not(None),
    ]
    ext_filters = [
        ExternalAPICall.experiment_id.in_(exp_ids),
        ExternalAPICall.experiment_id.is_not(None),
    ]
    if since is not None:
        llm_filters.append(LLMCall.called_at >= since)
        ext_filters.append(ExternalAPICall.called_at >= since)

    llm_rows = (
        await db.execute(
            select(
                LLMCall.experiment_id,
                LLMCall.phase,
                func.coalesce(func.sum(LLMCall.cost_usd), _ZERO).label("cost"),
                func.count(LLMCall.id).label("cnt"),
            )
            .where(*llm_filters)
            .group_by(LLMCall.experiment_id, LLMCall.phase)
        )
    ).all()

    ext_rows = (
        await db.execute(
            select(
                ExternalAPICall.experiment_id,
                ExternalAPICall.provider,
                func.coalesce(func.sum(ExternalAPICall.cost_usd), _ZERO).label("cost"),
                func.count(ExternalAPICall.id).label("cnt"),
            )
            .where(*ext_filters)
            .group_by(ExternalAPICall.experiment_id, ExternalAPICall.provider)
        )
    ).all()

    phases_by_exp: dict[UUID, list[ExperimentPhaseCost]] = {eid: [] for eid in exp_ids}
    llm_totals: dict[UUID, Decimal] = {eid: _ZERO for eid in exp_ids}
    ext_totals: dict[UUID, Decimal] = {eid: _ZERO for eid in exp_ids}

    for row in llm_rows:
        if row.experiment_id is None:
            continue
        cost = Decimal(str(row.cost))
        llm_totals[row.experiment_id] = llm_totals[row.experiment_id] + cost
        phase_key = row.phase if row.phase else "__unscoped__"
        phases_by_exp[row.experiment_id].append(
            ExperimentPhaseCost(
                phase=phase_key,
                label=workflow_phase_label(phase_key, "llm"),
                source="llm",
                cost_usd=cost,
                call_count=row.cnt,
            )
        )

    for row in ext_rows:
        if row.experiment_id is None:
            continue
        cost = Decimal(str(row.cost))
        ext_totals[row.experiment_id] = ext_totals[row.experiment_id] + cost
        phases_by_exp[row.experiment_id].append(
            ExperimentPhaseCost(
                phase=row.provider,
                label=workflow_phase_label(row.provider, "external"),
                source="external",
                cost_usd=cost,
                call_count=row.cnt,
            )
        )

    results: list[UserExperimentCostBreakdown] = []
    for exp in experiments:
        llm_cost = llm_totals[exp.id]
        ext_cost = ext_totals[exp.id]
        total = llm_cost + ext_cost
        if since is not None and total <= _ZERO:
            continue

        sorted_phases = sorted(
            phases_by_exp[exp.id],
            key=lambda p: _phase_sort_key(p.phase),
        )
        label = exp.name or (
            exp.raw_idea[:60] + ("…" if len(exp.raw_idea) > 60 else "")
        )
        results.append(
            UserExperimentCostBreakdown(
                experiment_id=exp.id,
                label=label,
                name=exp.name,
                status=str(exp.status.value if hasattr(exp.status, "value") else exp.status),
                total_cost_usd=total,
                llm_cost_usd=llm_cost,
                external_api_cost_usd=ext_cost,
                phases=sorted_phases,
            )
        )

    return user_row.email, user_row.name, results
