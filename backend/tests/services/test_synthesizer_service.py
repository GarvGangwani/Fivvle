"""Unit tests for app.services.synthesizer_service.

All LLM calls are mocked. Covers ADR 0012 hand-off: reader_outputs allow-list,
citation_hydration_index hydration, observability, and exception propagation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tavily import TavilyResult
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import (
    Citation,
    FindingDraft,
    QuestionFindingsDraft,
    ValidationReport,
    ValidationReportDraft,
)
from app.services.synthesizer_input import (
    CitationHydrationEntry,
    SynthesizerInput,
    build_citation_hydration_index,
    build_synthesizer_input,
)
from app.services.synthesizer_service import (
    _SYNTHESIZER_MAX_TOKENS,
    _SYNTHESIZER_MODEL,
    _SYNTHESIZER_PROVIDER,
    _SYNTHESIZER_TEMPERATURE,
    SynthesizerHallucinatedCitation,
    synthesize_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC)

_VALID_RISKS = [
    "Are ops managers already using Guru or Notion AI to answer policy questions?",
    "Do HR teams have compliance concerns about AI bots citing PTO policies?",
    "Is handbook staleness the real blocker — making the bot answer incorrectly?",
]


def _make_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="An AI Slack bot that answers HR policy questions from your handbook.",
        target_audience=(
            "Operations managers at 50-500 person companies who spend 2-3 hours per "
            "week answering Slack messages about PTO rules and expense policies."
        ),
        value_proposition=(
            "Cuts the 2-3 hour weekly ops-manager burden of answering repeat policy "
            "questions by routing them to an AI that reads the actual handbook."
        ),
        risks=_VALID_RISKS,
        headline="Policy answers in Slack — without tagging ops every time",
        subheadline=(
            "Connect your handbook. The bot handles repeat questions automatically."
        ),
        cta_text="Join the waitlist",
    )


def _make_plan(question_count: int = 5) -> ResearchPlan:
    questions = [
        ResearchQuestion(
            id=f"q{i}",
            question=f"Test question {i}",
            rationale=f"Rationale for q{i}",
            search_queries=[f"query for q{i}"],
        )
        for i in range(1, question_count + 1)
    ]
    return ResearchPlan(questions=questions)


def _make_reader_outputs(question_count: int = 5) -> dict[str, ReaderOutput]:
    return {
        f"q{i}": ReaderOutput(
            question_id=f"q{i}",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url=f"https://example.com/result-q{i}",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="Stub paraphrase.",
                    named_entities=[],
                ),
            ],
            evidence_gap_note=None,
        )
        for i in range(1, question_count + 1)
    }


def _make_synth_input(question_count: int = 5) -> SynthesizerInput:
    return build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(question_count),
        reader_outputs=_make_reader_outputs(question_count),
        rubric_version="v1",
    )


def _make_search_results(question_count: int = 5) -> dict[str, list[TavilyResult]]:
    return {
        f"q{i}": [
            TavilyResult(
                title=f"Result for q{i}",
                url=f"https://example.com/result-q{i}",
                content="Searcher snippet.",
                score=0.9,
            ),
        ]
        for i in range(1, question_count + 1)
    }


def _hydration_index(question_count: int = 5) -> dict[str, CitationHydrationEntry]:
    return build_citation_hydration_index(_make_search_results(question_count))


def _make_finding_draft(question_id: str = "q1") -> FindingDraft:
    return FindingDraft(
        question_id=question_id,
        claim="Guru provides Slack-based policy answering with 847 G2 reviews.",
        evidence_summary="Guru's G2 page confirms it as the leading Slack knowledge tool.",
        citations=[f"https://example.com/result-{question_id}"],
        confidence="medium",
        confidence_rationale="Single G2 listing.",
    )


def _make_draft_report(question_count: int = 5) -> ValidationReportDraft:
    qids = [f"q{i}" for i in range(1, question_count + 1)]
    return ValidationReportDraft(
        executive_summary=(
            "Research confirms Guru and Notion AI directly compete with the proposed "
            "Slack HR bot. The handbook-staleness risk is evidenced by Reddit posts. "
            "Recommendation is to iterate on a specific wedge before proceeding."
        ),
        questions_and_findings=[
            QuestionFindingsDraft(
                question_id=qid,
                question=f"Test question {qid}",
                findings=[_make_finding_draft(qid)],
                evidence_gap=None,
            )
            for qid in qids
        ],
        competitors=[],
        market_signals="No reliable market-size data found in the search results.",
        distribution_signals=None,
        regulatory_signals=None,
        risks_assessment=(
            "The Guru competitor risk (q2) is confirmed. Handbook staleness (q1) confirmed. "
            "Procurement (q4) partially confirmed by one Reddit thread evidence."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms Guru covers the core use case. q1 shows the differentiation "
            "is in freshness guarantees, not search. Iterate on the always-current wedge."
        ),
        research_limitations="Market size data was not found in search results.",
        rubric_version_used="v1",
    )


def _make_mock_llm_meta() -> MagicMock:
    meta = MagicMock()
    meta.prompt_tokens = 5000
    meta.completion_tokens = 2000
    meta.cost_usd = Decimal("0.045000")
    meta.latency_ms = 12345
    return meta


def test_synthesizer_service_constants() -> None:
    assert _SYNTHESIZER_MODEL == "claude-sonnet-4-6"
    assert _SYNTHESIZER_PROVIDER == "anthropic"
    assert _SYNTHESIZER_MAX_TOKENS == 16384
    assert _SYNTHESIZER_TEMPERATURE == 0.3


@pytest.mark.asyncio
async def test_synthesize_report_calls_complete_structured_with_synthesizer_v2() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    citation_hydration_index = _hydration_index()
    mock_draft = _make_draft_report()
    mock_meta = _make_mock_llm_meta()
    mock_complete = AsyncMock(return_value=(mock_draft, mock_meta))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=citation_hydration_index,
        )

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["prompt_name"] == "synthesizer_v2"
    assert call_kwargs["provider"] == _SYNTHESIZER_PROVIDER
    assert call_kwargs["model"] == _SYNTHESIZER_MODEL


@pytest.mark.asyncio
async def test_synthesize_report_builds_allowed_urls_from_reader_outputs() -> None:
    db = AsyncMock(spec=AsyncSession)
    allowed_url = "https://allowed.example/article"
    reader_outputs = _make_reader_outputs(5)
    reader_outputs["q1"] = ReaderOutput(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidence(
                source_url=allowed_url,
                relevance="high",
                verbatim_quote=None,
                paraphrase="x",
                named_entities=[],
            ),
        ],
        evidence_gap_note=None,
    )
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(5),
        reader_outputs=reader_outputs,
        rubric_version="v1",
    )
    index = build_citation_hydration_index(_make_search_results(5))
    index[allowed_url] = CitationHydrationEntry(title="T", source_domain="allowed.example")

    draft = _make_draft_report(5)
    draft.questions_and_findings[0].findings[0].citations = [allowed_url]

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _make_mock_llm_meta())),
    ):
        result = await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=index,
        )

    assert isinstance(result, ValidationReport)
    assert result.questions_and_findings[0].findings[0].citations[0].url == allowed_url


@pytest.mark.asyncio
async def test_synthesize_report_raises_when_citation_url_not_in_reader_outputs() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(question_count=5)
    bad_url = "https://hallucinated.com/fake"
    draft = _make_draft_report(question_count=5)
    draft.questions_and_findings[0].findings[0].citations = [bad_url]

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _make_mock_llm_meta())),
    ), pytest.raises(SynthesizerHallucinatedCitation) as exc_info:
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=_hydration_index(5),
        )

    assert exc_info.value.url == bad_url
    assert "questions_and_findings" in str(exc_info.value)


@pytest.mark.asyncio
async def test_synthesize_report_raises_when_url_passes_guard_but_missing_from_index() -> (
    None
):
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(5)
    draft = _make_draft_report(5)

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _make_mock_llm_meta())),
    ), pytest.raises(SynthesizerHallucinatedCitation, match="hydration index"):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index={},
        )


@pytest.mark.asyncio
async def test_synthesize_report_hydrates_citation_title_and_domain_from_index() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(5)
    url = "https://example.com/result-q1"
    index = _hydration_index(5)
    index[url] = CitationHydrationEntry(title="Indexed Title", source_domain="example.com")
    mock_draft = _make_draft_report(5)

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(mock_draft, _make_mock_llm_meta())),
    ):
        result = await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=index,
        )

    cit = result.questions_and_findings[0].findings[0].citations[0]
    assert isinstance(cit, Citation)
    assert cit.title == "Indexed Title"
    assert cit.source_domain == "example.com"


@pytest.mark.asyncio
async def test_synthesize_report_truncates_long_titles_to_citation_cap() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(5)
    url = "https://example.com/result-q1"
    long_title = "A" * 400
    index = _hydration_index(5)
    index[url] = CitationHydrationEntry(title=long_title, source_domain="example.com")
    mock_draft = _make_draft_report(5)

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(mock_draft, _make_mock_llm_meta())),
    ):
        result = await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=index,
        )

    cit = result.questions_and_findings[0].findings[0].citations[0]
    assert len(cit.title) == 300
    assert cit.title == long_title[:300]


@pytest.mark.asyncio
async def test_synthesize_report_emits_synthesizer_complete_info_log() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(5)
    index = _hydration_index(5)
    mock_draft = _make_draft_report(5)
    mock_meta = _make_mock_llm_meta()

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(mock_draft, mock_meta)),
    ), patch("app.services.synthesizer_service._logger.info") as mock_info:
        exp_id = uuid4()
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=index,
            experiment_id=exp_id,
        )

    complete_calls = [
        c
        for c in mock_info.call_args_list
        if len(c.args) > 0 and c.args[0] == "synthesizer complete"
    ]
    assert len(complete_calls) == 1
    kwargs = complete_calls[0].kwargs
    assert kwargs["prompt_name"] == "synthesizer_v2"
    assert kwargs["experiment_id"] == str(exp_id)
    assert kwargs["total_extracted_evidence_in_input"] == 5
    assert kwargs["finding_count"] == 5
    assert kwargs["competitor_count"] == 0
    assert kwargs["total_citation_count"] == 5
    assert kwargs["recommendation"] == "iterate"
    assert kwargs["cost_usd"] == str(mock_meta.cost_usd)
    assert kwargs["prompt_tokens"] == mock_meta.prompt_tokens
    assert kwargs["completion_tokens"] == mock_meta.completion_tokens
    assert kwargs["latency_ms"] == mock_meta.latency_ms


@pytest.mark.asyncio
async def test_synthesize_report_propagates_llm_exception() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()

    class _FakeAnthropicError(RuntimeError):
        pass

    mock_complete = AsyncMock(side_effect=_FakeAnthropicError("provider error"))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ), pytest.raises(_FakeAnthropicError, match="provider error"):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=_hydration_index(),
        )


@pytest.mark.asyncio
async def test_synthesize_report_forwards_none_experiment_id() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    mock_complete = AsyncMock(return_value=(_make_draft_report(), _make_mock_llm_meta()))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=_hydration_index(),
            experiment_id=None,
        )

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] is None


@pytest.mark.asyncio
async def test_synthesize_report_forwards_experiment_id() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    exp_id = uuid4()
    mock_complete = AsyncMock(return_value=(_make_draft_report(), _make_mock_llm_meta()))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=_hydration_index(),
            experiment_id=exp_id,
        )

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] == exp_id
