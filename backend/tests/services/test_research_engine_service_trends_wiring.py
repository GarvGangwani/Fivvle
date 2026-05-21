"""Orchestrator wiring: trends_signals from Searcher → SynthesizerInput (ADR 0016)."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.search import MergedSearchResults, TrendsPoint, TrendsSeries
from app.services.research_engine_service import run_research_engine_pipeline
from app.services.synthesizer_input import build_synthesizer_input
from tests.routers.test_confirm_and_research_status import (
    _create_refined_experiment,
    _force_experiment_status,
    _sync_user,
)


def _run_pipeline(experiment_id_str: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    async def _go() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            await run_research_engine_pipeline(
                experiment_id=UUID(experiment_id_str),
                sessionmaker=sm,
            )
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_go())


def _minimal_plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Question {i}?",
                rationale="r",
                search_queries=[f"sq{i}"],
            )
            for i in range(1, 6)
        ]
    )


def _reader_ok() -> dict[str, ReaderOutput]:
    return {
        f"q{i}": ReaderOutput(
            question_id=f"q{i}",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url=f"https://example.com/r{i}",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="Evidence text.",
                    named_entities=[],
                ),
            ],
            evidence_gap_note=None,
        )
        for i in range(1, 6)
    }


def _fake_report() -> MagicMock:
    report = MagicMock()
    report.model_dump.return_value = {"version": "test"}
    report.questions_and_findings = []
    report.overall_recommendation = "proceed"
    return report


async def _reflector_passthrough(**kwargs: object) -> tuple[object, object, object]:
    from app.schemas.reflector import ReflectorPhaseSummary  # noqa: PLC0415

    summary = ReflectorPhaseSummary(
        loop_iteration=0,
        questions_flagged_count=0,
        questions_scheduled_count=0,
        decision_method="rule_v1",
        waves_used=0,
    )
    return kwargs["reader_outputs"], kwargs["search_results"], summary


def _trends_foo() -> TrendsSeries:
    return TrendsSeries(
        keyword="foo",
        points=[TrendsPoint(date="2024-06-01", value=42)],
    )


def test_orchestrator_passes_merged_trends_into_synthesizer_input(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    trends = {"foo": _trends_foo()}
    merged = MergedSearchResults(
        tavily={f"q{i}": [] for i in range(1, 6)},
        trends=trends,
    )

    captured_synth_input = {}

    async def capture_synthesize_report(*_a, **kw) -> MagicMock:
        captured_synth_input["synth_input"] = kw["synth_input"]
        return _fake_report()

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_minimal_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=merged),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_reader_ok()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflector_passthrough),
            )
        )
        mock_build = stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                wraps=build_synthesizer_input,
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                AsyncMock(side_effect=capture_synthesize_report),
            ),
        )
        _run_pipeline(exp_id)

    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs["trends_signals"] == trends
    assert captured_synth_input["synth_input"].trends_signals == trends
