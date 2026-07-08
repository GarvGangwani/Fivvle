"""Dev-loop harness for iterating on Voices phase logic.

Runs voices_service + Synthesizer against canned upstream artifacts and
canned Perplexity search results. Cost per iteration ~$0.10 (Voices LLM call +
Synthesizer LLM call). No live Perplexity calls.

Usage:
    uv run python -m scripts.voices_devloop.voices_devloop \\
        --upstream us_founder_platform --reddit full
    uv run python -m scripts.voices_devloop.voices_devloop \\
        --upstream us_founder_platform --reddit empty --print-voices-only
    uv run python -m scripts.voices_devloop.voices_devloop \\
        --upstream us_founder_platform --reddit partial --skip-synthesizer
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any
from unittest.mock import patch
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.session import init_engine
from app.integrations.perplexity import PerplexityResult
from app.services.research_engine import RUBRIC_VERSION_DEFAULT
from app.services.synthesizer_input import (
    build_synthesizer_input,
)
from app.services.synthesizer_service import synthesize_report
from app.services.voices_service import execute_voices
from scripts.voices_devloop.fixture_loader import (
    build_citation_index_for_harness,
    load_perplexity_results_by_subreddit,
    load_upstream,
    scratch_experiment_id,
)


def _subreddit_from_domain_filter(domain_filter: list[str] | None) -> str:
    if not domain_filter:
        return ""
    entry = domain_filter[0]
    prefix = "reddit.com/r/"
    if entry.startswith(prefix):
        return entry[len(prefix) :].lower()
    return ""


def _http_error(message: str) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.perplexity.ai/chat/completions")
    response = httpx.Response(403, request=request, text=message)
    return httpx.HTTPStatusError(message, request=request, response=response)


def _build_perplexity_patch(mode: str):
    fixtures = load_perplexity_results_by_subreddit(mode)

    async def _search(
        db: AsyncSession,
        *,
        query: str,
        experiment_id: UUID | None = None,
        domain_filter: list[str] | None = None,
        max_results: int = 10,
        timeout_s: int = 30,
    ) -> list[PerplexityResult]:
        del db, query, experiment_id, timeout_s
        if mode == "empty":
            raise _http_error("fixture empty mode")
        sub = _subreddit_from_domain_filter(domain_filter)
        if mode == "partial" and sub != "startups":
            raise _http_error("fixture partial miss")
        items = fixtures.get(sub, [])
        return items[:max_results]

    return _search


async def run_harness(
    *,
    upstream: str,
    reddit_mode: str,
    skip_synthesizer: bool,
    print_voices_only: bool,
    print_full_report: bool,
    override_model: str | None,
) -> dict[str, Any]:
    init_engine(get_settings())
    settings = get_settings()
    if override_model:
        settings = settings.model_copy(update={"voices_extraction_model": override_model})

    upstream_data = load_upstream(upstream)
    experiment_id = scratch_experiment_id()
    perplexity_search = _build_perplexity_patch(reddit_mode)

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    result: dict[str, Any] = {}
    try:
        async with sm() as db:
            with patch(
                "app.services.voices_service.perplexity_integration.search",
                side_effect=perplexity_search,
            ):
                voices_output = await execute_voices(
                    db=db,
                    refined_idea=upstream_data["refined_idea"],
                    research_plan=upstream_data["research_plan"],
                    targeting=upstream_data["targeting"],
                    experiment_id=experiment_id,
                    settings=settings,
                )
            result["voices_output"] = voices_output.model_dump(mode="json")

            if skip_synthesizer or print_voices_only:
                if print_voices_only:
                    print(json.dumps(result["voices_output"], indent=2))
                return result

            synth_input = build_synthesizer_input(
                refined_idea=upstream_data["refined_idea"],
                research_plan=upstream_data["research_plan"],
                reader_outputs=upstream_data["reader_outputs"],
                rubric_version=RUBRIC_VERSION_DEFAULT,
                evidence_analysis=upstream_data["evidence_analysis"],
                reasoning_output=upstream_data["reasoning_output"],
                targeting=upstream_data["targeting"],
                voices_output=voices_output,
                experiment_id=experiment_id,
            )
            citation_index = build_citation_index_for_harness(
                upstream_data["reader_outputs"],
                voices_output,
            )
            report = await synthesize_report(
                db=db,
                synth_input=synth_input,
                citation_hydration_index=citation_index,
                experiment_id=experiment_id,
            )
            result["validation_report"] = report.model_dump(mode="json")
            if print_full_report:
                print(json.dumps(result["validation_report"], indent=2))
            elif report.voices:
                print(report.voices)
    finally:
        await engine.dispose()

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Voices dev-loop harness")
    parser.add_argument(
        "--upstream",
        required=True,
        help="Fixture set name (e.g. us_founder_platform)",
    )
    parser.add_argument(
        "--reddit",
        required=True,
        choices=["full", "empty", "partial"],
        help="Perplexity fixture mode (legacy flag name)",
    )
    parser.add_argument("--skip-synthesizer", action="store_true")
    parser.add_argument("--print-voices-only", action="store_true")
    parser.add_argument("--print-full-report", action="store_true")
    parser.add_argument("--override-model", default=None)
    args = parser.parse_args(argv)

    asyncio.run(
        run_harness(
            upstream=args.upstream,
            reddit_mode=args.reddit,
            skip_synthesizer=args.skip_synthesizer,
            print_voices_only=args.print_voices_only,
            print_full_report=args.print_full_report,
            override_model=args.override_model,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
