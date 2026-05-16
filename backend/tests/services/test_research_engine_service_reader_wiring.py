"""Orchestrator wiring tests for B3 Reader (no real LLM).

Patches mirror ``test_research_engine_service.py``: pipeline lazy-imports pull
patched symbols from ``app.services.reader_service`` / ``synthesizer_service``.
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.services.reader_service import ReaderTotalFailure
from app.services.research_engine_service import run_research_engine_pipeline
from tests.routers.test_confirm_and_research_status import (
    _create_refined_experiment,
    _force_experiment_status,
    _read_experiment_fields,
    _sync_user,
)


async def _read_experiment_status_async(experiment_id_str: str) -> ExperimentStatus:
    """Read experiment.status without nested ``run_until_complete`` (pipeline is async)."""
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            row = (
                await session.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id_str))
                )
            ).scalar_one()
            return row.status
    finally:
        await engine.dispose()


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
    """Planner schema requires ≥5 questions."""
    questions = [
        ResearchQuestion(
            id=f"q{i}",
            question=f"Question {i}?",
            rationale="r",
            search_queries=[f"sq{i}"],
        )
        for i in range(1, 6)
    ]
    return ResearchPlan(questions=questions)


def _fake_report() -> MagicMock:
    report = MagicMock()
    report.model_dump.return_value = {"version": "test", "findings": []}
    report.questions_and_findings = []
    report.overall_recommendation = "proceed"
    return report


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


async def _reflector_passthrough(**kwargs: object) -> tuple[object, object]:
    """Passthrough matching ``execute_reflector`` keyword-only API (ADR 0013 wiring)."""
    return kwargs["reader_outputs"], kwargs["search_results"]


def test_orchestrator_transitions_to_research_reading_before_reader(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    async def execute_reader_side_effect(**kwargs: object) -> dict[str, ReaderOutput]:
        status = await _read_experiment_status_async(exp_id)
        assert status == ExperimentStatus.RESEARCH_READING
        return _reader_ok()

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
                AsyncMock(return_value={f"q{i}": [] for i in range(1, 6)}),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(side_effect=execute_reader_side_effect),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                AsyncMock(return_value=_fake_report()),
            )
        )
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_READY


def test_orchestrator_transitions_to_research_reflecting_after_reader(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    from app.services import research_engine_service as res_mod  # noqa: PLC0415

    status_log: list[ExperimentStatus] = []
    orig_set_status = res_mod._set_status

    async def tracking_set(
        session: AsyncSession,
        experiment_id: UUID,
        new_status: ExperimentStatus,
        *,
        error_detail: str | None = None,
    ) -> None:
        status_log.append(new_status)
        return await orig_set_status(session, experiment_id, new_status, error_detail=error_detail)

    expected_tail = [
        ExperimentStatus.RESEARCH_PLANNING,
        ExperimentStatus.RESEARCH_SEARCHING,
        ExperimentStatus.RESEARCH_READING,
        ExperimentStatus.RESEARCH_REFLECTING,
        ExperimentStatus.RESEARCH_SYNTHESIZING,
        ExperimentStatus.RESEARCH_READY,
    ]

    with ExitStack() as stack:
        stack.enter_context(patch.object(res_mod, "_set_status", new=tracking_set))
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_minimal_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value={f"q{i}": [] for i in range(1, 6)}),
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
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                AsyncMock(return_value=_fake_report()),
            )
        )
        _run_pipeline(exp_id)

    assert status_log[-len(expected_tail) :] == expected_tail


def test_orchestrator_handles_reader_total_failure_gracefully(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    synth_mock = AsyncMock(return_value=_fake_report())

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
                AsyncMock(return_value={f"q{i}": [] for i in range(1, 6)}),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(side_effect=ReaderTotalFailure("no evidence")),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch("app.services.synthesizer_service.synthesize_report", synth_mock),
        )
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    detail = fields["research_error_detail"] or ""
    assert detail.startswith("reader:")
    synth_mock.assert_not_called()


def test_orchestrator_handles_reader_unexpected_exception_gracefully(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    synth_mock = AsyncMock(return_value=_fake_report())

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
                AsyncMock(return_value={f"q{i}": [] for i in range(1, 6)}),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(side_effect=RuntimeError("unexpected")),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch("app.services.synthesizer_service.synthesize_report", synth_mock),
        )
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    assert fields["research_error_detail"] is not None
    assert (fields["research_error_detail"] or "").startswith("reader:")
    synth_mock.assert_not_called()
