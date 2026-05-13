"""Searcher service — parallel Tavily fanout for the research engine.

Single public function: execute_search_plan().

Takes a ResearchPlan produced by the Planner phase and runs all search queries
for all questions in parallel via asyncio.gather(). Returns a dict mapping
question_id to a deduplicated list of TavilyResults.

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

Per AGENTS.md "Logging hygiene":
- NEVER log query text or scraped content — only metadata (counts, ids).
- NEVER log TavilyResult content — log only per-question result counts.

Per .cursorrules "LLM Calls":
- This service imports only from app.integrations.tavily — never imports
  the tavily SDK directly.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.integrations.tavily as tavily_client
from app.integrations.tavily import TavilyResult
from app.logging_config import get_logger
from app.schemas.planner import ResearchPlan

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


async def execute_search_plan(
    db: AsyncSession,
    research_plan: ResearchPlan,
    experiment_id: UUID | None = None,
) -> dict[str, list[TavilyResult]]:
    """Run all Tavily searches for a ResearchPlan in parallel.

    For each ResearchQuestion in the plan, runs all its search_queries
    concurrently. Deduplicates results by URL within each question's
    result set. Returns a mapping of question_id → deduplicated results.

    Parallelism: all (question, query) pairs launch simultaneously via a
    single asyncio.gather() call at the top level — NOT serial per question.
    With 7 questions × 2 queries average = ~14 parallel Tavily calls.

    Args:
        db: AsyncSession from the caller's context. The Tavily wrapper
            writes one ExternalAPICall row per search inside this session.
        research_plan: Validated ResearchPlan from the Planner phase.
            Contains 5-7 ResearchQuestions with 1-3 search_queries each.
        experiment_id: Optional FK for ExternalAPICall cost rollup.
            Pass the Experiment.id if available; None is valid for scripts.

    Returns:
        dict[str, list[TavilyResult]]: Maps question_id ("q1".."q7") to a
        deduplicated list of TavilyResults. Questions with partial failures
        receive whatever results succeeded; questions where ALL queries
        failed receive an empty list.

    Raises:
        SearcherFailure: if EVERY search across ALL questions fails.
            On partial failure, returns partial results instead of raising.
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

    return final_results
