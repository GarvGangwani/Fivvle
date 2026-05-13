"""Manual test script for the full 3-phase research engine.

Run from the backend/ directory:

    uv run python scripts/try_research_engine.py          # idea #1 (slack-hr-bot)
    uv run python scripts/try_research_engine.py 1        # slack-hr-bot
    uv run python scripts/try_research_engine.py 5        # newsletter-affiliate
    uv run python scripts/try_research_engine.py all      # ALL 10 ideas (costs $5-$8)

Requires a working .env with at minimum:
    ANTHROPIC_API_KEY
    TAVILY_API_KEY
    DATABASE_URL     (for LLMCall / ExternalAPICall logging)
    GROQ_API_KEY     (required by Settings validation, even if not used here)
    FIREBASE_PROJECT_ID
    GOOGLE_APPLICATION_CREDENTIALS
    REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT

What this script does:
- Runs the full Planner → Searcher → Synthesizer pipeline against eval ideas.
- Default (no arg): runs idea #1 (slack-hr-bot) only. Single run costs $0.30-$0.70.
- Numeric arg 1-10: runs that specific idea by position in EVAL_IDEAS list.
- "all" arg: runs all 10 ideas. WARNING: estimated cost $5-$8.
- For each idea, prints:
    • Idea id and domain
    • Planner result: question count, has_synthesizer_notes flag
    • Searcher result: per-question result counts
    • Full ValidationReport:
        - executive_summary
        - each QuestionFindings with all findings (claim, confidence, citations)
        - competitors list
        - market_signals, distribution_signals, regulatory_signals
        - risks_assessment
        - recommendation + rationale
        - research_limitations
    • Cost breakdown: planner LLM cost, synthesizer LLM cost, total Tavily cost,
      total cost
    • Per-phase latency

LLMCall and ExternalAPICall rows ARE written to the database automatically.

This script does NOT check output quality against gold standards — that is done
via backend/tests/eval/. This is a prompt-iteration tool for human inspection.
Read the output and tune prompts until reports are sharp, specific, and honest.
"""

import asyncio
import sys
import time
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup: allow `uv run python scripts/try_research_engine.py` from backend/
# ---------------------------------------------------------------------------
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

# ---------------------------------------------------------------------------
# Load .env before importing Settings (Pydantic Settings reads it at import)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_backend_root / ".env")

# ---------------------------------------------------------------------------
# Now import app modules (Settings will find its env vars)
# ---------------------------------------------------------------------------
from decimal import Decimal  # noqa: E402, F811

from sqlalchemy import desc, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.models.external_api_call import ExternalAPICall  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.schemas.validation_report import ValidationReport  # noqa: E402
from app.services.research_engine import run_research_engine  # noqa: E402
from tests.eval.ideas import EVAL_IDEAS  # noqa: E402


def _print_separator(label: str = "", width: int = 72) -> None:
    line = "=" * width
    if label:
        print(f"\n{line}")
        print(f"  {label}")
        print(line)
    else:
        print(line)


def _print_section(label: str, width: int = 72) -> None:
    print(f"\n{'─' * width}")
    print(f"  {label}")
    print(f"{'─' * width}")


def _print_report(report: ValidationReport) -> None:
    """Print the full ValidationReport in human-readable format."""
    _print_section("EXECUTIVE SUMMARY")
    print(f"  {report.executive_summary}")
    print(f"\n  Overall recommendation: [{report.overall_recommendation.upper()}]")
    print(f"  Rationale: {report.recommendation_rationale}")

    _print_section("QUESTIONS AND FINDINGS")
    for qf in report.questions_and_findings:
        print(f"\n  [{qf.question_id}] {qf.question}")
        print(f"       Findings ({len(qf.findings)} items):")
        for i, f in enumerate(qf.findings, 1):
            print(f"\n    Finding {i} [{f.confidence.upper()}]")
            print(f"      Claim:    {f.claim}")
            print(f"      Evidence: {f.evidence_summary}")
            print(f"      Why {f.confidence}: {f.confidence_rationale}")
            print(f"      Citations ({len(f.citations)}):")
            for c in f.citations:
                print(f"        • [{c.source_domain}] {c.title}")
                print(f"          {c.url}")
        if qf.evidence_gap:
            print(f"\n    Evidence gap: {qf.evidence_gap}")

    _print_section("COMPETITORS")
    if report.competitors:
        for comp in report.competitors:
            print(f"\n  {comp.name}")
            print(f"    {comp.description}")
            print(f"    vs idea: {comp.positioning_vs_idea}")
            for c in comp.citations:
                print(f"    source: {c.url}")
    else:
        print("  (no named competitors surfaced in search results)")

    _print_section("MARKET SIGNALS")
    print(f"  {report.market_signals}")

    if report.distribution_signals:
        _print_section("DISTRIBUTION SIGNALS")
        print(f"  {report.distribution_signals}")

    if report.regulatory_signals:
        _print_section("REGULATORY SIGNALS")
        print(f"  {report.regulatory_signals}")

    _print_section("RISKS ASSESSMENT")
    print(f"  {report.risks_assessment}")

    _print_section("RESEARCH LIMITATIONS")
    print(f"  {report.research_limitations}")

    print(f"\n  Rubric version: {report.rubric_version_used}")


async def _fetch_phase_costs(
    session_factory: async_sessionmaker,  # type: ignore[type-arg]
    experiment_id_none_run: bool = True,
) -> dict[str, Decimal]:
    """Fetch the most recent LLMCall rows for planner and synthesizer prompts."""
    from app.llm.prompts.planner import PROMPT_NAME as PLANNER_PROMPT
    from app.llm.prompts.synthesizer import PROMPT_NAME as SYNTH_PROMPT

    costs: dict[str, Decimal] = {}

    async with session_factory() as db:
        for prompt_name, phase_key in [
            (PLANNER_PROMPT, "planner"),
            (SYNTH_PROMPT, "synthesizer"),
        ]:
            stmt = (
                select(LLMCall)
                .where(LLMCall.prompt_name == prompt_name)
                .order_by(desc(LLMCall.called_at))
                .limit(1)
            )
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            if row is not None:
                costs[phase_key] = row.cost_usd
                costs[f"{phase_key}_tokens"] = Decimal(
                    row.prompt_tokens + row.completion_tokens
                )
                costs[f"{phase_key}_latency_ms"] = Decimal(row.latency_ms)
            else:
                costs[phase_key] = Decimal("0")

    return costs


async def _fetch_tavily_cost(
    session_factory: async_sessionmaker,  # type: ignore[type-arg]
    since_seconds: int = 120,
) -> Decimal:
    """Sum ExternalAPICall costs for Tavily in the last N seconds."""
    import datetime

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=since_seconds)
    async with session_factory() as db:
        stmt = select(ExternalAPICall).where(
            ExternalAPICall.provider == "tavily",
            ExternalAPICall.called_at >= cutoff,
            ExternalAPICall.success.is_(True),
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
    return sum((r.cost_usd for r in rows), Decimal("0"))


async def main() -> None:
    settings = get_settings()

    # ---------------------------------------------------------------------------
    # CLI parsing
    # ---------------------------------------------------------------------------
    run_all = False
    single_idx: int | None = None

    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg == "all":
            run_all = True
        else:
            try:
                single_idx = int(arg)
            except ValueError:
                print(
                    f"ERROR: argument must be a number (1-10) or 'all'; got {sys.argv[1]!r}"
                )
                sys.exit(1)
            if single_idx < 1 or single_idx > len(EVAL_IDEAS):
                print(
                    f"ERROR: index {single_idx} out of range — "
                    f"must be 1-{len(EVAL_IDEAS)}"
                )
                sys.exit(1)

    if run_all:
        ideas_to_run = list(enumerate(EVAL_IDEAS, start=1))
    elif single_idx is not None:
        ideas_to_run = [(single_idx, EVAL_IDEAS[single_idx - 1])]
    else:
        # Default: run idea #1 only
        ideas_to_run = [(1, EVAL_IDEAS[0])]

    # ---------------------------------------------------------------------------
    # Warnings
    # ---------------------------------------------------------------------------
    _print_separator("FIVVLE RESEARCH ENGINE TESTER (3-phase: Planner+Searcher+Synth)")
    print(f"Model:     claude-sonnet-4-6 (planner + synthesizer)")
    print(f"Search:    Tavily advanced depth, 5 results/query")
    print(f"Ideas:     {len(ideas_to_run)} idea(s) queued")

    if run_all:
        print(
            "\n  ⚠  WARNING: Running all 10 ideas will cost approximately $5-$8 in "
            "LLM + Tavily API costs.\n"
            "     Each idea: ~$0.30-$0.70 in API costs + 14-21 Tavily advanced searches.\n"
            "     Press Ctrl+C within 5 seconds to cancel."
        )
        await asyncio.sleep(5)
    else:
        print(f"  Estimated cost per idea: $0.30-$0.70 in LLM + Tavily API costs.")

    print(
        "\nLLMCall and ExternalAPICall rows will be written to the database.\n"
        "Inspect costs via GET /admin/cost/daily after the run.\n"
    )

    # ---------------------------------------------------------------------------
    # Engine setup
    # ---------------------------------------------------------------------------
    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # ---------------------------------------------------------------------------
    # Run ideas
    # ---------------------------------------------------------------------------
    total_ideas_run = 0
    total_ideas_failed = 0

    try:
        for idx, eval_idea in ideas_to_run:
            _print_separator(f"IDEA #{idx}: {eval_idea.id}  [{eval_idea.domain}]")
            print(f"  Target audience: {eval_idea.refined_idea.target_audience}")
            print(f"\n  Stated risks ({len(eval_idea.refined_idea.risks)} items):")
            for i, risk in enumerate(eval_idea.refined_idea.risks, 1):
                print(f"    {i}. {risk}")

            idea_start = time.perf_counter()

            try:
                async with session_factory() as db:
                    report = await run_research_engine(
                        db=db,
                        refined_idea=eval_idea.refined_idea,
                        experiment_id=None,
                    )
                    await db.commit()

                idea_elapsed_s = time.perf_counter() - idea_start

                print(f"\n  Completed in {idea_elapsed_s:.1f}s")

                # Print the full report
                _print_report(report)

                # Fetch cost breakdown
                phase_costs = await _fetch_phase_costs(session_factory)
                tavily_cost = await _fetch_tavily_cost(
                    session_factory, since_seconds=int(idea_elapsed_s) + 30
                )
                total_cost = (
                    phase_costs.get("planner", Decimal("0"))
                    + phase_costs.get("synthesizer", Decimal("0"))
                    + tavily_cost
                )

                _print_section("COST BREAKDOWN")
                print(
                    f"  Planner LLM:      ${phase_costs.get('planner', 0):.6f}  "
                    f"({int(phase_costs.get('planner_tokens', 0))} tokens, "
                    f"{int(phase_costs.get('planner_latency_ms', 0))}ms)"
                )
                print(
                    f"  Synthesizer LLM:  ${phase_costs.get('synthesizer', 0):.6f}  "
                    f"({int(phase_costs.get('synthesizer_tokens', 0))} tokens, "
                    f"{int(phase_costs.get('synthesizer_latency_ms', 0))}ms)"
                )
                print(f"  Tavily searches:  ${tavily_cost:.6f}")
                print(f"  TOTAL:            ${total_cost:.6f}")
                print(f"  Wall-clock:       {idea_elapsed_s:.1f}s")

                total_ideas_run += 1

            except Exception as exc:  # noqa: BLE001
                total_ideas_failed += 1
                print(
                    f"\n  ERROR on idea #{idx} ({eval_idea.id}): "
                    f"{type(exc).__name__}: {exc}"
                )
                import traceback
                traceback.print_exc()

            if idx != ideas_to_run[-1][0]:
                print("\n  (sleeping 2s before next idea...)")
                await asyncio.sleep(2)

    finally:
        await engine.dispose()

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    _print_separator("DONE")
    print(f"  Ideas run:    {total_ideas_run}")
    print(f"  Ideas failed: {total_ideas_failed}")
    print()
    print("Next steps:")
    print("  • Read the report output above — is the recommendation grounded?")
    print("  • Check citations — are they real URLs from the search results?")
    print("  • Check specificity — named entities, numbers, quoted sources?")
    print("  • Check honesty — if vague idea, did it say too_vague_to_recommend?")
    print("  • Tune synthesizer.py or planner.py if quality is off, then re-run.")
    print("  • Inspect LLMCall rows via GET /admin/cost/daily for cost summary.")


if __name__ == "__main__":
    asyncio.run(main())
