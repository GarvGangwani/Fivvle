#!/usr/bin/env python
"""Tier-3 calibration runner — real production research pipeline on eval ideas.

Runs a 5–7 idea subset through ``run_research_engine_pipeline`` (same path as
production), seeds Experiment rows per idea, and reports launch-gate metrics
(RESEARCH_READY rate, cost, latency, citation counts). Does not use gold files
or rubric scoring.

Usage (from ``D:\\Fivvle\\backend``):

    .\\.venv\\Scripts\\python.exe scripts/run_eval.py --yes
    .\\.venv\\Scripts\\python.exe scripts/run_eval.py --yes --ids slack-hr-bot,fitness-accountability

Writes ``docs/calibration/runs/eval-<timestamp>/summary.md`` and prints the same
summary to stdout. Requires ``--yes`` after the cost warning (real API spend).

Per AGENTS.md logging hygiene: never logs idea prose, report bodies, or citation URLs.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# ---------------------------------------------------------------------------
# Path + env (runnable from backend/)
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

from app.config import Settings  # noqa: E402
from app.db.enums import ExperimentStatus  # noqa: E402
from app.db.models.experiment import Experiment  # noqa: E402
from app.db.models.external_api_call import ExternalAPICall  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.db.session import dispose_engine, get_sessionmaker, init_engine  # noqa: E402
from app.services.research_engine_service import run_research_engine_pipeline  # noqa: E402
from tests.eval.ideas import EVAL_IDEAS  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_IDEAS = (
    "slack-hr-bot",
    "fitness-accountability",
    "mechanic-marketplace",
    "tax-loss-harvesting",
    "visa-deadline-tracker",
    "vague-ai-productivity",
)

EVAL_USER_EMAIL = "eval@fivvle.internal"
EVAL_FIREBASE_UID = "eval-fivvle-internal"

ESTIMATED_COST_PER_IDEA_USD = 1.60
RESEARCH_READY_THRESHOLD = 0.95
MEAN_COST_THRESHOLD_USD = 1.80

_EVAL_BY_ID = {idea.id: idea for idea in EVAL_IDEAS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _parse_ids(raw: str | None) -> list[str]:
    if raw is None:
        return list(DEFAULT_IDEAS)
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not ids:
        raise SystemExit("ERROR: --ids was empty after parsing.")
    unknown = [i for i in ids if i not in _EVAL_BY_ID]
    if unknown:
        known = ", ".join(sorted(_EVAL_BY_ID))
        raise SystemExit(
            f"ERROR: Unknown eval idea id(s): {', '.join(unknown)}\n"
            f"Valid ids: {known}"
        )
    return ids


def _eval_slug(idea_id: str, run_ts: str) -> str:
    slug = f"eval-{idea_id}-{run_ts}"
    if len(slug) > 50:
        raise SystemExit(
            f"ERROR: Generated slug exceeds 50 chars ({len(slug)}): use a shorter run timestamp."
        )
    return slug


def _count_citations(raw_report: dict) -> int:
    """Count citation objects in a persisted ValidationReport payload (no URL logging)."""
    total = 0
    for qf in raw_report.get("questions_and_findings") or []:
        if not isinstance(qf, dict):
            continue
        for finding in qf.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            citations = finding.get("citations") or []
            if isinstance(citations, list):
                total += len(citations)
    for comp in raw_report.get("competitors") or []:
        if not isinstance(comp, dict):
            continue
        citations = comp.get("citations") or []
        if isinstance(citations, list):
            total += len(citations)
    return total


def _safe_log(msg: str, **fields: object) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    parts = " ".join(f"{k}={v!r}" for k, v in fields.items())
    line = f"[{ts}][run_eval] {msg}"
    if parts:
        line = f"{line} {parts}"
    print(line, flush=True)


@dataclass
class IdeaRunResult:
    idea_id: str
    experiment_id: UUID
    slug: str
    terminal_status: str
    research_error_detail: str | None
    latency_s: float
    cost_usd: float
    citation_count: int | None  # None when no report persisted


async def _get_or_create_eval_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == EVAL_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        firebase_uid=EVAL_FIREBASE_UID,
        email=EVAL_USER_EMAIL,
        name="Eval Runner",
        credits_remaining=0,
        is_admin=False,
    )
    session.add(user)
    await session.flush()
    _safe_log("created eval user", user_id=str(user.id))
    return user


async def _sum_run_cost(session: AsyncSession, experiment_id: UUID) -> float:
    llm_sum = (
        await session.execute(
            select(func.coalesce(func.sum(LLMCall.cost_usd), 0)).where(
                LLMCall.experiment_id == experiment_id
            )
        )
    ).scalar_one()
    ext_sum = (
        await session.execute(
            select(func.coalesce(func.sum(ExternalAPICall.cost_usd), 0)).where(
                ExternalAPICall.experiment_id == experiment_id
            )
        )
    ).scalar_one()
    return float(Decimal(str(llm_sum)) + Decimal(str(ext_sum)))


async def _run_one_idea(
    sessionmaker,
    *,
    idea_id: str,
    eval_user_id: UUID,
    run_ts: str,
) -> IdeaRunResult:
    idea = _EVAL_BY_ID[idea_id]
    slug = _eval_slug(idea_id, run_ts)

    async with sessionmaker() as session:
        experiment = Experiment(
            user_id=eval_user_id,
            slug=slug,
            raw_idea=idea.raw_idea,
            refined_idea=idea.refined_idea.model_dump(mode="json"),
            status=ExperimentStatus.DRAFT,
        )
        session.add(experiment)
        await session.commit()
        await session.refresh(experiment)
        experiment_id = experiment.id

    _safe_log(
        "pipeline starting",
        idea_id=idea_id,
        experiment_id=str(experiment_id),
        slug=slug,
    )

    t0 = time.perf_counter()
    await run_research_engine_pipeline(experiment_id, sessionmaker)
    latency_s = time.perf_counter() - t0

    async with sessionmaker() as session:
        result = await session.execute(
            select(Experiment)
            .options(selectinload(Experiment.validation_report))
            .where(Experiment.id == experiment_id)
        )
        exp = result.scalar_one()
        cost_usd = await _sum_run_cost(session, experiment_id)
        citation_count: int | None = None
        if exp.validation_report is not None:
            citation_count = _count_citations(exp.validation_report.raw_report)

    _safe_log(
        "pipeline finished",
        idea_id=idea_id,
        experiment_id=str(experiment_id),
        status=exp.status.value,
        latency_s=round(latency_s, 2),
        cost_usd=round(cost_usd, 4),
        citation_count=citation_count,
    )

    return IdeaRunResult(
        idea_id=idea_id,
        experiment_id=experiment_id,
        slug=slug,
        terminal_status=exp.status.value,
        research_error_detail=exp.research_error_detail,
        latency_s=latency_s,
        cost_usd=cost_usd,
        citation_count=citation_count,
    )


def _build_summary_md(
    *,
    run_label: str,
    idea_ids: list[str],
    eval_user_id: UUID,
    results: list[IdeaRunResult],
    output_dir: Path,
) -> str:
    n = len(results)
    ready_count = sum(1 for r in results if r.terminal_status == ExperimentStatus.RESEARCH_READY.value)
    ready_rate = ready_count / n if n else 0.0
    costs = [r.cost_usd for r in results]
    latencies = [r.latency_s for r in results]
    mean_cost = sum(costs) / n if n else 0.0
    mean_latency = sum(latencies) / n if n else 0.0
    p90_cost = _pct_linear(sorted(costs), 90.0)
    p90_latency = _pct_linear(sorted(latencies), 90.0)

    total_citations = sum(r.citation_count or 0 for r in results)
    reports_with_citations = [r for r in results if r.citation_count is not None]

    ready_pass = ready_rate >= RESEARCH_READY_THRESHOLD
    cost_pass = mean_cost <= MEAN_COST_THRESHOLD_USD

    lines: list[str] = [
        f"# Eval calibration run `{run_label}`",
        "",
        f"Generated at (UTC): {datetime.now(UTC).isoformat()}",
        "",
        "## Configuration",
        "",
        f"- Ideas ({n}): `{', '.join(idea_ids)}`",
        f"- Eval user_id (filter handle): `{eval_user_id}`",
        f"- Output directory: `{output_dir.as_posix()}`",
        "- Heavy artifacts: none (raw ValidationReport JSON not written)",
        "",
        "## Per-idea results",
        "",
        "| idea_id | experiment_id | slug | terminal_status | latency_s | cost_usd | citations | error_detail |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]

    for r in results:
        err = (r.research_error_detail or "").replace("|", "\\|").replace("\n", " ")
        if len(err) > 120:
            err = err[:117] + "..."
        cites = str(r.citation_count) if r.citation_count is not None else "—"
        lines.append(
            f"| {r.idea_id} | `{r.experiment_id}` | `{r.slug}` | {r.terminal_status} "
            f"| {r.latency_s:.1f} | {r.cost_usd:.4f} | {cites} | {err or '—'} |"
        )

    lines.extend(
        [
            "",
            "## Tier-3 aggregate metrics",
            "",
            f"- **RESEARCH_READY rate:** {ready_count}/{n} = {ready_rate * 100:.1f}%",
            "- **Citation hallucination rate:** not computed (needs evidence set — "
            "Tavily/Reader URLs are not persisted on audit rows for post-hoc URL allowlists)",
            f"- **Citation count (sum across reports):** {total_citations} "
            f"({len(reports_with_citations)} report(s) with persisted citations)",
            f"- **Mean cost per run:** ${mean_cost:.4f}",
            f"- **P90 cost per run:** ${p90_cost:.4f}" if p90_cost is not None else "- **P90 cost per run:** —",
            f"- **Mean latency per run:** {mean_latency:.1f}s",
            f"- **P90 latency per run:** {p90_latency:.1f}s"
            if p90_latency is not None
            else "- **P90 latency per run:** —",
            "",
            "## Launch gates (Tier-3)",
            "",
            "| Gate | Threshold | Actual | Pass |",
            "| --- | --- | --- | --- |",
            f"| RESEARCH_READY rate | ≥ {RESEARCH_READY_THRESHOLD * 100:.0f}% | "
            f"{ready_rate * 100:.1f}% | {'PASS' if ready_pass else 'FAIL'} |",
            "| Citation hallucination rate | 0% | not computed | SKIP |",
            f"| Mean cost per run | ≤ ${MEAN_COST_THRESHOLD_USD:.2f} | "
            f"${mean_cost:.4f} | {'PASS' if cost_pass else 'FAIL'} |",
            "",
            f"**Overall launch gate:** {'PASS' if ready_pass and cost_pass else 'FAIL'} "
            "(hallucination gate skipped until evidence set is reachable)",
            "",
        ]
    )
    return "\n".join(lines)


def _print_stdout_summary(md: str) -> None:
    print("\n" + "=" * 72)
    try:
        print(md.rstrip())
    except UnicodeEncodeError:
        sys.stdout.buffer.write(md.rstrip().encode("utf-8", errors="replace") + b"\n")
    print("=" * 72 + "\n", flush=True)


async def _async_main(args: argparse.Namespace) -> int:
    idea_ids = _parse_ids(args.ids)
    n = len(idea_ids)
    est = n * ESTIMATED_COST_PER_IDEA_USD

    print(
        f"\nWARNING: This will run {n} idea(s) through the REAL research pipeline "
        f"(Tavily + Anthropic).\n"
        f"Estimated API spend: ~${est:.2f} ({n} × ~${ESTIMATED_COST_PER_IDEA_USD:.2f}).\n"
        "Re-run with --yes to proceed.\n",
        flush=True,
    )
    if not args.yes:
        return 1

    run_ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_label = f"eval-{run_ts}"
    output_dir = _REPO_ROOT / "docs" / "calibration" / "runs" / run_label
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings()
    init_engine(settings)
    sessionmaker = get_sessionmaker()

    try:
        async with sessionmaker() as session:
            eval_user = await _get_or_create_eval_user(session)
            await session.commit()
            eval_user_id = eval_user.id

        _safe_log("eval run starting", run_label=run_label, n_ideas=n, eval_user_id=str(eval_user_id))

        results: list[IdeaRunResult] = []
        for idea_id in idea_ids:
            results.append(
                await _run_one_idea(
                    sessionmaker,
                    idea_id=idea_id,
                    eval_user_id=eval_user_id,
                    run_ts=run_ts,
                )
            )

        summary_md = _build_summary_md(
            run_label=run_label,
            idea_ids=idea_ids,
            eval_user_id=eval_user_id,
            results=results,
            output_dir=output_dir,
        )
        summary_path = output_dir / "summary.md"
        summary_path.write_text(summary_md, encoding="utf-8")
        _safe_log("wrote summary", path=str(summary_path))
        _print_stdout_summary(summary_md)
        return 0
    finally:
        await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run eval ideas through the production research pipeline (Tier-3 metrics)."
    )
    parser.add_argument(
        "--ids",
        metavar="ID1,ID2,...",
        help=(
            "Comma-separated eval idea ids (default: 6-idea calibration spread: "
            + ", ".join(DEFAULT_IDEAS)
            + ")"
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm real API spend after reading the cost warning",
    )
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_async_main(args)))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
