"""Manual test script for the research-engine Planner service.

Run from the backend/ directory:

    uv run python scripts/try_planner.py          # all 3 eval ideas
    uv run python scripts/try_planner.py 1        # slack-hr-bot only
    uv run python scripts/try_planner.py 2        # video-editor-marketplace only
    uv run python scripts/try_planner.py 3        # vague-ai-productivity only

Requires a working .env with at minimum:
    ANTHROPIC_API_KEY
    DATABASE_URL     (for LLMCall logging — the LLM client writes a row per call)
    GROQ_API_KEY     (required by Settings, even if not used here)
    FIREBASE_PROJECT_ID
    FIREBASE_SERVICE_ACCOUNT_PATH
    TAVILY_API_KEY
    REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT

What this script does:
- Runs the planner against 3 EvalIdea entries:
    1. slack-hr-bot (B2B SaaS — well-defined idea with specific risks)
    2. video-editor-marketplace (Marketplace — supply-side dynamics)
    3. vague-ai-productivity (deliberately vague — tests honesty mechanism)
- For each idea, prints the input (audience, risks) and output (all questions
  with id, question text, rationale, search queries)
- Fetches the most recent LLMCall row for cost data after each call
- Catches and prints per-idea exceptions without stopping the loop
- Sleeps 1s between calls

This script does NOT execute Tavily searches — search_queries are printed for
human inspection only. Eval-by-execution of queries comes in B2.3+.

This is a prompt-iteration tool, not a test. Read the output and tweak
PLANNER_SYSTEM_PROMPT in app/llm/prompts/planner.py until the questions are
sharp, specific, and investigable for each idea type.

LLMCall rows ARE written to the database automatically.
"""

import asyncio
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup: allow `uv run python scripts/try_planner.py` from backend/
# ---------------------------------------------------------------------------
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

# ---------------------------------------------------------------------------
# Load .env before importing Settings (Pydantic Settings reads it at import)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv  # pydantic-settings bundles python-dotenv  # noqa: E402

load_dotenv(_backend_root / ".env")

# ---------------------------------------------------------------------------
# Now import app modules (Settings will find its env vars)
# ---------------------------------------------------------------------------
from sqlalchemy import desc, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.models.llm_call import LLMCall  # noqa: E402
from app.schemas.planner import ResearchPlan  # noqa: E402
from app.services.planner_service import plan_research  # noqa: E402
from tests.eval.ideas import EVAL_IDEAS  # noqa: E402

# ---------------------------------------------------------------------------
# 3 eval ideas from ideas.py, numbered 1-3 for the CLI arg.
# Chosen to cover well-defined B2B SaaS, supply-hard marketplace, and
# deliberately vague idea (honesty mechanism test).
# ---------------------------------------------------------------------------
_EVAL_INDICES = {
    1: "slack-hr-bot",
    2: "video-editor-marketplace",
    3: "vague-ai-productivity",
}

_EVAL_IDEAS_BY_NUMBER = {
    num: next(e for e in EVAL_IDEAS if e.id == slug)
    for num, slug in _EVAL_INDICES.items()
}


def _print_separator(label: str = "") -> None:
    line = "=" * 72
    if label:
        print(f"\n{line}")
        print(f"  {label}")
        print(line)
    else:
        print(line)


def _print_plan(idea_number: int, eval_idea, plan: ResearchPlan) -> None:  # type: ignore[no-untyped-def]
    refined = eval_idea.refined_idea

    print(f"\n{'─' * 72}")
    print(f"IDEA #{idea_number}: {eval_idea.id}  [{eval_idea.domain}]")

    print("\n  TARGET AUDIENCE:")
    print(f"    {refined.target_audience}")

    print(f"\n  STATED RISKS ({len(refined.risks)} items):")
    for i, risk in enumerate(refined.risks, 1):
        print(f"    {i}. {risk}")

    print(f"\n{'─' * 72}")
    print(f"RESEARCH PLAN — {len(plan.questions)} questions:")

    for q in plan.questions:
        print(f"\n  [{q.id}] {q.question}")
        print(f"       RATIONALE: {q.rationale}")
        print("       SEARCH QUERIES:")
        for sq in q.search_queries:
            print(f"         • {sq}")

    if plan.notes_for_synthesizer:
        print("\n  NOTES FOR SYNTHESIZER:")
        print(f"    {plan.notes_for_synthesizer}")
    else:
        print("\n  notes_for_synthesizer: (none)")


async def _fetch_latest_llm_call_cost(
    session_factory: async_sessionmaker,  # type: ignore[type-arg]
    prompt_name: str,
) -> None:
    """Query the most recent LLMCall row for this prompt_name and print cost."""
    async with session_factory() as db:
        stmt = (
            select(LLMCall)
            .where(LLMCall.prompt_name == prompt_name)
            .order_by(desc(LLMCall.called_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()

    if row is not None:
        print("\n  LLMCall cost summary:")
        print(f"    prompt_tokens:     {row.prompt_tokens}")
        print(f"    completion_tokens: {row.completion_tokens}")
        print(f"    cost_usd:          ${row.cost_usd:.6f}")
        print(f"    latency_ms:        {row.latency_ms}")
    else:
        print(f"\n  (No LLMCall row found for prompt_name={prompt_name!r})")


async def main() -> None:
    from app.llm.prompts.planner import PROMPT_NAME

    settings = get_settings()

    # Optional CLI arg: 1-based index of a single idea to run (1, 2, or 3).
    single_idx: int | None = None
    if len(sys.argv) > 1:
        try:
            single_idx = int(sys.argv[1])
        except ValueError:
            print(f"ERROR: argument must be 1, 2, or 3; got {sys.argv[1]!r}")
            sys.exit(1)
        if single_idx not in _EVAL_IDEAS_BY_NUMBER:
            print(f"ERROR: index {single_idx} out of range — must be 1, 2, or 3")
            sys.exit(1)

    if single_idx is not None:
        ideas_to_run = [(single_idx, _EVAL_IDEAS_BY_NUMBER[single_idx])]
    else:
        ideas_to_run = [(n, _EVAL_IDEAS_BY_NUMBER[n]) for n in sorted(_EVAL_IDEAS_BY_NUMBER)]

    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    _print_separator("FIVVLE PLANNER PROMPT TESTER")
    print(f"Model: claude-sonnet-4-6   Ideas: {len(ideas_to_run)}")
    print("LLM calls will be logged to LLMCall table.")
    print("Search queries are printed for inspection — NOT executed against Tavily.")

    try:
        for idx, eval_idea in ideas_to_run:
            try:
                async with session_factory() as db:
                    plan = await plan_research(
                        db=db,
                        refined_idea=eval_idea.refined_idea,
                        experiment_id=None,
                    )
                    await db.commit()

                _print_plan(idx, eval_idea, plan)

                # Fetch the freshly written LLMCall row for cost introspection.
                await _fetch_latest_llm_call_cost(session_factory, PROMPT_NAME)

            except Exception as exc:  # noqa: BLE001
                print(f"\n  ERROR on idea #{idx} ({eval_idea.id}): {type(exc).__name__}: {exc}")

            if idx < ideas_to_run[-1][0]:
                await asyncio.sleep(1)

    finally:
        await engine.dispose()

    _print_separator("DONE")
    print("Inspect LLMCall rows via GET /admin/cost/daily for cost summary.")
    print(
        "To tune the prompt: edit app/llm/prompts/planner.py and re-run this script."
    )


if __name__ == "__main__":
    asyncio.run(main())
