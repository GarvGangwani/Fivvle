"""Tests that execute_search_plan wires geography hint service correctly."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tavily import TavilyResult
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.targeting import ExperimentTargeting
from app.services.searcher_service import execute_search_plan


def _make_plan(question_count: int = 7, queries_per_question: int = 3) -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Test question {i}",
                rationale=f"Rationale {i}",
                search_queries=[
                    f"market size query {j}" if j == 1 else f"generic query {j}"
                    for j in range(1, queries_per_question + 1)
                ],
            )
            for i in range(1, question_count + 1)
        ]
    )


def _tavily_result() -> TavilyResult:
    return TavilyResult(
        title="Title",
        url="https://example.com/article",
        content="snippet",
        score=0.9,
    )


@contextmanager
def _patch_searcher(tavily_side_effect) -> Iterator[None]:
    with (
        patch(
            "app.services.searcher_service.tavily_client.search",
            side_effect=tavily_side_effect,
        ),
        patch(
            "app.services.searcher_service.fetch_trends",
            AsyncMock(return_value=None),
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_null_targeting_does_not_call_hint_service() -> None:
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)
    tavily_calls: list[dict] = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth, include_domains=None):
        tavily_calls.append({"include_domains": include_domains})
        return [_tavily_result()]

    with (
        patch(
            "app.services.geography_hint_service.get_include_domains_for_geography",
            AsyncMock(),
        ) as mock_hints,
        _patch_searcher(_mock_search),
    ):
        await execute_search_plan(db=db, research_plan=plan, targeting=None)

    mock_hints.assert_not_called()
    assert all("include_domains" not in c or c["include_domains"] is None for c in tavily_calls)


@pytest.mark.asyncio
async def test_empty_hint_list_omits_include_domains_kwarg() -> None:
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)
    targeting = ExperimentTargeting(target_geography="Brazil")
    tavily_calls: list[dict] = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth, include_domains=None):
        tavily_calls.append({"include_domains": include_domains, "query": query})
        return [_tavily_result()]

    with (
        patch(
            "app.services.geography_hint_service.get_include_domains_for_geography",
            AsyncMock(return_value=[]),
        ),
        _patch_searcher(_mock_search),
    ):
        await execute_search_plan(
            db=db,
            research_plan=plan,
            targeting=targeting,
        )

    geo_sensitive_calls = [c for c in tavily_calls if "market" in c["query"]]
    assert geo_sensitive_calls
    assert all(c["include_domains"] is None for c in geo_sensitive_calls)


@pytest.mark.asyncio
async def test_geo_sensitive_query_gets_include_domains() -> None:
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)
    plan.questions[0] = ResearchQuestion(
        id="q1",
        question="Market?",
        rationale="r",
        search_queries=["india market size tam"],
    )
    targeting = ExperimentTargeting(target_geography="India")
    hints = ["livemint.com", "inc42.com", "rbi.org.in"]
    captured: list[dict] = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth, include_domains=None):
        if "market size tam" in query:
            captured.append({"include_domains": include_domains})
        return [_tavily_result()]

    with (
        patch(
            "app.services.geography_hint_service.get_include_domains_for_geography",
            AsyncMock(return_value=hints),
        ),
        _patch_searcher(_mock_search),
    ):
        await execute_search_plan(db=db, research_plan=plan, targeting=targeting)

    assert len(captured) == 1
    assert captured[0]["include_domains"] == hints


@pytest.mark.asyncio
async def test_non_geo_sensitive_query_omits_include_domains() -> None:
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=5, queries_per_question=1)
    plan.questions[0] = ResearchQuestion(
        id="q1",
        question="Tech?",
        rationale="r",
        search_queries=["how blockchain consensus works"],
    )
    targeting = ExperimentTargeting(target_geography="India")
    captured: list[dict] = []

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth, include_domains=None):
        if "blockchain consensus" in query:
            captured.append({"include_domains": include_domains})
        return [_tavily_result()]

    with (
        patch(
            "app.services.geography_hint_service.get_include_domains_for_geography",
            AsyncMock(return_value=["livemint.com"]),
        ),
        _patch_searcher(_mock_search),
    ):
        await execute_search_plan(db=db, research_plan=plan, targeting=targeting)

    assert len(captured) == 1
    assert captured[0]["include_domains"] is None


@pytest.mark.asyncio
async def test_hint_service_called_once_per_pipeline_run() -> None:
    db = AsyncMock(spec=AsyncSession)
    plan = _make_plan(question_count=7, queries_per_question=3)
    targeting = ExperimentTargeting(target_geography="India")

    async def _mock_search(db, *, query, experiment_id, max_results, search_depth, include_domains=None):
        return [_tavily_result()]

    mock_hints = AsyncMock(return_value=["livemint.com"])

    with (
        patch(
            "app.services.geography_hint_service.get_include_domains_for_geography",
            mock_hints,
        ),
        _patch_searcher(_mock_search),
    ):
        await execute_search_plan(db=db, research_plan=plan, targeting=targeting)

    mock_hints.assert_awaited_once()
