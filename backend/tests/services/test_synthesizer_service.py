"""Unit tests for app.services.synthesizer_service.

All LLM calls are mocked. Tests verify:
  1. synthesize_report() calls complete_structured with ValidationReportDraft
     response_model, correct max_tokens (16384), and other required args
  2. Service hydrates URL-string citations to full Citation objects from input
  3. Service raises SynthesizerHallucinatedCitation when LLM emits unknown URL
  4. Exception propagation: if complete_structured raises, synthesize_report re-raises
  5. None experiment_id is forwarded correctly
  6. Non-None experiment_id is forwarded correctly

Pattern: patch complete_structured at the service module's import reference:
    patch("app.services.synthesizer_service.llm_client.complete_structured", ...)
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import (
    Citation,
    CompetitorMentionDraft,
    Finding,
    FindingDraft,
    QuestionFindings,
    QuestionFindingsDraft,
    ValidationReport,
    ValidationReportDraft,
)
from app.services.synthesizer_input import SynthesizerInput, TavilyResultForPrompt
from app.services.synthesizer_service import (
    SynthesizerHallucinatedCitation,
    _SYNTHESIZER_MAX_TOKENS,
    _SYNTHESIZER_MODEL,
    _SYNTHESIZER_PROVIDER,
    _SYNTHESIZER_TEMPERATURE,
    synthesize_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=timezone.utc)

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


def _make_synth_input(question_count: int = 5) -> SynthesizerInput:
    """SynthesizerInput with one result per question at well-known URLs."""
    refined = _make_refined_idea()
    plan = _make_plan(question_count)
    results: dict[str, list[TavilyResultForPrompt]] = {
        f"q{i}": [
            TavilyResultForPrompt(
                url=f"https://example.com/result-q{i}",
                title=f"Result for q{i}",
                content_excerpt="Scraped excerpt.",
                score=0.9,
            )
        ]
        for i in range(1, question_count + 1)
    }
    return SynthesizerInput(
        refined_idea=refined,
        research_plan=plan,
        search_results_by_question=results,
        rubric_version="v1",
    )


def _make_citation(question_id: str = "q1") -> Citation:
    return Citation(
        url=f"https://example.com/result-{question_id}",
        title=f"Result for {question_id}",
        source_domain="example.com",
        accessed_at=_NOW,
    )


def _make_finding(question_id: str = "q1") -> Finding:
    return Finding(
        question_id=question_id,
        claim="Guru provides Slack-based policy answering with 847 G2 reviews.",
        evidence_summary="Guru's G2 page confirms it as the leading Slack knowledge tool.",
        citations=[_make_citation(question_id)],
        confidence="medium",
        confidence_rationale="Single G2 listing.",
    )


def _make_finding_draft(question_id: str = "q1") -> FindingDraft:
    """FindingDraft using the same URL that _make_synth_input() provides for this qid."""
    return FindingDraft(
        question_id=question_id,
        claim="Guru provides Slack-based policy answering with 847 G2 reviews.",
        evidence_summary="Guru's G2 page confirms it as the leading Slack knowledge tool.",
        citations=[f"https://example.com/result-{question_id}"],
        confidence="medium",
        confidence_rationale="Single G2 listing.",
    )


def _make_draft_report(question_count: int = 5) -> ValidationReportDraft:
    """ValidationReportDraft with URL-string citations matching _make_synth_input()."""
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


def _make_valid_report(question_count: int = 5) -> ValidationReport:
    qids = [f"q{i}" for i in range(1, question_count + 1)]
    return ValidationReport(
        executive_summary=(
            "Research confirms Guru and Notion AI directly compete with the proposed "
            "Slack HR bot. The handbook-staleness risk is evidenced by Reddit posts. "
            "Recommendation is to iterate on a specific wedge before proceeding."
        ),
        questions_and_findings=[
            QuestionFindings(
                question_id=qid,
                question=f"Test question {qid}",
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


def _make_mock_llm_result() -> MagicMock:
    meta = MagicMock()
    meta.prompt_tokens = 5000
    meta.completion_tokens = 2000
    meta.cost_usd = Decimal("0.045000")
    return meta


# ---------------------------------------------------------------------------
# 1. synthesize_report() calls complete_structured with correct args
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_report_calls_complete_structured_correctly() -> None:
    """synthesize_report() must forward ValidationReportDraft, max_tokens=16384, etc."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    mock_draft = _make_draft_report()
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(mock_draft, mock_meta))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await synthesize_report(db=db, synth_input=synth_input)

    # The service hydrates the draft → should return a full ValidationReport
    assert isinstance(result, ValidationReport)
    mock_complete.assert_awaited_once()

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["provider"] == _SYNTHESIZER_PROVIDER
    assert call_kwargs["model"] == _SYNTHESIZER_MODEL
    assert call_kwargs["prompt_name"] == "synthesizer_v1"
    assert call_kwargs["response_model"] is ValidationReportDraft
    assert call_kwargs["phase"] == "synthesizer"
    assert call_kwargs["max_retries"] == 2
    assert call_kwargs["max_tokens"] == _SYNTHESIZER_MAX_TOKENS
    assert call_kwargs["temperature"] == _SYNTHESIZER_TEMPERATURE


def test_synthesizer_service_constants() -> None:
    """Verify the module-level constants match the spec requirements."""
    from app.services.synthesizer_service import (
        _SYNTHESIZER_MAX_TOKENS,
        _SYNTHESIZER_MODEL,
        _SYNTHESIZER_PROVIDER,
        _SYNTHESIZER_TEMPERATURE,
    )

    assert _SYNTHESIZER_MODEL == "claude-sonnet-4-6"
    assert _SYNTHESIZER_PROVIDER == "anthropic"
    assert _SYNTHESIZER_MAX_TOKENS == 16384
    assert _SYNTHESIZER_TEMPERATURE == 0.3


# ---------------------------------------------------------------------------
# 2. Hydration: draft URL strings → full Citation objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_report_hydrates_url_citations() -> None:
    """synthesize_report() hydrates URL-string citations to full Citation objects."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(question_count=5)
    mock_draft = _make_draft_report(question_count=5)
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(mock_draft, mock_meta)),
    ):
        result = await synthesize_report(db=db, synth_input=synth_input)

    assert isinstance(result, ValidationReport)
    for qf in result.questions_and_findings:
        for f in qf.findings:
            assert len(f.citations) >= 1
            for c in f.citations:
                assert isinstance(c, Citation)
                assert c.url.startswith("https://")
                assert len(c.title) > 0
                assert len(c.source_domain) > 0
                assert c.accessed_at is not None


@pytest.mark.asyncio
async def test_synthesize_report_hydrates_correct_title_and_domain() -> None:
    """Hydrated Citations use title from the matching TavilyResultForPrompt."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(question_count=5)
    mock_draft = _make_draft_report(question_count=5)
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(mock_draft, mock_meta)),
    ):
        result = await synthesize_report(db=db, synth_input=synth_input)

    # The synth input has URLs like "https://example.com/result-q1" with
    # title "Result for q1". Verify the hydrated Citation carries those values.
    first_qf = result.questions_and_findings[0]
    first_citation = first_qf.findings[0].citations[0]
    assert first_citation.url == "https://example.com/result-q1"
    assert first_citation.title == "Result for q1"
    assert first_citation.source_domain == "example.com"


# ---------------------------------------------------------------------------
# 3. Hallucination detection: raises SynthesizerHallucinatedCitation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_report_raises_on_hallucinated_url() -> None:
    """synthesize_report() raises SynthesizerHallucinatedCitation for unknown URLs."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input(question_count=5)

    # Build a draft that cites a URL not in the synth_input results
    hallucinated_url = "https://hallucinated.com/fake-article-not-in-input"
    draft_with_hallucination = ValidationReportDraft(
        executive_summary=(
            "Research confirms Guru directly competes. Handbook staleness confirmed. "
            "Recommendation is to iterate on a narrower wedge before proceeding here."
        ),
        questions_and_findings=[
            QuestionFindingsDraft(
                question_id=f"q{i}",
                question=f"Test question q{i}",
                findings=[
                    FindingDraft(
                        question_id=f"q{i}",
                        claim="Guru provides Slack-based policy answering.",
                        evidence_summary="Guru's G2 page confirms leading Slack knowledge tool.",
                        citations=(
                            [hallucinated_url]
                            if i == 1
                            else [f"https://example.com/result-q{i}"]
                        ),
                        confidence="medium",
                        confidence_rationale="Single G2 listing evidence.",
                    )
                ],
                evidence_gap=None,
            )
            for i in range(1, 6)
        ],
        competitors=[],
        market_signals="No reliable TAM data found in the provided search results.",
        distribution_signals=None,
        regulatory_signals=None,
        risks_assessment=(
            "The Guru competitor risk is confirmed. Handbook staleness confirmed. "
            "Procurement complexity partially confirmed by one Reddit thread evidence."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms Guru covers the core use case. Iterate on freshness wedge."
        ),
        research_limitations="Market size data was not found in search results.",
        rubric_version_used="v1",
    )
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft_with_hallucination, mock_meta)),
    ):
        with pytest.raises(SynthesizerHallucinatedCitation) as exc_info:
            await synthesize_report(db=db, synth_input=synth_input)

    assert hallucinated_url in str(exc_info.value)
    assert exc_info.value.url == hallucinated_url


# ---------------------------------------------------------------------------
# 4. Exception propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_report_propagates_exceptions() -> None:
    """If complete_structured raises, synthesize_report must re-raise without catching."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()

    class _FakeAnthropicError(RuntimeError):
        pass

    mock_complete = AsyncMock(side_effect=_FakeAnthropicError("provider error"))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ), pytest.raises(_FakeAnthropicError, match="provider error"):
        await synthesize_report(db=db, synth_input=synth_input)


# ---------------------------------------------------------------------------
# 5. None experiment_id forwarded correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesize_report_forwards_none_experiment_id() -> None:
    """experiment_id=None must be forwarded to complete_structured as None."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    mock_draft = _make_draft_report()
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(mock_draft, mock_meta))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        await synthesize_report(db=db, synth_input=synth_input, experiment_id=None)

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] is None


@pytest.mark.asyncio
async def test_synthesize_report_forwards_experiment_id() -> None:
    """experiment_id value is forwarded to complete_structured."""
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    mock_draft = _make_draft_report()
    mock_meta = _make_mock_llm_result()
    exp_id = uuid4()

    mock_complete = AsyncMock(return_value=(mock_draft, mock_meta))

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        await synthesize_report(db=db, synth_input=synth_input, experiment_id=exp_id)

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] == exp_id
