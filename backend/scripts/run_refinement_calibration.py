#!/usr/bin/env python
"""Refinement chat-mode calibration harness (planning §4.6).

Walks N=5 archetypes through ``refinement_service.run_turn()`` against the live
refinement LLM and writes pass/fail metrics to
``docs/calibration/runs/YYYY-MM-DD-refinement-chatmode.md``.

Usage (from ``D:\\Fivvle\\backend``):

    uv run python scripts/run_refinement_calibration.py --yes

Requires ``--yes`` after the cost warning (real API spend). Does not use HTTP.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

from app.config import Settings, get_settings  # noqa: E402
from app.db.enums import ExperimentStatus  # noqa: E402
from app.db.models.experiment import Experiment  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.db.session import dispose_engine, get_sessionmaker, init_engine  # noqa: E402
from app.schemas.refinement import RefinedIdea, RefinementTurnDecision  # noqa: E402
from app.services.refinement_service import run_turn  # noqa: E402
from tests.eval.refinement_archetypes import REFINEMENT_ARCHETYPES, RefinementArchetype  # noqa: E402

EVAL_USER_EMAIL = "eval@fivvle.internal"
EVAL_FIREBASE_UID = "eval-fivvle-internal"

REFINEMENT_COST_BUDGET_USD = 0.015
MESSAGE_CHAR_LIMIT = 400
MAX_CLARIFY_TURNS_GLOBAL = 3

ESTIMATED_COST_PER_ARCHETYPE_USD = 0.006


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


def _safe_log(msg: str, **fields: object) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    parts = " ".join(f"{k}={v!r}" for k, v in fields.items())
    line = f"[{ts}][refinement_cal] {msg}"
    if parts:
        line = f"{line} {parts}"
    print(line, flush=True)


def _truncate(text: str, n: int) -> str:
    text = text.replace("\n", " ")
    if len(text) <= n:
        return text
    return text[: n - 3] + "..."


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


async def _sum_refinement_cost(session: AsyncSession, experiment_id: UUID) -> float:
    total = (
        await session.execute(
            select(func.coalesce(func.sum(LLMCall.cost_usd), 0)).where(
                LLMCall.experiment_id == experiment_id,
                LLMCall.phase == "refinement_chat",
            )
        )
    ).scalar_one()
    return float(Decimal(str(total)))


def _archetype_slug(archetype_id: str, run_ts: str) -> str:
    slug = f"ref-cal-{archetype_id.lower()}-{run_ts}"
    if len(slug) > 50:
        raise SystemExit(f"ERROR: slug exceeds 50 chars: {slug}")
    return slug


@dataclass
class TurnRecord:
    turn_idx: int
    user_message: str
    decision: str
    clarifying_dimension: str | None
    assistant_message: str
    latency_ms: int
    cost_usd: float
    refinement_count_after: int
    refined_idea: RefinedIdea | None
    schema_ok: bool
    schema_error: str | None


@dataclass
class ArchetypeRunResult:
    archetype: RefinementArchetype
    experiment_id: UUID
    slug: str
    turns: list[TurnRecord] = field(default_factory=list)
    first_decision: str | None = None
    first_dimension: str | None = None
    clarify_turn_count: int = 0
    pivot_turn_ok: bool | None = None
    pivot_counter_reset_ok: bool | None = None
    total_cost_usd: float = 0.0
    automated_pass: bool = False
    check_details: dict[str, str] = field(default_factory=dict)


def _evaluate_archetype(result: ArchetypeRunResult) -> None:
    arch = result.archetype
    checks: dict[str, str] = {}

    first = result.turns[0] if result.turns else None
    if first is None:
        checks["first_turn"] = "FAIL (no turns)"
        result.automated_pass = False
        result.check_details = checks
        return

    fd_ok = first.decision == arch.expected_first_decision
    checks["first_turn_decision"] = (
        f"{'PASS' if fd_ok else 'FAIL'} "
        f"(expected={arch.expected_first_decision}, actual={first.decision})"
    )

    dim_ok = True
    if arch.expected_first_dimensions is not None:
        dim = first.clarifying_dimension
        dim_ok = dim in arch.expected_first_dimensions if dim else False
        checks["first_turn_dimension"] = (
            f"{'PASS' if dim_ok else 'FAIL'} "
            f"(expected one of {sorted(arch.expected_first_dimensions)}, actual={dim!r})"
        )
    else:
        checks["first_turn_dimension"] = "N/A"

    clarify_ok = result.clarify_turn_count <= arch.expected_max_clarify_turns
    checks["clarifying_turns"] = (
        f"{'PASS' if clarify_ok else 'FAIL'} "
        f"({result.clarify_turn_count} observed, max {arch.expected_max_clarify_turns})"
    )

    msg_ok = all(len(t.assistant_message) <= MESSAGE_CHAR_LIMIT for t in result.turns)
    checks["message_length"] = f"{'PASS' if msg_ok else 'FAIL'} (≤ {MESSAGE_CHAR_LIMIT} chars)"

    schema_ok = all(t.schema_ok for t in result.turns)
    checks["schema_validation"] = f"{'PASS' if schema_ok else 'FAIL'}"

    anti_loop_ok = result.clarify_turn_count <= MAX_CLARIFY_TURNS_GLOBAL
    checks["anti_loop"] = (
        f"{'PASS' if anti_loop_ok else 'FAIL'} "
        f"(≤ {MAX_CLARIFY_TURNS_GLOBAL} clarifying turns)"
    )

    cost_ok = result.total_cost_usd <= REFINEMENT_COST_BUDGET_USD
    checks["cost"] = (
        f"{'PASS' if cost_ok else 'FAIL'} "
        f"(${result.total_cost_usd:.4f}, budget ${REFINEMENT_COST_BUDGET_USD:.3f})"
    )

    finalize_turn = next((t for t in reversed(result.turns) if t.decision == "finalize"), None)
    trait_results: list[str] = []
    traits_ok = True
    if finalize_turn is None:
        traits_ok = False
        trait_results.append("FAIL (never finalized)")
    else:
        msg_lower = finalize_turn.assistant_message.lower()
        for trait in arch.expected_finalize_traits:
            ok = trait.lower() in msg_lower
            if not ok:
                traits_ok = False
            trait_results.append(f"{trait!r}: {'PASS' if ok else 'FAIL'}")
    checks["finalize_traits"] = "; ".join(trait_results) if trait_results else "FAIL (no finalize)"

    pivot_ok = True
    if arch.expected_pivot_turn is not None:
        pivot_idx = arch.expected_pivot_turn
        pivot_turn = next((t for t in result.turns if t.turn_idx == pivot_idx), None)
        if pivot_turn is None:
            pivot_dim_ok = False
            pivot_reset_ok = False
        else:
            pivot_dim_ok = pivot_turn.clarifying_dimension == "pivot_resolution"
            pivot_reset_ok = pivot_turn.refinement_count_after == 0
        pivot_ok = pivot_dim_ok and pivot_reset_ok
        checks["pivot"] = (
            f"{'PASS' if pivot_ok else 'FAIL'} "
            f"(turn {pivot_idx}: dimension=pivot_resolution "
            f"{'yes' if pivot_turn and pivot_turn.clarifying_dimension == 'pivot_resolution' else 'no'}, "
            f"counter reset "
            f"{'yes' if pivot_turn and pivot_turn.refinement_count_after == 0 else 'no'})"
        )
        result.pivot_turn_ok = pivot_dim_ok
        result.pivot_counter_reset_ok = pivot_reset_ok

    result.check_details = checks
    result.automated_pass = (
        fd_ok
        and (arch.expected_first_dimensions is None or dim_ok)
        and clarify_ok
        and msg_ok
        and schema_ok
        and anti_loop_ok
        and cost_ok
        and traits_ok
        and pivot_ok
    )


async def _run_archetype(
    sessionmaker,
    *,
    archetype: RefinementArchetype,
    eval_user_id: UUID,
    run_ts: str,
) -> ArchetypeRunResult:
    slug = _archetype_slug(archetype.id, run_ts)

    async with sessionmaker() as session:
        experiment = Experiment(
            user_id=eval_user_id,
            slug=slug,
            raw_idea=archetype.user_messages[0],
            status=ExperimentStatus.REFINING,
            refinement_count=0,
        )
        session.add(experiment)
        await session.commit()
        await session.refresh(experiment)
        experiment_id = experiment.id

    _safe_log(
        "archetype starting",
        archetype_id=archetype.id,
        experiment_id=str(experiment_id),
    )

    result = ArchetypeRunResult(
        archetype=archetype,
        experiment_id=experiment_id,
        slug=slug,
    )
    chat_history: list[tuple[str, str]] = []

    for turn_idx, user_message in enumerate(archetype.user_messages):
        async with sessionmaker() as session:
            exp_result = await session.execute(
                select(Experiment).where(Experiment.id == experiment_id)
            )
            experiment = exp_result.scalar_one()
            cost_before = await _sum_refinement_cost(session, experiment_id)

            t0 = time.perf_counter()
            schema_ok = True
            schema_error: str | None = None
            decision: RefinementTurnDecision | None = None
            try:
                decision = await run_turn(
                    session,
                    experiment,
                    chat_history,
                    user_message,
                )
            except (ValidationError, Exception) as exc:
                schema_ok = False
                schema_error = type(exc).__name__
                await session.commit()
                result.turns.append(
                    TurnRecord(
                        turn_idx=turn_idx,
                        user_message=user_message,
                        decision="error",
                        clarifying_dimension=None,
                        assistant_message="",
                        latency_ms=int((time.perf_counter() - t0) * 1000),
                        cost_usd=0.0,
                        refinement_count_after=experiment.refinement_count,
                        refined_idea=None,
                        schema_ok=False,
                        schema_error=schema_error,
                    )
                )
                break

            latency_ms = int((time.perf_counter() - t0) * 1000)
            await session.commit()
            cost_after = await _sum_refinement_cost(session, experiment_id)
            turn_cost = cost_after - cost_before

            refined: RefinedIdea | None = None
            if decision.refined_idea is not None:
                refined = decision.refined_idea

            record = TurnRecord(
                turn_idx=turn_idx,
                user_message=user_message,
                decision=decision.decision,
                clarifying_dimension=decision.clarifying_dimension,
                assistant_message=decision.assistant_message,
                latency_ms=latency_ms,
                cost_usd=turn_cost,
                refinement_count_after=experiment.refinement_count,
                refined_idea=refined,
                schema_ok=schema_ok,
                schema_error=schema_error,
            )
            result.turns.append(record)

            if turn_idx == 0:
                result.first_decision = decision.decision
                result.first_dimension = decision.clarifying_dimension
            if decision.decision == "clarify":
                result.clarify_turn_count += 1

            chat_history.append(("user", user_message))
            chat_history.append(("assistant", decision.assistant_message))

            if decision.decision == "finalize":
                break

    async with sessionmaker() as session:
        result.total_cost_usd = await _sum_refinement_cost(session, experiment_id)

    _evaluate_archetype(result)
    _safe_log(
        "archetype finished",
        archetype_id=archetype.id,
        automated_pass=result.automated_pass,
        cost_usd=round(result.total_cost_usd, 4),
        turns=len(result.turns),
    )
    return result


def _next_run_number(report_path: Path) -> int:
    """First write is run 1; each subsequent execution appends Run 2, Run 3, …"""
    if not report_path.exists():
        return 1
    return report_path.read_text(encoding="utf-8").count("## Run ") + 2


def _build_report_md(
    *,
    run_number: int,
    settings: Settings,
    results: list[ArchetypeRunResult],
    wall_clock_s: float,
    total_cost_usd: float,
) -> str:
    today = datetime.now(UTC).date().isoformat()
    provider = settings.refinement_provider
    model = settings.refinement_model
    passed = sum(1 for r in results if r.automated_pass)
    costs = [r.total_cost_usd for r in results]
    latencies_ms = [t.latency_ms for r in results for t in r.turns]
    per_turn_costs = [t.cost_usd for r in results for t in r.turns]

    cost_p90 = _pct_linear(sorted(costs), 90.0) or 0.0
    latency_p90_s = (_pct_linear(sorted([float(x) for x in latencies_ms]), 90.0) or 0.0) / 1000.0
    per_turn_cost_p90 = _pct_linear(sorted(per_turn_costs), 90.0) or 0.0

    automated_all_pass = passed == len(results)

    lines: list[str] = []
    if run_number == 1:
        lines.extend(
            [
                f"# Refinement Calibration Run — {today} — {provider}/{model}",
                "",
                "## Summary",
                f"- Archetypes passed (§4.1 + §4.2 + §4.3 automated): {passed} / {len(results)}",
                f"- Cost p90 per experiment (refinement only): ${cost_p90:.4f} (budget: ${REFINEMENT_COST_BUDGET_USD:.3f})",
                f"- Latency p90 per turn: {latency_p90_s:.2f}s",
                "- §4.4 (insight, sharpness, reflection accuracy) — REQUIRES HUMAN SCORING; "
                'see "Per-archetype outputs" below.',
                "",
            ]
        )
    else:
        lines.append("")

    lines.extend(
        [
            f"## Run {run_number}",
            "",
            f"Generated at (UTC): {datetime.now(UTC).isoformat()}",
            f"Wall-clock: {wall_clock_s:.1f}s | Total refinement cost: ${total_cost_usd:.4f}",
            "",
            "### Summary (this run)",
            f"- Archetypes passed (automated): {passed} / {len(results)}",
            f"- Cost p90 per experiment: ${cost_p90:.4f}",
            f"- Latency p90 per turn: {latency_p90_s:.2f}s",
            f"- Per-turn cost p90: ${per_turn_cost_p90:.4f}",
            "",
            "## Per-archetype results",
            "",
        ]
    )

    for r in results:
        arch = r.archetype
        lines.extend(
            [
                f"### {arch.id} — {arch.name}",
                "",
                "**Automated checks:**",
            ]
        )
        for key, detail in r.check_details.items():
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {detail}")

        lines.extend(
            [
                "",
                "**Full turn-by-turn:**",
                "",
                "| Turn | User message (first 80 chars) | Decision | Dimension | "
                "Assistant message | Latency (ms) | Cost |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for t in r.turns:
            lines.append(
                f"| {t.turn_idx} | {_truncate(t.user_message, 80)} | {t.decision} | "
                f"{t.clarifying_dimension or '—'} | {_truncate(t.assistant_message, 120)} | "
                f"{t.latency_ms} | ${t.cost_usd:.4f} |"
            )

        lines.extend(
            [
                "",
                "**§4.4 Human scoring (fill in):**",
                "",
                "| Axis | Score (1-5) | Notes |",
                "|---|---|---|",
                "| Insight |   |   |",
                "| Sharpness |   |   |",
                "| Reflection accuracy |   |   |",
                "",
            ]
        )

        finalize_turn = next((t for t in reversed(r.turns) if t.decision == "finalize"), None)
        if finalize_turn and finalize_turn.refined_idea is not None:
            payload = finalize_turn.refined_idea.model_dump(mode="json")
            lines.append("**Refined idea (if finalized):**")
            lines.append("```json")
            lines.append(json.dumps(payload, indent=2))
            lines.append("```")
        else:
            lines.append("**Refined idea:** _not finalized_")
        lines.append("")

    lines.extend(
        [
            "## Decision",
            "",
            f"- Automated criteria: {'PASS' if automated_all_pass else 'FAIL'}",
            "- If automated PASS: ship pending §4.4 human scores "
            "(median ≥ 4 on all axes across N=5 required per §4.4).",
            "- If automated FAIL on current model: per planning §6.3, flip "
            "refinement_provider/refinement_model in .env and re-run.",
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
    n = len(REFINEMENT_ARCHETYPES)
    est = n * ESTIMATED_COST_PER_ARCHETYPE_USD

    print(
        f"\nWARNING: This will run {n} refinement archetype(s) against the REAL "
        f"refinement LLM.\n"
        f"Estimated API spend: ~${est:.3f} ({n} × ~${ESTIMATED_COST_PER_ARCHETYPE_USD:.3f}).\n"
        "Re-run with --yes to proceed.\n",
        flush=True,
    )
    if not args.yes:
        return 1

    settings = get_settings()
    print(
        f"Provider/model: {settings.refinement_provider} / {settings.refinement_model}\n",
        flush=True,
    )

    today = datetime.now(UTC).date().isoformat()
    report_path = _REPO_ROOT / "docs" / "calibration" / "runs" / f"{today}-refinement-chatmode.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    run_number = _next_run_number(report_path)

    run_ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    init_engine(settings)
    sessionmaker = get_sessionmaker()
    wall_t0 = time.perf_counter()

    try:
        async with sessionmaker() as session:
            eval_user = await _get_or_create_eval_user(session)
            await session.commit()
            eval_user_id = eval_user.id

        results: list[ArchetypeRunResult] = []
        for archetype in REFINEMENT_ARCHETYPES:
            results.append(
                await _run_archetype(
                    sessionmaker,
                    archetype=archetype,
                    eval_user_id=eval_user_id,
                    run_ts=run_ts,
                )
            )

        wall_clock_s = time.perf_counter() - wall_t0
        total_cost_usd = sum(r.total_cost_usd for r in results)

        report_md = _build_report_md(
            run_number=run_number,
            settings=settings,
            results=results,
            wall_clock_s=wall_clock_s,
            total_cost_usd=total_cost_usd,
        )

        if report_path.exists() and run_number > 1:
            existing = report_path.read_text(encoding="utf-8")
            report_path.write_text(existing.rstrip() + "\n\n" + report_md, encoding="utf-8")
        else:
            report_path.write_text(report_md, encoding="utf-8")

        _safe_log("wrote report", path=str(report_path))
        _print_stdout_summary(report_md)
        return 0 if all(r.automated_pass for r in results) else 2
    finally:
        await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run refinement chat-mode calibration archetypes (§4.6 harness)."
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
