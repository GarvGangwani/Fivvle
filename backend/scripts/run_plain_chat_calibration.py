#!/usr/bin/env python
"""Plain-chat calibration harness (planning §7.5.4).

Runs N=20 founder-shaped questions through ``chat_service.reply_plain()`` against
the live LLM and writes pass/fail metrics to
``docs/calibration/runs/YYYY-MM-DD-plain-chat.md``.

Usage (from ``D:\\Fivvle\\backend``):

    uv run python scripts/run_plain_chat_calibration.py --yes

Requires ``--yes`` after the cost warning (real API spend). Does not use HTTP.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_BACKEND_ROOT / ".env")

from app.config import Settings, get_settings  # noqa: E402
from app.db.models.chat_thread import ChatThread  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.db.session import dispose_engine, get_sessionmaker, init_engine  # noqa: E402
from app.llm.prompts.chat_normal import PROMPT_NAME_CHAT_NORMAL  # noqa: E402
from app.services import chat_service  # noqa: E402
from tests.eval.plain_chat_questions import (  # noqa: E402
    REFERENCE_QUESTIONS,
    PlainChatBucket,
    PlainChatQuestion,
)

EVAL_USER_EMAIL = "eval@fivvle.internal"
EVAL_FIREBASE_UID = "eval-fivvle-internal"

RESPONSE_CHAR_LIMIT = 1200
ESTIMATED_COST_PER_QUESTION_USD = 0.003

BUCKET_ORDER: list[PlainChatBucket] = [
    "general",
    "product",
    "idea_redirect",
    "off_topic",
    "prior_research",
]


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
    line = f"[{ts}][plain_chat_cal] {msg}"
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


async def _latest_chat_normal_call(
    session: AsyncSession,
    *,
    after: datetime | None = None,
) -> tuple[float, int] | None:
    stmt = (
        select(LLMCall.cost_usd, LLMCall.latency_ms)
        .where(
            LLMCall.phase == "chat_normal",
            LLMCall.prompt_name == PROMPT_NAME_CHAT_NORMAL,
        )
        .order_by(LLMCall.called_at.desc())
        .limit(1)
    )
    if after is not None:
        stmt = stmt.where(LLMCall.called_at >= after)
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        return None
    cost_usd, latency_ms = row
    return float(Decimal(str(cost_usd))), int(latency_ms)


@dataclass
class QuestionRunResult:
    question: PlainChatQuestion
    thread_id: UUID
    response: str
    latency_ms: int
    cost_usd: float
    automated_pass: bool = False
    check_details: dict[str, str] = field(default_factory=dict)
    fail_phrases_hit: list[str] = field(default_factory=list)


def _evaluate_question(result: QuestionRunResult) -> None:
    q = result.question
    checks: dict[str, str] = {}
    text = result.response
    text_lower = text.lower()

    # pass_criteria: ALL required; pass_criteria_any_of: at least one per group.
    missing = [c for c in q.pass_criteria if c.lower() not in text_lower]
    for group in q.pass_criteria_any_of:
        if not any(term.lower() in text_lower for term in group):
            missing.append(f"any_of{group!r}")
    pass_ok = len(missing) == 0
    checks["pass_criteria"] = (
        "PASS"
        if pass_ok
        else f"FAIL (missing: {missing!r})"
    )

    found_fail = [f for f in q.fail_phrases if f.lower() in text_lower]
    result.fail_phrases_hit = found_fail
    fail_ok = len(found_fail) == 0
    checks["fail_phrases"] = (
        "PASS"
        if fail_ok
        else f"FAIL (found: {found_fail!r})"
    )

    length_ok = len(text) <= RESPONSE_CHAR_LIMIT
    checks["length"] = (
        f"{'PASS' if length_ok else 'FAIL'} "
        f"({len(text)} chars, limit {RESPONSE_CHAR_LIMIT})"
    )

    schema_ok = bool(text and text.strip())
    checks["schema"] = f"{'PASS' if schema_ok else 'FAIL'} (non-empty string)"

    result.check_details = checks
    result.automated_pass = pass_ok and fail_ok and length_ok and schema_ok


async def _run_question(
    sessionmaker,
    *,
    question: PlainChatQuestion,
    eval_user_id: UUID,
    run_started_at: datetime,
) -> QuestionRunResult:
    async with sessionmaker() as session:
        thread = ChatThread(user_id=eval_user_id, title=f"plain-cal-{question.id}")
        session.add(thread)
        await session.flush()
        thread_id = thread.id

        t0 = time.perf_counter()
        try:
            response = await chat_service.reply_plain(
                session,
                chat_history=[],
                latest_message=question.question,
            )
        except Exception as exc:
            await session.commit()
            latency_ms = int((time.perf_counter() - t0) * 1000)
            result = QuestionRunResult(
                question=question,
                thread_id=thread_id,
                response="",
                latency_ms=latency_ms,
                cost_usd=0.0,
            )
            result.check_details = {"error": f"FAIL ({type(exc).__name__}: {exc})"}
            result.automated_pass = False
            _safe_log(
                "question error",
                question_id=question.id,
                error=type(exc).__name__,
            )
            return result

        await session.commit()
        latency_ms = int((time.perf_counter() - t0) * 1000)

        call_info = await _latest_chat_normal_call(session, after=run_started_at)
        if call_info is not None:
            cost_usd, ledger_latency_ms = call_info
            latency_ms = ledger_latency_ms
        else:
            cost_usd = 0.0

    result = QuestionRunResult(
        question=question,
        thread_id=thread_id,
        response=response,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )
    _evaluate_question(result)
    _safe_log(
        "question finished",
        question_id=question.id,
        bucket=question.bucket,
        automated_pass=result.automated_pass,
        cost_usd=round(result.cost_usd, 4),
        chars=len(response),
    )
    return result


def _next_run_number(report_path: Path) -> int:
    if not report_path.exists():
        return 1
    return report_path.read_text(encoding="utf-8").count("## Run ") + 2


def _bucket_pass_counts(results: list[QuestionRunResult]) -> dict[PlainChatBucket, tuple[int, int]]:
    counts: dict[PlainChatBucket, tuple[int, int]] = {
        b: (0, 0) for b in BUCKET_ORDER
    }
    for r in results:
        passed, total = counts[r.question.bucket]
        total += 1
        if r.automated_pass:
            passed += 1
        counts[r.question.bucket] = (passed, total)
    return counts


def _build_report_md(
    *,
    run_number: int,
    settings: Settings,
    results: list[QuestionRunResult],
    wall_clock_s: float,
    total_cost_usd: float,
) -> str:
    today = datetime.now(UTC).date().isoformat()
    provider = settings.refinement_provider
    model = settings.refinement_model
    passed = sum(1 for r in results if r.automated_pass)
    costs = [r.cost_usd for r in results]
    latencies_ms = [float(r.latency_ms) for r in results]

    cost_p90 = _pct_linear(sorted(costs), 90.0) or 0.0
    latency_p90_s = (_pct_linear(sorted(latencies_ms), 90.0) or 0.0) / 1000.0
    bucket_counts = _bucket_pass_counts(results)
    automated_all_pass = passed == len(results)

    lines: list[str] = []
    if run_number == 1:
        lines.extend(
            [
                f"# Plain Chat Calibration Run — {today} — {provider}/{model}",
                "",
                "## Summary",
                f"- Questions passed (automated): {passed} / {len(results)}",
                f"- Cost p90 per question: ${cost_p90:.4f}",
                f"- Latency p90 per question: {latency_p90_s:.2f}s",
                "- §4.4-style human scoring (concision, on-topic discipline, redirect quality) — "
                "REQUIRES HUMAN SCORING; see per-question sections below.",
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
            f"Wall-clock: {wall_clock_s:.1f}s | Total plain-chat cost: ${total_cost_usd:.4f}",
            "",
            "### Summary (this run)",
            f"- Questions passed (automated): {passed} / {len(results)}",
            f"- Cost p90 per question: ${cost_p90:.4f}",
            f"- Latency p90 per question: {latency_p90_s:.2f}s",
            "",
            "### Pass/fail by bucket",
            "",
            "| Bucket | Passed | Total |",
            "|---|---|---|",
        ]
    )
    for bucket in BUCKET_ORDER:
        p, t = bucket_counts[bucket]
        lines.append(f"| {bucket} | {p} | {t} |")
    lines.append("")

    lines.extend(
        [
            "## Per-question results",
            "",
            "| ID | Bucket | Pass | Latency (ms) | Cost | Chars | Notes |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for r in results:
        q = r.question
        status = "PASS" if r.automated_pass else "FAIL"
        note = ""
        if not r.automated_pass:
            failed_checks = [
                k for k, v in r.check_details.items() if v.startswith("FAIL")
            ]
            note = ", ".join(failed_checks) if failed_checks else "see checks"
        lines.append(
            f"| {q.id} | {q.bucket} | {status} | {r.latency_ms} | "
            f"${r.cost_usd:.4f} | {len(r.response)} | {note} |"
        )
    lines.append("")

    for r in results:
        q = r.question
        lines.extend(
            [
                f"### {q.id} — {q.bucket}",
                "",
                f"**Question:** {q.question}",
                "",
                "**Automated checks:**",
            ]
        )
        for key, detail in r.check_details.items():
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {detail}")
        if r.fail_phrases_hit:
            lines.append(f"- Fail phrases hit: {r.fail_phrases_hit!r}")
        lines.extend(
            [
                "",
                "**Assistant response (full):**",
                "",
                "```",
                r.response if r.response else "(empty)",
                "```",
                "",
                "**§4.4-style human scoring (fill in):**",
                "",
                "| Axis | Score (1-5) | Notes |",
                "|---|---|---|",
                "| Concision |   |   |",
                "| On-topic discipline |   |   |",
                "| Redirect quality |   |   |",
                "",
            ]
        )

    lines.extend(
        [
            "## Decision",
            "",
            f"- Automated criteria: {'PASS' if automated_all_pass else 'FAIL'}",
            "- If automated PASS: ship pending §4.4-style human scores "
            "(median ≥ 4 on concision + on-topic discipline across N=20).",
            "- If automated FAIL: review fail_phrases and pass_criteria in "
            "`plain_chat_questions.py` and/or iterate `chat_normal` prompt, then re-run.",
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
    n = len(REFERENCE_QUESTIONS)
    est = n * ESTIMATED_COST_PER_QUESTION_USD

    print(
        f"\nWARNING: This will run {n} plain-chat question(s) against the REAL "
        f"LLM (phase chat_normal).\n"
        f"Estimated API spend: ~${est:.3f} ({n} × ~${ESTIMATED_COST_PER_QUESTION_USD:.3f}).\n"
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
    report_path = _REPO_ROOT / "docs" / "calibration" / "runs" / f"{today}-plain-chat.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    run_number = _next_run_number(report_path)

    run_started_at = datetime.now(UTC)
    init_engine(settings)
    sessionmaker = get_sessionmaker()
    wall_t0 = time.perf_counter()

    try:
        async with sessionmaker() as session:
            eval_user = await _get_or_create_eval_user(session)
            await session.commit()
            eval_user_id = eval_user.id

        results: list[QuestionRunResult] = []
        for question in REFERENCE_QUESTIONS:
            results.append(
                await _run_question(
                    sessionmaker,
                    question=question,
                    eval_user_id=eval_user_id,
                    run_started_at=run_started_at,
                )
            )

        wall_clock_s = time.perf_counter() - wall_t0
        total_cost_usd = sum(r.cost_usd for r in results)

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
        description="Run plain-chat calibration questions (§7.5.4 harness)."
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
