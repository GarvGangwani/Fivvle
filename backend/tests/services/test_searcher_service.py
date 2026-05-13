"""Unit tests for app.services.searcher_service.

All Tavily calls are mocked at module-import level via patch().

Tests:
  1.  Happy path: 7 questions × 2 queries each = 14 parallel calls, all succeed
  2.  Deduplication: same URL from two queries in same question collapses to one result
  3.  Partial failure: 2 calls fail, 12 succeed → partial results, logs warning, no raise
  4.  Total failure: all calls fail → raises SearcherFailure
  5.  experiment_id forwarding
  6.  Top-10 filter by score: 15 results per question (after dedup) → keeps top 10
  7.  score=None results are sorted to the bottom, not discarded

Pattern: patch the Tavily search function at the service module's import reference:
    patch("app.services.searcher_service.tavily_client.search", ...)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tavily import TavilyResult
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.services.searcher_service import SearcherFailure, execute_search_plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_question(id: str, query_count: int = 2) -> ResearchQuestion:
    return ResearchQuestion(
        id=id,
        question=f"Test question {id}",
        rationale=f"Rationale for {id}",
        search_queries=[f"{id} query {i}" for i in range(1, query_count + 1)],
    )


def _make_plan(question_count: int = 7, queries_per_question: int = 2) -> ResearchPlan:
    questions = [
        _make_question(f"q{i}", queries_per_question)
        for i in range(1, question_count + 1)
    ]
    return ResearchPlan(questions=questions)


def _make_tavily_result(url: str, title: str = "Title", score: float = 0.9) -> TavilyResult:
    return TavilyResult(
        title=title,
        url=url,
        content="Scraped content snippet for testing.",
        score=score,
    )


# ---------------------------------------------------------------------------
# 1. Happy path: 7 questions × 2 queries = 14 calls, all succeed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_happy_path() -> None:
    """14 parallel Tavily calls all succeed, returns per-question result dicts."""
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=7, queries_per_question=2)

    call_count = 0

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        nonlocal call_count
        call_count += 1
        # Return unique URL per call so dedup has nothing to do
        return [_make_tavily_result(f"https://example.com/result-{call_count}")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        results = await execute_search_plan(db=db, research_plan=plan)

    assert call_count == 14  # 7 questions × 2 queries
    assert len(results) == 7
    for qid in [f"q{i}" for i in range(1, 8)]:
        assert qid in results
        # 2 queries × 1 result each = 2 results per question (unique URLs)
        assert len(results[qid]) == 2


@pytest.mark.asyncio
async def test_execute_search_plan_passes_correct_args() -> None:
    """search() is called with search_depth='advanced' and max_results=5."""
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)

    call_args_list: list[dict] = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        call_args_list.append({"max_results": max_results, "search_depth": search_depth})
        return [_make_tavily_result("https://example.com/result")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        await execute_search_plan(db=db, research_plan=plan)

    assert len(call_args_list) == 5
    for args in call_args_list:
        assert args["max_results"] == 5
        assert args["search_depth"] == "advanced"


# ---------------------------------------------------------------------------
# 2. Deduplication: same URL from two queries in same question collapses to one
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_deduplicates_by_url() -> None:
    """Same URL returned by two queries for the same question collapses to one result."""
    db = AsyncMock(spec=AsyncSession)
    # Plan needs at least 5 questions; q1 has 2 queries, others have 1 each.
    plan = ResearchPlan(
        questions=[
            _make_question("q1", query_count=2),
            _make_question("q2", query_count=1),
            _make_question("q3", query_count=1),
            _make_question("q4", query_count=1),
            _make_question("q5", query_count=1),
        ]
    )

    duplicate_url = "https://example.com/same-article"
    unique_url_base = "https://example.com/unique"
    call_idx = 0

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        nonlocal call_idx
        call_idx += 1
        if "q1" in query:
            # Both q1 queries return the duplicate URL
            return [_make_tavily_result(duplicate_url, title="Same Article")]
        # Other questions return unique URLs
        return [_make_tavily_result(f"{unique_url_base}-{call_idx}")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        results = await execute_search_plan(db=db, research_plan=plan)

    # Two q1 calls, same URL → deduplicated to 1 result for q1
    assert len(results["q1"]) == 1
    assert results["q1"][0].url == duplicate_url


@pytest.mark.asyncio
async def test_execute_search_plan_no_dedup_across_questions() -> None:
    """Same URL appearing in different questions is NOT deduplicated across questions."""
    db = AsyncMock(spec=AsyncSession)
    plan = ResearchPlan(
        questions=[
            _make_question("q1", query_count=1),
            _make_question("q2", query_count=1),
            _make_question("q3", query_count=1),
            _make_question("q4", query_count=1),
            _make_question("q5", query_count=1),
        ]
    )

    shared_url = "https://example.com/shared-article"

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        return [_make_tavily_result(shared_url)]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        results = await execute_search_plan(db=db, research_plan=plan)

    # Each question gets its own result — not deduplicated across questions
    for qid in ["q1", "q2", "q3", "q4", "q5"]:
        assert len(results[qid]) == 1
        assert results[qid][0].url == shared_url


# ---------------------------------------------------------------------------
# 3. Partial failure: 2 calls fail, 12 succeed → returns partial, no raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_partial_failure() -> None:
    """Some searches fail, others succeed → returns partial results, no exception."""
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=7, queries_per_question=2)  # 14 total calls

    call_count = 0

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        nonlocal call_count
        call_count += 1
        # Fail on calls 3 and 7 (2 failures out of 14)
        if call_count in (3, 7):
            raise RuntimeError("Tavily network error")
        return [_make_tavily_result(f"https://example.com/result-{call_count}")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        # Should NOT raise — partial failure is tolerated
        results = await execute_search_plan(db=db, research_plan=plan)

    assert call_count == 14
    assert len(results) == 7  # all questions present in the mapping
    # Total results should be 12 (14 calls minus 2 failures)
    total = sum(len(v) for v in results.values())
    assert total == 12


# ---------------------------------------------------------------------------
# 4. Total failure: all calls fail → raises SearcherFailure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_total_failure_raises() -> None:
    """If every single Tavily call fails, SearcherFailure is raised."""
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=2)

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        raise RuntimeError("Tavily completely down")

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        with pytest.raises(SearcherFailure) as exc_info:
            await execute_search_plan(db=db, research_plan=plan)

    err = exc_info.value
    assert err.question_count == 5
    assert err.query_count == 10  # 5 questions × 2 queries
    assert isinstance(err.first_error, RuntimeError)


# ---------------------------------------------------------------------------
# 5. experiment_id forwarded to Tavily wrapper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_forwards_experiment_id() -> None:
    """experiment_id passed to execute_search_plan is forwarded to each search call."""
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)
    exp_id = uuid4()

    seen_experiment_ids: list = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        seen_experiment_ids.append(experiment_id)
        return [_make_tavily_result("https://example.com/r")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        await execute_search_plan(db=db, research_plan=plan, experiment_id=exp_id)

    assert all(eid == exp_id for eid in seen_experiment_ids)
    assert len(seen_experiment_ids) == 5


@pytest.mark.asyncio
async def test_execute_search_plan_forwards_none_experiment_id() -> None:
    """experiment_id=None is forwarded correctly (valid for script-level calls)."""
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)

    seen_experiment_ids: list = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        seen_experiment_ids.append(experiment_id)
        return [_make_tavily_result("https://example.com/r")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        await execute_search_plan(db=db, research_plan=plan, experiment_id=None)

    assert all(eid is None for eid in seen_experiment_ids)


# ---------------------------------------------------------------------------
# 6. Top-10 filtering by score descending (B2.3-fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_keeps_top_10_by_score() -> None:
    """After dedup, only the top 10 results per question (by score desc) are kept."""
    db = AsyncMock(spec=AsyncSession)
    # Plan with 5 questions, 3 queries each → potentially 15 results per question
    plan = _make_plan(question_count=5, queries_per_question=3)

    # Each call returns 5 results with distinct URLs and distinct scores.
    # We generate 15 unique results per question (3 calls × 5 results).
    call_count = 0

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        nonlocal call_count
        call_count += 1
        # Extract the question prefix from the query string (e.g. "q1 query 1" → "q1")
        qid = query.split(" ")[0]
        return [
            _make_tavily_result(
                f"https://example.com/{qid}/call{call_count}-result{j}",
                score=float(call_count * 10 + j),  # unique, increasing scores
            )
            for j in range(5)
        ]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        results = await execute_search_plan(db=db, research_plan=plan)

    # Each question had 15 results (3 calls × 5 results, all unique URLs).
    # After top-10 filter, each question should have exactly 10.
    for qid, q_results in results.items():
        assert len(q_results) == 10, (
            f"Expected 10 results for {qid} after top-10 filter, got {len(q_results)}"
        )


@pytest.mark.asyncio
async def test_execute_search_plan_top10_sorted_by_score_descending() -> None:
    """Results kept after top-10 filter are the highest-scoring ones."""
    db = AsyncMock(spec=AsyncSession)
    # Single question with 2 queries; each returns 5 results with known scores.
    plan = ResearchPlan(
        questions=[
            _make_question("q1", query_count=2),
            _make_question("q2", query_count=1),
            _make_question("q3", query_count=1),
            _make_question("q4", query_count=1),
            _make_question("q5", query_count=1),
        ]
    )

    # q1, call 1: scores 0.1, 0.2, 0.3, 0.4, 0.5
    # q1, call 2: scores 0.6, 0.7, 0.8, 0.9, 1.0  (all unique URLs)
    # Total 10 for q1 → all fit within top-10, no trimming
    # To test trimming: need >10 unique URLs for one question.
    # Use 3 queries × 5 results = 15 unique URLs for q1.
    plan2 = ResearchPlan(
        questions=[
            _make_question("q1", query_count=3),
            _make_question("q2", query_count=1),
            _make_question("q3", query_count=1),
            _make_question("q4", query_count=1),
            _make_question("q5", query_count=1),
        ]
    )

    q1_results_generated: list[TavilyResult] = []
    call_idx = 0

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        nonlocal call_idx
        call_idx += 1
        if "q1" in query:
            batch = [
                _make_tavily_result(
                    f"https://example.com/q1/r{call_idx}-{j}",
                    score=float(call_idx * 10 + j),
                )
                for j in range(5)
            ]
            q1_results_generated.extend(batch)
            return batch
        return [_make_tavily_result(f"https://example.com/other-{call_idx}")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        results = await execute_search_plan(db=db, research_plan=plan2)

    q1 = results["q1"]
    assert len(q1) == 10  # trimmed from 15

    # All returned results should have score ≥ the minimum score of the top-10.
    returned_scores = sorted([r.score for r in q1], reverse=True)
    all_scores = sorted(
        [r.score for r in q1_results_generated if r.score is not None], reverse=True
    )
    # The 10 returned results should have the top-10 scores.
    assert returned_scores == all_scores[:10]


# ---------------------------------------------------------------------------
# 7. score=None results sorted to the bottom (B2.3-fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_search_plan_none_score_sorted_to_bottom() -> None:
    """Results with score=None are treated as score=0.0 and sorted to the bottom."""
    db = AsyncMock(spec=AsyncSession)
    # Need enough unique results to trigger the top-10 cap (>10).
    # Use 3 queries × 5 results = 15 results. Include some with score=None.
    plan = ResearchPlan(
        questions=[
            _make_question("q1", query_count=3),
            _make_question("q2", query_count=1),
            _make_question("q3", query_count=1),
            _make_question("q4", query_count=1),
            _make_question("q5", query_count=1),
        ]
    )

    none_score_urls: list[str] = []
    call_idx = 0

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth):
        nonlocal call_idx
        call_idx += 1
        if "q1" in query:
            results = []
            for j in range(5):
                url = f"https://example.com/q1/c{call_idx}-r{j}"
                # First 5 results (call 1, j=0..4) get score=None
                score = None if call_idx == 1 else float(call_idx * 10 + j + 1)
                if score is None:
                    none_score_urls.append(url)
                results.append(_make_tavily_result(url, score=score))
            return results
        return [_make_tavily_result(f"https://example.com/other-{call_idx}")]

    with patch(
        "app.services.searcher_service.tavily_client.search",
        side_effect=_mock_search,
    ):
        results = await execute_search_plan(db=db, research_plan=plan)

    q1 = results["q1"]
    assert len(q1) == 10  # trimmed from 15

    # The 5 results with score=None should NOT be in the top-10 since there
    # are 10 results with positive scores to displace them.
    returned_urls = {r.url for r in q1}
    for none_url in none_score_urls:
        assert none_url not in returned_urls, (
            f"score=None result {none_url!r} should have been sorted out by top-10 filter"
        )
