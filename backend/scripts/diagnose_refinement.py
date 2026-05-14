"""Standalone diagnostic: runs one real refinement call and prints the full exception chain.

Run from backend/:
    uv run python scripts/diagnose_refinement.py

Requires:
    - ANTHROPIC_API_KEY in .env (loaded via python-dotenv)
    - Does NOT need the FastAPI server running.
    - Creates its own in-memory SQLite engine so it doesn't touch prod Postgres.
"""

from __future__ import annotations

import asyncio
import traceback
from decimal import Decimal

# Load .env so ANTHROPIC_API_KEY is available
from dotenv import load_dotenv

load_dotenv()

import instructor
import anthropic
from pydantic import ValidationError

from app.llm.prompts.refinement import REFINEMENT_SYSTEM_PROMPT, build_refinement_user_prompt
from app.schemas.refinement import RefinedIdea


RAW_IDEA = (
    "A B2B SaaS platform that helps e-commerce brands automatically detect "
    "and recover abandoned checkout sessions using AI-written personalised "
    "follow-up emails, SMS, and WhatsApp nudges. Integrates with Shopify, "
    "WooCommerce, and BigCommerce. Flat monthly fee plus revenue-share on "
    "recovered orders. Targets brands doing $50k–$2M GMV per month."
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
MAX_RETRIES = 1


async def main() -> None:
    client = anthropic.AsyncAnthropic()
    iclient = instructor.from_anthropic(client)

    user_prompt = build_refinement_user_prompt(raw_idea=RAW_IDEA)

    print(f"[diag] calling {MODEL} max_tokens={MAX_TOKENS} max_retries={MAX_RETRIES}")
    print("-" * 60)

    try:
        parsed, raw = await iclient.create_with_completion(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.4,
            max_retries=MAX_RETRIES,
            system=REFINEMENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            response_model=RefinedIdea,
        )
        print("[diag] SUCCESS")
        print(f"  stop_reason: {raw.stop_reason}")
        print(f"  input_tokens: {raw.usage.input_tokens}")
        print(f"  output_tokens: {raw.usage.output_tokens}")
        print(f"  refined_one_liner ({len(parsed.refined_one_liner)} chars): {parsed.refined_one_liner!r}")
        print(f"  target_audience ({len(parsed.target_audience)} chars): {parsed.target_audience!r}")
        print(f"  value_proposition ({len(parsed.value_proposition)} chars): {parsed.value_proposition!r}")
        print(f"  risks ({len(parsed.risks)} items):")
        for i, r in enumerate(parsed.risks):
            print(f"    [{i}] ({len(r)} chars) {r!r}")
        print(f"  headline ({len(parsed.headline)} chars): {parsed.headline!r}")
        print(f"  subheadline ({len(parsed.subheadline)} chars): {parsed.subheadline!r}")
        print(f"  cta_text ({len(parsed.cta_text)} chars): {parsed.cta_text!r}")

    except Exception as exc:
        print(f"[diag] FAILED: {type(exc).__name__}")
        print()

        # Print the full exception chain
        traceback.print_exc()
        print()

        # For InstructorRetryException, dig into last_attempt
        cause = exc
        depth = 0
        while cause is not None and depth < 10:
            print(f"[chain depth={depth}] {type(cause).__name__}: {str(cause)[:500]}")
            # Instructor wraps retries — check __cause__ and __context__
            next_cause = getattr(cause, "__cause__", None) or getattr(cause, "__context__", None)
            if next_cause is cause:
                break
            cause = next_cause
            depth += 1

        # Also check instructor-specific attributes
        if hasattr(exc, "last_attempt"):
            print(f"\n[diag] last_attempt: {exc.last_attempt}")
        if hasattr(exc, "errors"):
            print(f"\n[diag] errors: {exc.errors()}")
        if hasattr(exc, "n_attempts"):
            print(f"\n[diag] n_attempts: {exc.n_attempts}")


if __name__ == "__main__":
    asyncio.run(main())
