"""Searcher service — parallel Tavily fanout plus Google Trends for the research engine.

Single public function: execute_search_plan().

Takes a ResearchPlan produced by the Planner phase and runs all search queries
for all questions in parallel via asyncio.gather(). After Tavily completes,
fetches Google Trends once per pipeline (graceful-skip on failure). Returns
MergedSearchResults with per-question Tavily results and optional Trends signals.

Design choices:
- ALL (question, query) pairs are launched at the top level, not serially per
  question. With 7 questions × ~2 queries average = ~14 parallel calls. The
  Tavily circuit breaker already handles partial failures.
- Deduplication is per question: if two queries return the same URL for the same
  question, it collapses to one TavilyResult. URLs from different questions are
  not deduplicated across questions — the synthesizer benefits from seeing the
  same source appear across multiple question contexts.
- Partial failure tolerance: if some searches fail and others succeed, the
  service returns partial results and logs a warning. This matches the
  graceful-degradation policy in .cursorrules — "Tavily down: return partial
  results from sources that succeeded; mark report partial."
- Total failure: if ALL searches fail, raises SearcherFailure — a domain
  exception wrapping the first encountered error. The orchestrator catches
  this and wraps it in ResearchEngineFailure.
- Trends: one fetch_trends call per pipeline after Tavily; failures never raise.

Per AGENTS.md "Logging hygiene":
- NEVER log query text, keyword strings, or scraped content — only metadata.
- NEVER log TavilyResult content — log only per-question result counts.

Per .cursorrules "LLM Calls":
- External calls go through app.integrations — never import provider SDKs here.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.integrations.tavily as tavily_client
from app.integrations.tavily import TavilyResult
from app.integrations.trends import fetch_trends
from app.logging_config import get_logger
from app.schemas.planner import ResearchPlan
from app.schemas.refinement import RefinedIdea
from app.schemas.search import MergedSearchResults, TrendsSeries

_logger = get_logger(__name__)

# Per the spec: search_depth="advanced", max_results=5 per query.
# Advanced = 2 credits ($0.016) per call vs basic = 1 credit ($0.008).
# With 14 calls that's ~$0.22 in Tavily costs per engine run — within budget.
_SEARCH_DEPTH = "advanced"
_MAX_RESULTS_PER_QUERY = 5

# After URL-dedup, keep only the top N results per question sorted by Tavily
# score descending. With 7 questions × ~2 queries × 5 results each, dedup
# may leave up to ~10 results per question. Capping at 10 keeps synthesizer
# prompt size bounded without discarding useful evidence.
# Results with score=None are sorted to the bottom (treated as score=0.0).
_TOP_RESULTS_PER_QUESTION = 10

# pytrends hard limit (ADR 0015 / planning doc §4).
_MAX_TRENDS_KEYWORDS = 5

_STOP_WORDS = {
    "the",
    "a",
    "an",
    "for",
    "and",
    "or",
    "in",
    "on",
    "of",
    "to",
    "with",
    "is",
    "are",
    "how",
    "what",
    "why",
    "does",
    "do",
    "can",
}


def _shorten_to_trends_keyword(phrase: str, max_words: int = 3) -> str:
    """Extract a short, Trends-friendly keyword from a longer search phrase."""
    words = phrase.strip().split()
    trimmed = words[:max_words]
    while trimmed and trimmed[-1].lower().rstrip("?,.:") in _STOP_WORDS:
        trimmed.pop()
    return " ".join(trimmed)


class SearcherFailure(Exception):
    """Raised when ALL Tavily searches fail for a given plan.

    Wraps the first encountered error so the orchestrator has context.
    Only raised when every single (question, query) pair fails — partial
    failures are handled by returning partial results.
    """

    def __init__(self, question_count: int, query_count: int, first_error: Exception) -> None:
        self.question_count = question_count
        self.query_count = query_count
        self.first_error = first_error
        super().__init__(
            f"All {query_count} Tavily searches failed across {question_count} questions. "
            f"First error: {type(first_error).__name__}: {first_error}"
        )


def _extract_trends_keywords(
    research_plan: ResearchPlan,
    refined_idea: RefinedIdea | None,
) -> list[str]:
    """Build 1-5 short keyword phrases for Google Trends."""
    candidates: list[str] = []

    for question in research_plan.questions:
        candidates.extend(question.search_queries)

    if refined_idea is not None and hasattr(refined_idea, "target_audience"):
        audience = getattr(refined_idea, "target_audience", "")
        if audience:
            candidates.append(audience)

    seen: set[str] = set()
    keywords: list[str] = []
    for phrase in candidates:
        if not phrase:
            continue
        short = _shorten_to_trends_keyword(phrase)
        if len(short.split()) < 2 or len(short) > 40:
            continue
        key = short.casefold()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(short)
        if len(keywords) >= _MAX_TRENDS_KEYWORDS:
            break
    return keywords


async def _fetch_trends_graceful(
    db: AsyncSession,
    keywords: list[str],
    experiment_id: UUID | None,
) -> dict[str, TrendsSeries] | None:
    """Invoke fetch_trends once; never raise on Trends failure."""
    if not keywords:
        return None

    trends: dict[str, TrendsSeries] | None = None
    try:
        trends = await fetch_trends(db, keywords, experiment_id=experiment_id)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "searcher trends skipped — unexpected error",
            integration="trends",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id) if experiment_id else None,
        )
        trends = None

    _logger.info(
        "searcher trends completed",
        integration="trends",
        experiment_id=str(experiment_id) if experiment_id else None,
        keywords_count=len(keywords),
        trends_present=trends is not None and len(trends) > 0,
    )
    return trends


async def execute_search_plan(
    db: AsyncSession,
    research_plan: ResearchPlan,
    experiment_id: UUID | None = None,
    refined_idea: RefinedIdea | None = None,
) -> MergedSearchResults:
    """Run all Tavily searches for a ResearchPlan in parallel, then Google Trends once.

    For each ResearchQuestion in the plan, runs all its search_queries
    concurrently. Deduplicates results by URL within each question's
    result set. After Tavily completes, fetches Trends for a keyword bag
    derived from RefinedIdea (when provided) and plan search_queries.

    Parallelism: all (question, query) pairs launch simultaneously via a
    single asyncio.gather() call at the top level — NOT serial per question.
    With 7 questions × 2 queries average = ~14 parallel Tavily calls.

    Args:
        db: AsyncSession from the caller's context. Integration wrappers
            write ExternalAPICall rows inside this session.
        research_plan: Validated ResearchPlan from the Planner phase.
            Contains 5-7 ResearchQuestions with 1-3 search_queries each.
        experiment_id: Optional FK for ExternalAPICall cost rollup.
            Pass the Experiment.id if available; None is valid for scripts.
        refined_idea: Optional RefinedIdea for Trends keyword adaptation (ADR 0015).
            When omitted, keywords come from plan search_queries only.

    Returns:
        MergedSearchResults: tavily maps question_id to deduplicated TavilyResults;
        trends is a dict of TrendsSeries or None when Trends was skipped.

    Raises:
        SearcherFailure: if EVERY Tavily search across ALL questions fails.
            On partial Tavily failure, returns partial tavily results instead of raising.
            Trends failure never raises.
    """
    questions = research_plan.questions
    total_query_count = sum(len(q.search_queries) for q in questions)

    _logger.info(
        "searcher started",
        question_count=len(questions),
        total_query_count=total_query_count,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    # Build a flat list of (question_id, query) pairs for parallel dispatch.
    # Maintaining the question_id alongside lets us re-assemble results into
    # the per-question dict after gather completes.
    task_pairs: list[tuple[str, str]] = [
        (q.id, query)
        for q in questions
        for query in q.search_queries
    ]

    async def _run_single_search(
        question_id: str, query: str
    ) -> tuple[str, list[TavilyResult] | Exception]:
        """Run one Tavily search. Returns (question_id, results|exception)."""
        try:
            results = await tavily_client.search(
                db,
                query=query,
                experiment_id=experiment_id,
                max_results=_MAX_RESULTS_PER_QUERY,
                search_depth=_SEARCH_DEPTH,
            )
            return question_id, results
        except Exception as exc:  # noqa: BLE001
            return question_id, exc

    # Launch all searches in parallel.
    raw_outcomes: list[tuple[str, list[TavilyResult] | Exception]] = list(
        await asyncio.gather(
            *[_run_single_search(qid, q) for qid, q in task_pairs],
            return_exceptions=False,  # exceptions already captured in _run_single_search
        )
    )

    # Separate successes from failures.
    # Accumulate per-question results using URL-based deduplication.
    results_by_question: dict[str, dict[str, TavilyResult]] = {
        q.id: {} for q in questions
    }
    failures: list[Exception] = []

    for question_id, outcome in raw_outcomes:
        if isinstance(outcome, Exception):
            failures.append(outcome)
        else:
            url_map = results_by_question[question_id]
            for result in outcome:
                # Dedup by URL — first occurrence wins, which tends to have
                # the highest Tavily relevance score since queries are ordered
                # by score descending.
                if result.url not in url_map:
                    url_map[result.url] = result

    failure_count = len(failures)
    success_count = len(raw_outcomes) - failure_count

    # Total failure → raise SearcherFailure.
    if success_count == 0:
        first_err = failures[0]
        _logger.error(
            "searcher total failure — all searches failed",
            question_count=len(questions),
            total_query_count=total_query_count,
            failure_count=failure_count,
            first_error_type=type(first_err).__name__,
            experiment_id=str(experiment_id) if experiment_id else None,
        )
        raise SearcherFailure(
            question_count=len(questions),
            query_count=total_query_count,
            first_error=first_err,
        )

    # Partial failure → log warning, return what succeeded.
    if failure_count > 0:
        _logger.warning(
            "searcher partial failure — some searches failed",
            total_query_count=total_query_count,
            success_count=success_count,
            failure_count=failure_count,
            experiment_id=str(experiment_id) if experiment_id else None,
        )

    # Convert the per-question URL dicts to final lists.
    # Sort by Tavily score descending (None treated as 0.0) and keep top N.
    # This ensures the synthesizer always receives the most relevant results
    # and caps prompt size regardless of how many queries ran per question.
    total_unique_results = 0
    final_results: dict[str, list[TavilyResult]] = {}
    for qid, url_map in results_by_question.items():
        sorted_results = sorted(
            url_map.values(),
            key=lambda r: r.score if r.score is not None else 0.0,
            reverse=True,
        )
        top_n = sorted_results[:_TOP_RESULTS_PER_QUESTION]
        final_results[qid] = top_n
        total_unique_results += len(url_map)

    total_results_after_topn_filter = sum(len(v) for v in final_results.values())

    # Logging summary — counts only, no content per AGENTS.md.
    per_question_counts = {
        qid: len(results) for qid, results in final_results.items()
    }

    _logger.info(
        "searcher completed",
        question_count=len(questions),
        total_query_count=total_query_count,
        total_unique_results=total_unique_results,
        total_results_after_topn_filter=total_results_after_topn_filter,
        total_tavily_calls=len(raw_outcomes),
        total_failures=failure_count,
        per_question_result_counts=per_question_counts,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    trends_keywords = _extract_trends_keywords(research_plan, refined_idea)
    trends = await _fetch_trends_graceful(db, trends_keywords, experiment_id)

    return MergedSearchResults(tavily=final_results, trends=trends)
