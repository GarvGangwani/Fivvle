"""Aggregate LLM + external API spend by experiment for cost-ledger reconciliation.

Queries Postgres only; prints aggregate metrics (no prompts, no PII). Run from
`D:\\Fivvle\\backend`:

    .venv\\Scripts\\python.exe scripts/cost_ledger_audit.py

Expects `DATABASE_URL` in `backend/.env` (loaded explicitly below).
"""

from __future__ import annotations

import asyncio
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

from app.config import get_settings  # noqa: E402
from app.db.models.external_api_call import ExternalAPICall  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.db.session import dispose_engine, get_sessionmaker, init_engine  # noqa: E402


def _f(d: Decimal | None) -> float:
    return float(d or 0)


def _pct_linear(sorted_vals: list[float], pct: float) -> float | None:
    n = len(sorted_vals)
    if n == 0:
        return None
    idx = pct * (n - 1) / 100.0
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(sorted_vals[lo])
    return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])


@dataclass
class ExpAgg:
    experiment_id: UUID | None
    anthropic_usd: float
    llm_all_usd: float
    n_llm: int
    llm_min_at: datetime | None
    llm_max_at: datetime | None
    ext_usd: float
    n_ext: int
    ext_min_at: datetime | None
    ext_max_at: datetime | None
    prompt_names: frozenset[str]
    phases: frozenset[str]
    llm_providers: frozenset[str]
    ext_providers: frozenset[str]

    @property
    def time_min(self) -> datetime | None:
        xs = [x for x in (self.llm_min_at, self.ext_min_at) if x is not None]
        return min(xs) if xs else None

    @property
    def time_max(self) -> datetime | None:
        xs = [x for x in (self.llm_max_at, self.ext_max_at) if x is not None]
        return max(xs) if xs else None

    @property
    def combined_anthropic_plus_ext(self) -> float:
        return self.anthropic_usd + self.ext_usd


async def _load_llm_meta(session: AsyncSession) -> dict[UUID | None, dict[str, set]]:
    out: dict[UUID | None, dict[str, set]] = defaultdict(
        lambda: {"prompts": set(), "phases": set(), "llm_providers": set()}
    )
    rs = await session.execute(
        select(LLMCall.experiment_id, LLMCall.prompt_name, LLMCall.phase, LLMCall.provider)
    )
    for eid, pn, ph, prov in rs:
        b = out[eid]
        b["prompts"].add(pn)
        if ph:
            b["phases"].add(ph)
        b["llm_providers"].add(prov)
    return out


async def _load_ext_meta(session: AsyncSession) -> dict[UUID | None, set[str]]:
    out: dict[UUID | None, set[str]] = defaultdict(set)
    rs = await session.execute(
        select(ExternalAPICall.experiment_id, ExternalAPICall.provider)
    )
    for eid, prov in rs:
        out[eid].add(prov)
    return out


async def main() -> None:
    init_engine(get_settings())
    Session = get_sessionmaker()
    try:
        async with Session() as session:
            anthropic_case = case(
                (func.lower(LLMCall.provider) == literal("anthropic"), LLMCall.cost_usd),
                else_=0,
            )
            llm_stmt = (
                select(
                    LLMCall.experiment_id,
                    func.sum(anthropic_case).label("anthropic_usd"),
                    func.sum(LLMCall.cost_usd).label("llm_all_usd"),
                    func.count().label("n_llm"),
                    func.min(LLMCall.called_at).label("llm_min_at"),
                    func.max(LLMCall.called_at).label("llm_max_at"),
                )
                .group_by(LLMCall.experiment_id)
            )
            llm_rows = (await session.execute(llm_stmt)).all()

            ext_stmt = (
                select(
                    ExternalAPICall.experiment_id,
                    func.sum(ExternalAPICall.cost_usd).label("ext_usd"),
                    func.count().label("n_ext"),
                    func.min(ExternalAPICall.called_at).label("ext_min_at"),
                    func.max(ExternalAPICall.called_at).label("ext_max_at"),
                )
                .group_by(ExternalAPICall.experiment_id)
            )
            ext_rows = (await session.execute(ext_stmt)).all()

            llm_meta = await _load_llm_meta(session)
            ext_meta = await _load_ext_meta(session)

            llm_by_eid: dict[UUID | None, tuple] = {r[0]: tuple(r[1:]) for r in llm_rows}
            ext_by_eid: dict[UUID | None, tuple] = {r[0]: tuple(r[1:]) for r in ext_rows}
            all_eids = sorted(
                set(llm_by_eid) | set(ext_by_eid),
                key=lambda x: (x is None, str(x) if x else ""),
            )

            aggs: list[ExpAgg] = []
            for eid in all_eids:
                lm = llm_by_eid.get(eid)
                ex = ext_by_eid.get(eid)
                meta_l = llm_meta.get(eid, {"prompts": set(), "phases": set(), "llm_providers": set()})
                prompts = frozenset(meta_l["prompts"])
                phases = frozenset(meta_l["phases"])
                llm_providers = frozenset(meta_l["llm_providers"])
                ext_providers = frozenset(ext_meta.get(eid, set()))

                if lm:
                    ant, all_llm, n_llm, t0, t1 = (
                        _f(lm[0]),
                        _f(lm[1]),
                        int(lm[2]),
                        lm[3],
                        lm[4],
                    )
                else:
                    ant, all_llm, n_llm, t0, t1 = 0.0, 0.0, 0, None, None

                if ex:
                    ext_u, n_ext, e0, e1 = _f(ex[0]), int(ex[1]), ex[2], ex[3]
                else:
                    ext_u, n_ext, e0, e1 = 0.0, 0, None, None

                aggs.append(
                    ExpAgg(
                        experiment_id=eid,
                        anthropic_usd=ant,
                        llm_all_usd=all_llm,
                        n_llm=n_llm,
                        llm_min_at=t0,
                        llm_max_at=t1,
                        ext_usd=ext_u,
                        n_ext=n_ext,
                        ext_min_at=e0,
                        ext_max_at=e1,
                        prompt_names=prompts,
                        phases=phases,
                        llm_providers=llm_providers,
                        ext_providers=ext_providers,
                    )
                )

            aggs.sort(
                key=lambda a: (
                    (a.time_max or datetime.min.replace(tzinfo=UTC)),
                    str(a.experiment_id) if a.experiment_id else "",
                ),
                reverse=True,
            )

            lifetime_anthropic = sum(a.anthropic_usd for a in aggs)
            lifetime_ext = sum(a.ext_usd for a in aggs)
            lifetime_llm_all = sum(a.llm_all_usd for a in aggs)
            n_distinct_experiments = sum(1 for a in aggs if a.experiment_id is not None)
            has_null_bucket = any(a.experiment_id is None for a in aggs)

            print("=== Cost ledger audit (Postgres aggregates) ===")
            print()
            print("--- Top-level summary ---")
            print(f"Lifetime Anthropic (LLM, provider=anthropic): ${lifetime_anthropic:.6f}")
            print(f"Lifetime all LLM providers:                ${lifetime_llm_all:.6f}")
            print(f"Lifetime external API:                     ${lifetime_ext:.6f}")
            print(
                f"Lifetime combined (Anthropic LLM + ext):   ${lifetime_anthropic + lifetime_ext:.6f}"
            )
            print(f"Distinct experiments (non-null id):       {n_distinct_experiments}")
            print(f"Rows with NULL experiment_id bucket:        {'yes' if has_null_bucket else 'no'}")
            print()

            print("--- Per experiment (sorted by max(call time) DESC) ---")
            for a in aggs:
                eid_s = str(a.experiment_id) if a.experiment_id else "NULL"
                tmn = a.time_min.isoformat() if a.time_min else "-"
                tmx = a.time_max.isoformat() if a.time_max else "-"
                prompts_s = ", ".join(sorted(a.prompt_names)) if a.prompt_names else "-"
                phases_s = ", ".join(sorted(a.phases)) if a.phases else "-"
                lp = ", ".join(sorted(a.llm_providers)) if a.llm_providers else "-"
                ep = ", ".join(sorted(a.ext_providers)) if a.ext_providers else "-"
                print(f"experiment_id: {eid_s}")
                print(f"  time_range (min max called_at): {tmn} .. {tmx}")
                print(f"  Anthropic LLM $:        {a.anthropic_usd:.6f}  ({a.n_llm} LLM rows)")
                print(f"  all LLM $ (all prov):   {a.llm_all_usd:.6f}")
                print(f"  External API $:         {a.ext_usd:.6f}  ({a.n_ext} ext rows)")
                print(
                    f"  Combined (Anthropic+ext): {a.combined_anthropic_plus_ext:.6f}"
                )
                print(f"  prompt_names: {prompts_s}")
                print(f"  phases:       {phases_s}")
                print(f"  LLM providers: {lp}")
                print(f"  ext providers: {ep}")
                print()

            # Projection: remaining Anthropic credit $4.64 (from user), cost-per-run from observed anthropic/experiment
            remaining = 4.64
            anthropic_per_run = [
                a.anthropic_usd for a in aggs if a.experiment_id is not None and a.anthropic_usd > 0
            ]
            print("--- Projection ($4.64 remaining Anthropic credit) ---")
            print("Definition: one 'run' = per-experiment Anthropic spend (this DB snapshot).")
            if not anthropic_per_run:
                print("No experiments with Anthropic > 0 — cannot compute mean/p90 baseline.")
            else:
                srt = sorted(anthropic_per_run)
                mean_c = sum(srt) / len(srt)
                p90_c = _pct_linear(srt, 90.0)
                assert p90_c is not None
                n_mean = math.floor(remaining / mean_c) if mean_c > 0 else 0
                n_p90 = math.floor(remaining / p90_c) if p90_c > 0 else 0
                print(f"Observed experiments (Anthropic>0): n={len(srt)}")
                print(f"Mean Anthropic $/experiment:   {mean_c:.6f}")
                print(f"P90 Anthropic $/experiment:   {p90_c:.6f}")
                print()
                print("| Baseline              | $/run (approx.) | Runs on $4.64 (floor) |")
                print("|-----------------------|-----------------|------------------------|")
                print(f"| Mean per experiment   | ${mean_c:.6f}     | {n_mean:<22d} |")
                print(f"| P90 per experiment    | ${p90_c:.6f}     | {n_p90:<22d} |")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
