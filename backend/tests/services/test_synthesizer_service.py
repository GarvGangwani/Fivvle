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
from app.llm.client import USER_CACHE_ZONE_BOUNDARY
from app.llm.prompts.synthesizer import (
    PROMPT_NAME_V2_CACHED,
    PROMPT_NAME_V3_CACHED,
    build_synthesizer_user_prompt,
    build_synthesizer_v3_user_prompt,
    synthesizer_v2_legacy_flat_user_and_system,
)
from app.schemas.search import TrendsPoint, TrendsSeries
from app.services.synthesizer_service import PROMPT_NAME
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import (
    Citation,
    FindingDraft,
    QuestionFindingsDraft,
    SectionScore,
    ValidationReport,
    ValidationReportDraft,
)
from app.config import get_settings
from app.services.synthesizer_input import (
    CitationHydrationEntry,
    SynthesizerInput,
    build_citation_hydration_index,
    build_synthesizer_input,
)
from app.services.synthesizer_service import (
    _SYNTHESIZER_MAX_TOKENS,
    _SYNTHESIZER_TEMPERATURE,
    SYNTHESIZER_CACHE_BREAKPOINTS,
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


def _default_section_scores() -> list[SectionScore]:
    return [
        SectionScore(
            section_id="market",
            label="Market demand",
            score=62,
            rationale="Demand signals are present but market-size data is limited.",
            pros=["G2/review activity suggests buyer interest."],
            cons=["No reliable TAM figure in search results."],
        ),
        SectionScore(
            section_id="competition",
            label="Competition",
            score=55,
            rationale="Named competitors overlap the core use case.",
            pros=["Competitor Guru is well documented with citations."],
            cons=["Differentiation gap appears narrow."],
        ),
        SectionScore(
            section_id="distribution",
            label="Distribution",
            score=48,
            rationale="Limited distribution evidence beyond generic channels.",
            pros=["Slack App Directory noted as a channel."],
            cons=["No validated acquisition playbook."],
        ),
        SectionScore(
            section_id="regulatory",
            label="Regulatory",
            score=70,
            rationale="No regulatory blockers surfaced for this category.",
            pros=["Low apparent compliance burden."],
            cons=["Regulatory depth was not fully investigated."],
        ),
        SectionScore(
            section_id="risk",
            label="Risk profile",
            score=58,
            rationale="Key risks are confirmed but not all are mitigated.",
            pros=["Handbook-staleness risk is evidenced."],
            cons=["Procurement complexity only partially confirmed."],
        ),
        SectionScore(
            section_id="research",
            label="Research depth",
            score=72,
            rationale="Most questions answered with cited findings.",
            pros=["Five research questions with medium+ confidence."],
            cons=["Some gaps on market sizing."],
        ),
    ]


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
        section_scores=_default_section_scores(),
        overall_score=61,
    )


def _make_mock_llm_meta() -> MagicMock:
    meta = MagicMock()
    meta.prompt_tokens = 5000
    meta.completion_tokens = 2000
    meta.cost_usd = Decimal("0.045000")
    meta.latency_ms = 12345
    return meta


def test_synthesizer_service_constants() -> None:
    settings = get_settings()
    assert settings.synthesizer_model == "kimi-k2.6"
    assert settings.synthesizer_provider == "kimi"
    assert _SYNTHESIZER_MAX_TOKENS == 16384
    assert _SYNTHESIZER_TEMPERATURE == 0.3


@pytest.mark.asyncio
async def test_synthesize_report_calls_complete_structured_with_synthesizer_v3() -> None:
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
    assert call_kwargs["prompt_name"] == PROMPT_NAME_V3_CACHED
    assert call_kwargs["prompt_name"] == PROMPT_NAME
    settings = get_settings()
    assert call_kwargs["provider"] == settings.synthesizer_provider
    assert call_kwargs["model"] == settings.synthesizer_model


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
    assert kwargs["prompt_name"] == PROMPT_NAME_V3_CACHED
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


# ---------------------------------------------------------------------------
# Prompt caching (synthesizer_v2_cached)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesizer_passes_cache_breakpoints_to_client() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    citation_hydration_index = _hydration_index()
    mock_draft = _make_draft_report()
    mock_meta = _make_mock_llm_meta()
    captured: dict = {}

    async def capture_complete(*_a, **kw):
        captured.update(kw)
        return mock_draft, mock_meta

    mock_complete = AsyncMock(side_effect=capture_complete)

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        mock_complete,
    ):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=citation_hydration_index,
        )

    bps = captured["cache_breakpoints"]
    assert bps is not None
    assert len(bps) == 2
    assert bps[0].position == "user_zone_a_end" and bps[0].ttl == "1h"
    assert bps[1].position == "user_zone_b_end" and bps[1].ttl == "5m"
    assert bps == SYNTHESIZER_CACHE_BREAKPOINTS


def test_synthesizer_v3_user_prompt_contains_zone_boundaries() -> None:
    synth_input = _make_synth_input(question_count=5)
    user = build_synthesizer_v3_user_prompt(synth_input, for_cache=True)
    assert user.count(USER_CACHE_ZONE_BOUNDARY) == 2
    zone_a, zone_b, zone_c = user.split(USER_CACHE_ZONE_BOUNDARY)
    assert "You are a market researcher at Fivvle" in zone_a
    assert "<refined_idea>" in zone_b and "<reader_evidence_q1" in zone_b
    assert zone_c == ""


def test_synthesizer_synthesizer_v2_cached_semantically_equivalent_to_v2() -> None:
    import re

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    synth_input = _make_synth_input(question_count=5)
    leg_sys, leg_user = synthesizer_v2_legacy_flat_user_and_system(synth_input)
    cached_user = build_synthesizer_user_prompt(synth_input, for_cache=True)
    flat = norm(cached_user.replace(USER_CACHE_ZONE_BOUNDARY, ""))
    assert norm(leg_sys) in flat
    assert norm(leg_user) in flat
    for anchor in (
        "ANTI-HALLUCINATION RULES",
        "SECURITY NOTICE — PROMPT INJECTION PROTECTION",
        "RECOMMENDATION DECISION RULES",
        "<task>",
        "verbatim_quote",
        "<closing_instruction>",
        "rubric_version_used",
    ):
        assert anchor in flat
    assert PROMPT_NAME_V2_CACHED == "synthesizer_v2_cached"


def _make_trends_signals() -> dict[str, TrendsSeries]:
    return {
        "foo": TrendsSeries(
            keyword="foo",
            points=[
                TrendsPoint(date="2024-01-01", value=20),
                TrendsPoint(date="2024-06-01", value=60),
            ],
        ),
    }


def test_synthesizer_v3_prompt_includes_trends_block_when_signals_populated() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(5),
        reader_outputs=_make_reader_outputs(5),
        rubric_version="v1",
        trends_signals=_make_trends_signals(),
    )
    prompt = build_synthesizer_v3_user_prompt(synth_input, for_cache=True)
    assert "<trends_signals>" in prompt
    assert "<trends_framing>" in prompt
    assert "<keyword>foo</keyword>" in prompt


def test_synthesizer_v3_prompt_discloses_unavailable_trends_when_signals_none() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(5),
        reader_outputs=_make_reader_outputs(5),
        rubric_version="v1",
        trends_signals=None,
    )
    prompt = build_synthesizer_v3_user_prompt(synth_input, for_cache=True)
    assert "<trends_signals>" not in prompt
    assert "<trends_framing>" in prompt
    assert "Trends signals indicate" not in prompt
    assert "research_limitations" in prompt
    assert (
        "demand-trajectory (search-interest) data could not be retrieved for this run"
        in prompt
    )
    assert "findings rest on the cited web sources alone" in prompt


def test_synthesizer_v3_prompt_discloses_unavailable_trends_when_signals_empty_dict() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(5),
        reader_outputs=_make_reader_outputs(5),
        rubric_version="v1",
        trends_signals={},
    )
    prompt = build_synthesizer_v3_user_prompt(synth_input, for_cache=True)
    assert "<trends_signals>" not in prompt
    assert "<trends_framing>" in prompt
    assert (
        "demand-trajectory (search-interest) data could not be retrieved for this run"
        in prompt
    )


@pytest.mark.asyncio
async def test_synthesizer_falls_back_when_cache_breakpoints_none() -> None:
    db = AsyncMock(spec=AsyncSession)
    synth_input = _make_synth_input()
    citation_hydration_index = _hydration_index()
    mock_draft = _make_draft_report()
    mock_meta = _make_mock_llm_meta()
    captured: dict = {}

    async def capture_complete(*_a, **kw):
        captured.update(kw)
        return mock_draft, mock_meta

    with patch(
        "app.services.synthesizer_service.llm_client.complete_structured",
        AsyncMock(side_effect=capture_complete),
    ):
        await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=citation_hydration_index,
            cache_breakpoints=None,
        )

    assert captured["cache_breakpoints"] is None
    assert USER_CACHE_ZONE_BOUNDARY not in captured["user"]
