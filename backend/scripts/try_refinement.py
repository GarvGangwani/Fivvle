"""Manual test script for the idea-refinement service.

Run from the backend/ directory:

    uv run python scripts/try_refinement.py          # all 5 ideas + regen round
    uv run python scripts/try_refinement.py 3        # idea #3 only, no regen round

Requires a working .env with at minimum:
    ANTHROPIC_API_KEY
    DATABASE_URL     (for LLMCall logging — the LLM client writes a row per call)
    GROQ_API_KEY     (required by Settings, even if not used here)
    FIREBASE_PROJECT_ID
    FIREBASE_SERVICE_ACCOUNT_PATH
    TAVILY_API_KEY
    REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT

What this script does:
- Runs refinement on 5 diverse founder ideas (B2B SaaS, consumer mobile,
  marketplace, dev tool, creator economy)
- Prints each field of the returned RefinedIdea with clear labels
- Tries one regeneration with feedback on the first idea
- Catches and prints per-idea exceptions without stopping the loop
- Adds a 1-second pause between calls to be polite to Anthropic

This is a prompt-iteration tool, not a test. Read the output with your eyes
and tweak REFINEMENT_SYSTEM_PROMPT in app/llm/prompts/refinement.py until
every field looks right. Then run again to verify.

LLMCall rows ARE written to the database (the client wrapper handles that
automatically). You can inspect cost via the admin endpoints after running.
"""

import asyncio
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup: allow `uv run python scripts/try_refinement.py` from backend/
# ---------------------------------------------------------------------------
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

# ---------------------------------------------------------------------------
# Load .env before importing Settings (Pydantic Settings reads it at import)
# ---------------------------------------------------------------------------
from dotenv import load_dotenv  # pydantic-settings bundles python-dotenv

load_dotenv(_backend_root / ".env")

# ---------------------------------------------------------------------------
# Now import app modules (Settings will find its env vars)
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.refinement_service import refine_idea  # noqa: E402

# ---------------------------------------------------------------------------
# 5 diverse founder ideas — written as a founder would actually type them,
# NOT as polished one-liners. Messy, contextual, real.
# ---------------------------------------------------------------------------
FOUNDER_IDEAS = [
    # 1. B2B SaaS — operations / HR
    """\
We're building a tool for operations managers at mid-sized companies (50-500 employees)
who are drowning in ad-hoc Slack messages asking "what's the policy on X?". Every week
there are 20-30 questions like "can I expense this?", "what's the PTO carryover rule?",
"do we have a parental leave policy?" that should have answers in the handbook but the
handbook is a 200-page Google Doc nobody reads. Our idea is an AI that sits in Slack,
watches for those questions, and instantly drafts an answer from the actual company
policy documents — so ops managers don't have to manually answer the same questions
every week and employees get faster answers.
""",
    # 2. Consumer mobile — fitness / accountability
    """\
I want to make a fitness app specifically for people who keep starting and stopping
workout plans. The existing apps are full of features but nobody finishes anything.
My idea is super simple — you pick one habit per week, find a partner on the app who
has the same goal, and you both have to "check in" daily with a photo. If your partner
doesn't check in by 9pm, you both get charged $5 to a charity you chose at signup.
Loss aversion and social accountability combined. I've talked to 30 people and most of
them have tried at least 3 fitness apps and quit all of them.
""",
    # 3. Marketplace — freelance / creative economy
    """\
There's no good marketplace for short-form video editing freelancers. Fiverr and Upwork
are messy, over-indexed on web developers and logo designers, and the quality varies
wildly. I want to build a curated marketplace just for video editors who specialize in
social content (TikTok, Reels, YouTube Shorts). Brands and creators post a brief,
editors apply with a portfolio of short-form work, and we vet every editor before they
join. The model is project-based, not hourly, and we handle contracts and payments.
I've seen brand teams waste weeks going through 50 Upwork applications to find someone
who actually knows how to edit for social.
""",
    # 4. Developer tool — observability / debugging
    """\
I'm a backend engineer and my biggest daily frustration is that when a production bug
happens I spend 30-60 minutes jumping between Datadog, Sentry, our Postgres logs, and
Slack searching for context before I can even form a hypothesis. My idea is a tool that
sits on top of your existing observability stack (doesn't replace anything) and when
you paste in an error or incident ID, it automatically pulls the correlated logs,
recent deploys, database slow queries, and any related Sentry issues from the same
timeframe and puts them all in one scrollable timeline. Engineers already have all this
data, they just can't see it together fast enough.
""",
    # 5. Creator economy — monetization / newsletters
    """\
I write a weekly newsletter about personal finance for people in their 30s and I have
about 8,000 subscribers but I'm only making money from one sponsor per issue. The
problem is sponsorships are hard to sell, require minimum audience sizes most small
newsletters don't have, and I'm leaving money on the table because I know my readers
trust my recommendations. My idea is a platform that lets newsletter writers like me
monetize through "reader-matched affiliate deals" — the platform knows what financial
products my readers have clicked on before and surfaces relevant affiliate partnerships
I can include in my issues as genuine recommendations, not banner ads. Pay-per-click
revenue that doesn't require a sales relationship.
""",
]


def _print_separator(label: str = "") -> None:
    line = "=" * 72
    if label:
        print(f"\n{line}")
        print(f"  {label}")
        print(line)
    else:
        print(line)


def _print_refined_idea(idea_number: int, raw_idea: str, result) -> None:  # type: ignore[no-untyped-def]
    print(f"\n{'─' * 72}")
    print(f"RAW IDEA #{idea_number}:")
    print(raw_idea.strip())

    print(f"\n{'─' * 72}")
    print(f"REFINED OUTPUT #{idea_number}:")

    print(f"\n  ONE-LINER ({len(result.refined_one_liner)} chars):")
    print(f"    {result.refined_one_liner}")

    print(f"\n  TARGET AUDIENCE ({len(result.target_audience)} chars):")
    print(f"    {result.target_audience}")

    print(f"\n  VALUE PROPOSITION ({len(result.value_proposition)} chars):")
    print(f"    {result.value_proposition}")

    print(f"\n  RISKS ({len(result.risks)} items):")
    for i, risk in enumerate(result.risks, 1):
        print(f"    {i}. {risk}")

    print(f"\n  HEADLINE ({len(result.headline)} chars):")
    print(f"    {result.headline}")

    print(f"\n  SUBHEADLINE ({len(result.subheadline)} chars):")
    print(f"    {result.subheadline}")

    print(f"\n  CTA ({len(result.cta_text)} chars):")
    print(f"    {result.cta_text}")


async def main() -> None:
    settings = get_settings()

    # Optional CLI arg: 1-based index of a single idea to run.
    single_idx: int | None = None
    if len(sys.argv) > 1:
        try:
            single_idx = int(sys.argv[1])
        except ValueError:
            print(f"ERROR: argument must be an integer 1–{len(FOUNDER_IDEAS)}, got {sys.argv[1]!r}")
            sys.exit(1)
        if not (1 <= single_idx <= len(FOUNDER_IDEAS)):
            print(f"ERROR: index {single_idx} out of range — must be 1–{len(FOUNDER_IDEAS)}")
            sys.exit(1)

    # Slice to one idea when a specific index was requested.
    # Preserve original 1-based numbering in output by keeping (number, idea) pairs.
    if single_idx is not None:
        ideas_to_run = [(single_idx, FOUNDER_IDEAS[single_idx - 1])]
    else:
        ideas_to_run = list(enumerate(FOUNDER_IDEAS, 1))

    run_regen = single_idx is None  # regen round only when all 5 ran

    # Create a minimal engine for LLMCall logging.
    # Pool size 1: this is a single-user script, not a server.
    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    _print_separator("FIVVLE REFINEMENT PROMPT TESTER")
    print(f"Model: claude-sonnet-4-6   Ideas: {len(ideas_to_run)}")
    print("LLM calls will be logged to LLMCall table.")

    first_result = None

    try:
        for idx, raw_idea in ideas_to_run:
            try:
                async with session_factory() as db:
                    result = await refine_idea(db=db, raw_idea=raw_idea)
                    await db.commit()

                _print_refined_idea(idx, raw_idea, result)

                if idx == 1:
                    first_result = result

            except Exception as exc:  # noqa: BLE001
                print(f"\n  ERROR on idea #{idx}: {type(exc).__name__}: {exc}")

            if idx < ideas_to_run[-1][0]:
                await asyncio.sleep(1)

        # -----------------------------------------------------------------------
        # Regeneration test: take the first idea's refinement and ask Claude to
        # tighten the target audience description.
        # Only runs when all 5 ideas were processed (no single-idea CLI arg).
        # -----------------------------------------------------------------------
        if run_regen and first_result is not None:
            _print_separator("REGENERATION TEST — Idea #1 with feedback")
            print(
                "Feedback: 'Make the target audience more specific — what kind of "
                "operations managers exactly? What size company, what industry?'"
            )

            try:
                async with session_factory() as db:
                    regen_result = await refine_idea(
                        db=db,
                        raw_idea=FOUNDER_IDEAS[0],
                        previous_refinement=first_result,
                        feedback=(
                            "Make the target audience more specific — what kind of "
                            "operations managers exactly? What size company, what industry? "
                            "I want to see a vivid portrait, not a job title."
                        ),
                    )
                    await db.commit()

                _print_refined_idea(0, FOUNDER_IDEAS[0], regen_result)
                print(
                    "\n  DIFF CHECK — target audience changed from first pass?\n"
                    f"    BEFORE: {first_result.target_audience}\n"
                    f"    AFTER:  {regen_result.target_audience}"
                )

            except Exception as exc:  # noqa: BLE001
                print(f"\n  ERROR on regeneration test: {type(exc).__name__}: {exc}")

    finally:
        await engine.dispose()

    _print_separator("DONE")
    print("Inspect LLMCall rows via GET /admin/cost/daily for cost summary.")


if __name__ == "__main__":
    asyncio.run(main())
