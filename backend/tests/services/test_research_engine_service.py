"""State-machine unit tests for run_research_engine_pipeline (B2.4 / B3 Reader / Reflector).

Orchestration tests, all sync (asyncio.get_event_loop().run_until_complete pattern,
consistent with _force_experiment_status in the router tests):

  1. Happy path: planner + searcher + reader + synthesizer succeed → RESEARCH_READY.
  2. Planner exception → RESEARCH_FAILED with "planner:" prefix in detail.
  3. Searcher exception → RESEARCH_FAILED with "searcher:" prefix.
  4. Synthesizer exception → RESEARCH_FAILED with "synthesizer:" prefix.
  5. Synthesizer hallucinated citation → RESEARCH_FAILED with "synthesizer:" prefix.
  6. asyncio.TimeoutError at planner → detail contains "TimeoutError".
  7. API key planted in exception message → detail has "[REDACTED]", not the key.
  8. After planner failure, searcher is never called.

DB setup mirrors the router regression tests: create experiment via API
(LLM mocked → REFINED), force to RESEARCHING, then call the pipeline directly.
Pipeline stages are patched at their defining modules — the lazy imports inside
``run_research_engine_pipeline`` pick up the patches correctly.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import ExitStack

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.integrations.tavily import TavilyResult
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.search import MergedSearchResults
from app.schemas.reflector import ReflectorPhaseSummary
from app.services.research_engine_service import (
    _write_validation_report,
    run_research_engine_pipeline,
)
from app.services.synthesizer_service import SynthesizerHallucinatedCitation
from tests.routers.test_confirm_and_research_status import (
    _AUTH_HEADER,
    _create_refined_experiment,
    _force_experiment_status,
    _read_experiment_fields,
    _sync_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_pipeline(experiment_id_str: str) -> None:
    """Call run_research_engine_pipeline synchronously on a fresh event loop.

    Creates a dedicated async engine rather than reusing get_sessionmaker() so
    that every DB future belongs to the same event loop that run_until_complete
    drives.  This is identical in pattern to _force_experiment_status.
    """
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


def _fake_research_plan() -> MagicMock:
    """Minimal ResearchPlan stand-in — pipeline only reads .questions."""
    return MagicMock(questions=[])


def _merged_searcher_result(
    tavily: dict[str, list[TavilyResult]] | None = None,
) -> MergedSearchResults:
    """Searcher mock return shape after Commit 2 (MergedSearchResults)."""
    return MergedSearchResults(tavily=tavily or {}, trends=None)


def _fake_report() -> MagicMock:
    """Minimal ValidationReport stand-in for the synthesizer success path."""
    report = MagicMock()
    report.model_dump.return_value = {"version": "test", "findings": []}
    report.questions_and_findings = []
    report.overall_recommendation = "proceed"
    return report


async def _reflector_identity(**kwargs: object) -> tuple[object, object, object]:
    """Async passthrough matching execute_reflector's keyword-only API."""
    summary = ReflectorPhaseSummary(
        loop_iteration=0,
        questions_flagged_count=0,
        questions_scheduled_count=0,
        decision_method="rule_v1",
        waves_used=0,
    )
    return kwargs["reader_outputs"], kwargs["search_results"], summary


def _fake_reader_outputs() -> dict[str, ReaderOutput]:
    """Minimal Reader outputs so execute_reader aggregate extractions > 0 (B3)."""
    return {
        "stub_q": ReaderOutput(
            question_id="stub_q",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url="https://example.com/smoke",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="stub evidence",
                    named_entities=[],
                ),
            ],
            evidence_gap_note=None,
        ),
    }


# ---------------------------------------------------------------------------
# Each test calls _sync_user(client) + _create_refined_experiment(client)
# directly (same pattern as the router regression tests).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_happy_path_transitions_through_all_phases_to_ready(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Planner + searcher + reader + synthesizer all succeed → RESEARCH_READY in DB."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflector_identity),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        mock_synth = AsyncMock(return_value=_fake_report())
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                mock_synth,
            )
        )
        _run_pipeline(exp_id)

    mock_synth.assert_awaited_once()
    call_kw = mock_synth.await_args.kwargs
    assert "citation_hydration_index" in call_kw
    assert call_kw["citation_hydration_index"] == {}
    rs = client.get(f"/experiments/{exp_id}/research-status", headers=_AUTH_HEADER)
    assert rs.status_code == 200
    phases_json = rs.json().get("phases_completed") or []
    phase_labels = [str(p) for p in phases_json]
    assert any("RESEARCH_REFLECTING" in p for p in phase_labels), phase_labels
    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_READY
    assert fields["research_error_detail"] is None


# ---------------------------------------------------------------------------
# 2. Planner exception → RESEARCH_FAILED with "planner:" prefix
# ---------------------------------------------------------------------------


def test_planner_exception_sets_research_failed_with_planner_prefix(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Exception inside plan_research → RESEARCH_FAILED, detail starts with 'planner:'."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with patch(
        "app.services.planner_service.plan_research",
        AsyncMock(side_effect=RuntimeError("upstream LLM timeout")),
    ):
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    assert fields["research_error_detail"] is not None
    assert fields["research_error_detail"].startswith("planner:")


# ---------------------------------------------------------------------------
# 3. Searcher exception → RESEARCH_FAILED with "searcher:" prefix
# ---------------------------------------------------------------------------


def test_searcher_exception_sets_research_failed_with_searcher_prefix(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Exception inside execute_search_plan → RESEARCH_FAILED with 'searcher:' prefix."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(side_effect=RuntimeError("Tavily API 503")),
            )
        )
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    assert fields["research_error_detail"] is not None
    assert fields["research_error_detail"].startswith("searcher:")


# ---------------------------------------------------------------------------
# 4. Synthesizer exception → RESEARCH_FAILED with "synthesizer:" prefix
# ---------------------------------------------------------------------------


def test_synthesizer_exception_sets_research_failed_with_synthesizer_prefix(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Exception inside synthesize_report → RESEARCH_FAILED with 'synthesizer:' prefix."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflector_identity),
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
                AsyncMock(side_effect=RuntimeError("Anthropic overloaded")),
            )
        )
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    assert fields["research_error_detail"] is not None
    assert fields["research_error_detail"].startswith("synthesizer:")


# ---------------------------------------------------------------------------
# 4b. Synthesizer hallucinated citation → RESEARCH_FAILED with "synthesizer:"
# ---------------------------------------------------------------------------


def test_synthesizer_hallucinated_citation_sets_research_failed_with_synthesizer_prefix(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """SynthesizerHallucinatedCitation → RESEARCH_FAILED, detail starts with 'synthesizer:'."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflector_identity),
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
                AsyncMock(
                    side_effect=SynthesizerHallucinatedCitation(
                        "https://fabricated.example/x",
                        detail="Hallucinated citation URL 'https://fabricated.example/x'",
                    )
                ),
            )
        )
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    assert fields["research_error_detail"] is not None
    assert fields["research_error_detail"].startswith("synthesizer:")


# ---------------------------------------------------------------------------
# 5. asyncio.TimeoutError at planner → "TimeoutError" in detail
# ---------------------------------------------------------------------------


def test_timeout_error_sets_research_failed_with_timeout_in_detail(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """asyncio.TimeoutError propagating from plan_research is caught and annotated."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with patch(
        "app.services.planner_service.plan_research",
        AsyncMock(side_effect=TimeoutError()),
    ):
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    detail = fields["research_error_detail"] or ""
    assert "TimeoutError" in detail, f"Expected 'TimeoutError' in detail, got: {detail!r}"


# ---------------------------------------------------------------------------
# 6. Secret redaction — API key in exception message must not reach the DB
# ---------------------------------------------------------------------------


def test_error_detail_redacts_secrets_before_writing_to_db(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """A fake API key planted in an exception message must be redacted in DB.

    We temporarily inject a known fake secret into os.environ so
    _build_redaction_set() picks it up, then assert it is absent from the
    stored research_error_detail.
    """
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    fake_secret = "fake-anthropic-key-for-redaction-test-xyz"

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": fake_secret}), patch(
        "app.services.planner_service.plan_research",
        AsyncMock(
            side_effect=RuntimeError(f"Request failed: key={fake_secret}")
        ),
    ):
        _run_pipeline(exp_id)

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED
    detail = fields["research_error_detail"] or ""
    assert fake_secret not in detail, (
        f"Secret must not appear in error detail. Got: {detail!r}"
    )
    assert "[REDACTED]" in detail, f"Expected '[REDACTED]' placeholder. Got: {detail!r}"


# ---------------------------------------------------------------------------
# 7. Subsequent phases not called after planner failure
# ---------------------------------------------------------------------------


def test_subsequent_phases_not_called_after_planner_failure(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """When the planner raises, execute_search_plan must never be invoked."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    mock_searcher = AsyncMock(return_value=_merged_searcher_result())

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(side_effect=RuntimeError("planner broke")),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                mock_searcher,
            )
        )
        _run_pipeline(exp_id)

    mock_searcher.assert_not_called()

    fields = _read_experiment_fields(exp_id)
    assert fields["status"] == ExperimentStatus.RESEARCH_FAILED


# ---------------------------------------------------------------------------
# B3 Reflector orchestration wiring
# ---------------------------------------------------------------------------


def _read_validation_report_reflection_loops(experiment_id: str) -> int:
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.validation_report import ValidationReport  # noqa: PLC0415

    result: dict[str, int] = {}

    async def _run() -> None:
        engine = create_async_engine(
            get_settings().database_url, pool_size=1, max_overflow=0
        )
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                row = (
                    await session.execute(
                        select(ValidationReport.reflection_loops_used).where(
                            ValidationReport.experiment_id == UUID(experiment_id)
                        )
                    )
                ).scalar_one()
                result["value"] = row
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())
    return result["value"]


async def _reflect_merge_reader_outputs(
    **kwargs: object,
) -> tuple[object, object, object]:
    merged = dict(kwargs["reader_outputs"])  # type: ignore[arg-type]
    merged["stub_q"] = ReaderOutput(
        question_id="stub_q",
        extracted_evidence=[
            ExtractedEvidence(
                source_url="https://post-reflector.example/x",
                relevance="high",
                verbatim_quote=None,
                paraphrase="merged-paraphrase-marker",
                named_entities=[],
            ),
        ],
        evidence_gap_note=None,
    )
    summary = ReflectorPhaseSummary(
        loop_iteration=0,
        questions_flagged_count=0,
        questions_scheduled_count=0,
        decision_method="rule_v1",
        waves_used=0,
    )
    return merged, kwargs["search_results"], summary


async def _reflect_merge_search_results(
    **kwargs: object,
) -> tuple[object, object, object]:
    sr = dict(kwargs["search_results"])  # type: ignore[arg-type]
    sr["stub_q"] = [
        TavilyResult(
            title="post-reflector-row",
            url="https://post-reflector.example/hydrate-target",
            content="snippet-after-reflector",
        ),
    ]
    summary = ReflectorPhaseSummary(
        loop_iteration=0,
        questions_flagged_count=0,
        questions_scheduled_count=0,
        decision_method="rule_v1",
        waves_used=0,
    )
    return kwargs["reader_outputs"], sr, summary


async def _reflector_one_wave_summary(**kwargs: object) -> tuple[object, object, object]:
    summary = ReflectorPhaseSummary(
        loop_iteration=0,
        questions_flagged_count=5,
        questions_scheduled_count=4,
        decision_method="rule_v1",
        waves_used=1,
    )
    return kwargs["reader_outputs"], kwargs["search_results"], summary


@pytest.mark.asyncio
async def test_write_validation_report_persists_reflection_loops_used() -> None:
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415
    from app.db.models.user import User  # noqa: PLC0415
    from app.db.models.validation_report import ValidationReport  # noqa: PLC0415

    exp_id = uuid4()
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            user = User(
                firebase_uid=f"refl-loop-{exp_id}",
                email=f"refl-loop-{exp_id}@example.com",
                name="t",
            )
            session.add(user)
            await session.flush()
            session.add(
                Experiment(
                    id=exp_id,
                    user_id=user.id,
                    raw_idea="idea",
                    refined_idea={},
                    status=ExperimentStatus.RESEARCHING,
                )
            )
            await session.commit()

        async with sm() as session:
            await _write_validation_report(
                session,
                exp_id,
                {"version": "test"},
                reflection_loops_used=2,
            )
            await session.commit()

        async with sm() as session:
            stored = (
                await session.execute(
                    select(ValidationReport.reflection_loops_used).where(
                        ValidationReport.experiment_id == exp_id
                    )
                )
            ).scalar_one()
        assert stored == 2
    finally:
        await engine.dispose()


def test_orchestrator_calls_execute_reflector_between_reader_and_synthesizer(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """execute_reflector invoked once with orchestrator kwargs before synthesizer."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    mock_refl = AsyncMock(side_effect=_reflector_identity)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch("app.services.reflector_service.execute_reflector", mock_refl),
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        mock_synth = AsyncMock(return_value=_fake_report())
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                mock_synth,
            )
        )
        _run_pipeline(exp_id)

    mock_refl.assert_awaited_once()
    kw = mock_refl.await_args.kwargs
    assert set(kw.keys()) >= {
        "experiment_id",
        "research_plan",
        "reader_outputs",
        "search_results",
        "db",
        "settings",
    }
    mock_synth.assert_awaited_once()


def test_orchestrator_proceeds_to_synthesizer_when_reflector_pass_through(
    client: TestClient,
    mock_firebase: None,
) -> None:
    mock_build = MagicMock(return_value=MagicMock())

    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflector_identity),
            ),
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                mock_build,
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                AsyncMock(return_value=_fake_report()),
            )
        )
        _run_pipeline(exp_id)

    built_ro = mock_build.call_args.kwargs["reader_outputs"]
    assert built_ro["stub_q"].extracted_evidence[0].paraphrase == "stub evidence"


def test_orchestrator_uses_merged_reader_outputs_when_reflector_modifies(
    client: TestClient,
    mock_firebase: None,
) -> None:
    mock_build = MagicMock(return_value=MagicMock())

    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflect_merge_reader_outputs),
            ),
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                mock_build,
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                AsyncMock(return_value=_fake_report()),
            )
        )
        _run_pipeline(exp_id)

    merged_ro = mock_build.call_args.kwargs["reader_outputs"]
    assert merged_ro["stub_q"].extracted_evidence[0].paraphrase == (
        "merged-paraphrase-marker"
    )


def test_orchestrator_rebuilds_citation_hydration_index_after_reflector(
    client: TestClient,
    mock_firebase: None,
) -> None:
    hydration_calls: list[object] = []

    def capture_hydration(sr: object) -> dict[str, str]:
        hydration_calls.append(sr)
        return {"tracked": "yes"}

    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflect_merge_search_results),
            ),
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_synthesizer_input",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch(
                "app.services.synthesizer_input.build_citation_hydration_index",
                side_effect=capture_hydration,
            ),
        )
        mock_synth = AsyncMock(return_value=_fake_report())
        stack.enter_context(
            patch(
                "app.services.synthesizer_service.synthesize_report",
                mock_synth,
            )
        )
        _run_pipeline(exp_id)

    assert hydration_calls, "hydration index builder should run after reflector merge"
    last_sr = hydration_calls[-1]
    rows = last_sr["stub_q"]  # type: ignore[index]
    assert rows[0].url == "https://post-reflector.example/hydrate-target"
    idx_passed_to_synth = mock_synth.await_args.kwargs["citation_hydration_index"]
    assert idx_passed_to_synth == {"tracked": "yes"}


def test_orchestrator_persists_reflection_loops_used_from_reflector_summary(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """RESEARCH_READY upsert stores reflector_summary.waves_used, not hardcoded 0."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.planner_service.plan_research",
                AsyncMock(return_value=_fake_research_plan()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.searcher_service.execute_search_plan",
                AsyncMock(return_value=_merged_searcher_result()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reader_service.execute_reader",
                AsyncMock(return_value=_fake_reader_outputs()),
            )
        )
        stack.enter_context(
            patch(
                "app.services.reflector_service.execute_reflector",
                AsyncMock(side_effect=_reflector_one_wave_summary),
            ),
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

    assert _read_validation_report_reflection_loops(exp_id) == 1
