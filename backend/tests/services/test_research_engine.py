"""Unit tests for app.services.research_engine.

Mocks Planner, Searcher, Reader, Reflector passthrough, and Synthesizer. Tests verify:
  1. Happy path: all phases succeed, returns ValidationReport
  2. Planner fails → ResearchEngineFailure phase="planner"
  3. Searcher fails → ResearchEngineFailure phase="searcher"
  4. Synthesizer fails → ResearchEngineFailure phase="synthesizer"
  5. experiment_id and rubric_version forwarded correctly

Pattern: patch each phase at app.services.research_engine.<name>.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import (
    Citation,
    Finding,
    QuestionFindings,
    ValidationReport,
)
from app.services.research_engine import (
    RUBRIC_VERSION_DEFAULT,
    ResearchEngineFailure,
    run_research_engine,
)
from app.services.searcher_service import SearcherFailure

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC)

_VALID_RISKS = [
    "Are ops managers already using Guru or Notion AI?",
    "Do HR teams have compliance concerns about AI bots?",
    "Is handbook staleness the real blocker?",
]


def _make_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="An AI Slack bot that answers HR policy questions.",
        target_audience=(
            "Operations managers at 50-500 person companies who spend 2-3 hours per "
            "week answering Slack messages about PTO rules and expense policies."
        ),
        value_proposition=(
            "Cuts the 2-3 hour weekly burden of answering repeat policy questions."
        ),
        risks=_VALID_RISKS,
        headline="Policy answers in Slack — without tagging ops",
        subheadline="Connect your handbook. The bot handles repeat questions.",
        cta_text="Join the waitlist",
    )


def _make_plan(question_count: int = 5) -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Test question {i}",
                rationale=f"Rationale for q{i}",
                search_queries=[f"query {i}"],
            )
            for i in range(1, question_count + 1)
        ]
    )


def _fake_reader_outputs() -> dict[str, ReaderOutput]:
    return {
        f"q{i}": ReaderOutput(
            question_id=f"q{i}",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url="https://example.com/article",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="stub",
                    named_entities=[],
                ),
            ],
            evidence_gap_note=None,
        )
        for i in range(1, 6)
    }


def _make_citation() -> Citation:
    return Citation(
        url="https://example.com/article",
        title="Test Article",
        source_domain="example.com",
        accessed_at=_NOW,
    )


def _make_finding(question_id: str = "q1") -> Finding:
    return Finding(
        question_id=question_id,
        claim="Guru provides Slack-based policy answering with 847 G2 reviews.",
        evidence_summary="Guru's G2 page confirms it.",
        citations=[_make_citation()],
        confidence="medium",
        confidence_rationale="Single G2 listing.",
    )


def _make_valid_report(question_count: int = 5) -> ValidationReport:
    qids = [f"q{i}" for i in range(1, question_count + 1)]
    return ValidationReport(
        executive_summary=(
            "Research confirms Guru and Notion AI compete. Handbook staleness confirmed. "
            "Recommendation is to iterate on a specific wedge before proceeding here."
        ),
        questions_and_findings=[
            QuestionFindings(
                question_id=qid,
                question=f"Question {qid}",
                findings=[_make_finding(qid)],
                evidence_gap=None,
            )
            for qid in qids
        ],
        competitors=[],
        market_signals="No reliable market-size data found in the search results.",
        distribution_signals=None,
        regulatory_signals=None,
        risks_assessment=(
            "The Guru risk is confirmed. Handbook staleness confirmed. "
            "Procurement partially confirmed from Reddit thread evidence."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms Guru covers the core. q1 shows differentiation in freshness."
        ),
        research_limitations="Market size data was not found in search results.",
        rubric_version_used="v1",
    )


async def _mock_execute_reflector_passthrough(**kwargs):
    """Keeps unit tests DB-free: real Reflector loads Experiment.refined_idea from DB."""
    return kwargs["reader_outputs"], kwargs["search_results"]


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_engine_happy_path() -> None:
    """All three phases succeed → returns the ValidationReport from synthesizer."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()
    mock_search_results = {f"q{i}": [] for i in range(1, 6)}
    mock_report = _make_valid_report()

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(return_value=mock_plan),
        ),
        patch(
            "app.services.research_engine.execute_search_plan",
            AsyncMock(return_value=mock_search_results),
        ),
        patch(
            "app.services.research_engine.execute_reader",
            AsyncMock(return_value=_fake_reader_outputs()),
        ),
        patch(
            "app.services.research_engine.execute_reflector",
            AsyncMock(side_effect=_mock_execute_reflector_passthrough),
        ),
        patch(
            "app.services.research_engine.synthesize_report",
            AsyncMock(return_value=mock_report),
        ),
    ):
        result = await run_research_engine(
            db=db, refined_idea=refined_idea
        )

    assert result is mock_report
    assert result.overall_recommendation == "iterate"


@pytest.mark.asyncio
async def test_run_research_engine_default_rubric_version() -> None:
    """Default rubric_version is RUBRIC_VERSION_DEFAULT ('v1')."""
    assert RUBRIC_VERSION_DEFAULT == "v1"

    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()
    mock_report = _make_valid_report()

    captured_rubric: list[str] = []

    async def _mock_synthesize(db, synth_input, citation_hydration_index, experiment_id=None):
        captured_rubric.append(synth_input.rubric_version)
        return mock_report

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(return_value=mock_plan),
        ),
        patch(
            "app.services.research_engine.execute_search_plan",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.services.research_engine.execute_reader",
            AsyncMock(return_value=_fake_reader_outputs()),
        ),
        patch(
            "app.services.research_engine.execute_reflector",
            AsyncMock(side_effect=_mock_execute_reflector_passthrough),
        ),
        patch(
            "app.services.research_engine.synthesize_report",
            _mock_synthesize,
        ),
    ):
        await run_research_engine(db=db, refined_idea=refined_idea)

    assert captured_rubric == [RUBRIC_VERSION_DEFAULT]


# ---------------------------------------------------------------------------
# 2. Planner fails → ResearchEngineFailure with phase="planner"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_engine_planner_failure() -> None:
    """If planner raises, run_research_engine wraps in ResearchEngineFailure phase='planner'."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()

    class _FakePlannerError(RuntimeError):
        pass

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(side_effect=_FakePlannerError("planner blew up")),
        ),
        pytest.raises(ResearchEngineFailure) as exc_info,
    ):
        await run_research_engine(db=db, refined_idea=refined_idea)

    err = exc_info.value
    assert err.phase == "planner"
    assert isinstance(err.cause, _FakePlannerError)
    assert "planner blew up" in str(err.cause)


# ---------------------------------------------------------------------------
# 3. Searcher fails with SearcherFailure → ResearchEngineFailure phase="searcher"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_engine_searcher_failure_wraps_searcher_failure() -> None:
    """SearcherFailure from execute_search_plan is wrapped in ResearchEngineFailure."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()

    searcher_err = SearcherFailure(
        question_count=5,
        query_count=10,
        first_error=RuntimeError("Tavily down"),
    )

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(return_value=mock_plan),
        ),
        patch(
            "app.services.research_engine.execute_search_plan",
            AsyncMock(side_effect=searcher_err),
        ),
        pytest.raises(ResearchEngineFailure) as exc_info,
    ):
        await run_research_engine(db=db, refined_idea=refined_idea)

    err = exc_info.value
    assert err.phase == "searcher"
    assert isinstance(err.cause, SearcherFailure)


# ---------------------------------------------------------------------------
# 4. Searcher fails with generic exception → ResearchEngineFailure phase="searcher"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_engine_searcher_generic_failure() -> None:
    """Generic exception from execute_search_plan wraps in ResearchEngineFailure."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()

    class _FakeNetworkError(ConnectionError):
        pass

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(return_value=mock_plan),
        ),
        patch(
            "app.services.research_engine.execute_search_plan",
            AsyncMock(side_effect=_FakeNetworkError("network failed")),
        ),
        pytest.raises(ResearchEngineFailure) as exc_info,
    ):
        await run_research_engine(db=db, refined_idea=refined_idea)

    err = exc_info.value
    assert err.phase == "searcher"
    assert isinstance(err.cause, _FakeNetworkError)


# ---------------------------------------------------------------------------
# 5. Synthesizer fails → ResearchEngineFailure with phase="synthesizer"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_engine_synthesizer_failure() -> None:
    """If synthesizer raises, run_research_engine wraps in ResearchEngineFailure."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()

    class _FakeSynthError(ValueError):
        pass

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(return_value=mock_plan),
        ),
        patch(
            "app.services.research_engine.execute_search_plan",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.services.research_engine.execute_reader",
            AsyncMock(return_value=_fake_reader_outputs()),
        ),
        patch(
            "app.services.research_engine.execute_reflector",
            AsyncMock(side_effect=_mock_execute_reflector_passthrough),
        ),
        patch(
            "app.services.research_engine.synthesize_report",
            AsyncMock(side_effect=_FakeSynthError("schema violation")),
        ),
        pytest.raises(ResearchEngineFailure) as exc_info,
    ):
        await run_research_engine(db=db, refined_idea=refined_idea)

    err = exc_info.value
    assert err.phase == "synthesizer"
    assert isinstance(err.cause, _FakeSynthError)


# ---------------------------------------------------------------------------
# 6. experiment_id and rubric_version forwarded to all phases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_research_engine_forwards_experiment_id_to_all_phases() -> None:
    """experiment_id is forwarded to plan_research, execute_search_plan, synthesize_report."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()
    mock_report = _make_valid_report()
    exp_id = uuid4()

    captured: dict[str, object] = {}

    async def _mock_plan(db, refined_idea, experiment_id=None):
        captured["planner_exp_id"] = experiment_id
        return mock_plan

    async def _mock_search(db, research_plan, experiment_id=None):
        captured["searcher_exp_id"] = experiment_id
        return {}

    async def _mock_reader(*, experiment_id, **kwargs):
        captured["reader_exp_id"] = experiment_id
        return _fake_reader_outputs()

    async def _mock_synth(db, synth_input, citation_hydration_index, experiment_id=None):
        captured["synthesizer_exp_id"] = experiment_id
        return mock_report

    with (
        patch("app.services.research_engine.plan_research", _mock_plan),
        patch("app.services.research_engine.execute_search_plan", _mock_search),
        patch("app.services.research_engine.execute_reader", _mock_reader),
        patch(
            "app.services.research_engine.execute_reflector",
            AsyncMock(side_effect=_mock_execute_reflector_passthrough),
        ),
        patch("app.services.research_engine.synthesize_report", _mock_synth),
    ):
        await run_research_engine(
            db=db, refined_idea=refined_idea, experiment_id=exp_id
        )

    assert captured["planner_exp_id"] == exp_id
    assert captured["searcher_exp_id"] == exp_id
    assert captured["reader_exp_id"] == exp_id
    assert captured["synthesizer_exp_id"] == exp_id


@pytest.mark.asyncio
async def test_run_research_engine_forwards_rubric_version() -> None:
    """Custom rubric_version is passed through to build_synthesizer_input."""
    db = AsyncMock(spec=AsyncSession)
    refined_idea = _make_refined_idea()
    mock_plan = _make_plan()
    mock_report = _make_valid_report()

    captured_rubric: list[str] = []

    async def _mock_synth(db, synth_input, citation_hydration_index, experiment_id=None):
        captured_rubric.append(synth_input.rubric_version)
        return mock_report

    with (
        patch(
            "app.services.research_engine.plan_research",
            AsyncMock(return_value=mock_plan),
        ),
        patch(
            "app.services.research_engine.execute_search_plan",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.services.research_engine.execute_reader",
            AsyncMock(return_value=_fake_reader_outputs()),
        ),
        patch(
            "app.services.research_engine.execute_reflector",
            AsyncMock(side_effect=_mock_execute_reflector_passthrough),
        ),
        patch("app.services.research_engine.synthesize_report", _mock_synth),
    ):
        await run_research_engine(
            db=db, refined_idea=refined_idea, rubric_version="v2"
        )

    assert captured_rubric == ["v2"]


# ---------------------------------------------------------------------------
# 7. ResearchEngineFailure exception structure
# ---------------------------------------------------------------------------


def test_research_engine_failure_phase_attribute() -> None:
    """ResearchEngineFailure stores phase and cause correctly."""
    cause = ValueError("test error")
    err = ResearchEngineFailure(phase="searcher", cause=cause)
    assert err.phase == "searcher"
    assert err.cause is cause
    assert "phase='searcher'" in str(err)
    assert "ValueError" in str(err)
