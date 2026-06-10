"""Regression: post-re-search path completes without TypeError (M-2 blocker).

Previously ``_partial_re_read`` omitted required ``_extract_for_question`` kwargs
(``refined_idea``, ``research_questions``, ``settings``), causing TypeError after
successful Tavily re-search and triggering the degrade invariant.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import app.services.reflector_service as reflector_mod
from app.integrations.tavily import TavilyResult
from app.llm.client import LLMResult
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ExtractedEvidenceDraft, ReaderOutput, ReaderOutputDraft
from app.schemas.refinement import RefinedIdea
from app.services.reflector_service import _RefinedQueryListDraft, execute_reflector


def _llm_meta() -> LLMResult:
    return LLMResult(
        text="{}",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt_tokens=50,
        completion_tokens=10,
        cost_usd=Decimal("0.02"),
        latency_ms=80,
    )


def _research_question(qid: str) -> ResearchQuestion:
    return ResearchQuestion(
        id=qid,
        question=f"Question for {qid}?",
        rationale="r",
        search_queries=["initial-query"],
    )


def _minimal_plan(question_ids: tuple[str, ...]) -> ResearchPlan:
    return ResearchPlan(
        questions=[_research_question(qid) for qid in question_ids],
        notes_for_synthesizer=None,
    )


def _atom(url: str, *, paraphrase: str = "p") -> ExtractedEvidence:
    return ExtractedEvidence(
        source_url=url,
        relevance="medium",
        verbatim_quote=None,
        paraphrase=paraphrase,
        named_entities=[],
    )


def _make_reader_output(
    qid: str,
    atoms: list[ExtractedEvidence],
    *,
    gap_note: str | None = None,
) -> ReaderOutput:
    return ReaderOutput(
        question_id=qid,
        extracted_evidence=atoms,
        evidence_gap_note=gap_note,
    )


def _minimal_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="Reflect typeerror repro fixture.",
        target_audience="Understaffed hospitals evaluating nurse tooling.",
        value_proposition="Faster shift handoffs with structured notes.",
        risks=[
            "Do incumbent EMR tools already cover this workflow?",
            "Will procurement block Slack-connected bots?",
            "Can night-shift adoption succeed without admin buy-in?",
        ],
        headline="Handoffs without hallway chasing",
        subheadline="Structured nurse notes synced safely.",
        cta_text="Join waitlist",
    )


def _make_error_printer(orig_error):
    def _print_logged_exc_info(*args, **kwargs):
        if kwargs.get("exc_info") is True:
            import traceback

            traceback.print_exc()
        return orig_error(*args, **kwargs)

    return _print_logged_exc_info


@pytest.mark.asyncio
async def test_execute_reflector_post_research_path_completes_without_typeerror() -> None:
    """Force re-search + real _extract_for_question; must not hit degrade path."""
    plan = _minimal_plan(("q1", "q2", "q3", "q4", "q5"))
    outputs = {
        "q1": _make_reader_output("q1", [], gap_note="still unknown"),
        **{
            q.id: _make_reader_output(
                q.id,
                [
                    _atom(f"https://a{q.id}.com/1"),
                    _atom(f"https://b{q.id}.com/2"),
                    _atom(f"https://c{q.id}.com/3"),
                ],
            )
            for q in plan.questions[1:]
        },
    }
    sr_in: dict[str, list[TavilyResult]] = {}
    fresh_url = "https://fresh.example/n"
    fresh_row = TavilyResult(
        title="fresh",
        url=fresh_url,
        content="fresh content slice for reader",
        score=0.9,
    )

    async def fake_tavily_search(
        db,  # noqa: ARG001
        *,
        query,  # noqa: ARG001
        experiment_id,  # noqa: ARG001
        max_results,  # noqa: ARG001
        search_depth,  # noqa: ARG001
    ) -> list[TavilyResult]:
        return [fresh_row]

    refinement_draft = _RefinedQueryListDraft(queries=["refined query one"])
    reader_draft = ReaderOutputDraft(
        question_id="q1",
        extracted_evidence=[
            ExtractedEvidenceDraft(
                source_url=fresh_url,
                relevance="high",
                verbatim_quote=None,
                paraphrase="extracted from fresh hit",
                named_entities=[],
            ),
        ],
    )

    async def fake_complete_structured(_db, **_kwargs):
        response_model = _kwargs.get("response_model")
        if response_model is _RefinedQueryListDraft:
            return refinement_draft, _llm_meta()
        if response_model is ReaderOutputDraft:
            return reader_draft, _llm_meta()
        raise AssertionError(f"unexpected response_model={response_model!r}")

    settings = MagicMock()
    settings.reflector_max_refinement_waves = 1

    with (
        patch(
            "app.services.reflector_service._load_refined_idea_for_reader",
            AsyncMock(return_value=_minimal_refined_idea()),
        ),
        patch(
            "app.services.reflector_service.tavily_client.search",
            AsyncMock(side_effect=fake_tavily_search),
        ),
        patch(
            "app.llm.client.complete_structured",
            AsyncMock(side_effect=fake_complete_structured),
        ),
        patch.object(
            reflector_mod._logger,
            "error",
            side_effect=_make_error_printer(reflector_mod._logger.error),
        ),
    ):
        ro_out, sr_out, summary = await execute_reflector(
            experiment_id=uuid4(),
            research_plan=plan,
            reader_outputs=outputs,
            search_results=sr_in,
            db=MagicMock(spec=[]),
            settings=settings,
        )

    assert summary.waves_used == 1
    assert "q1" in ro_out
    assert ro_out["q1"].extracted_evidence
    assert ro_out["q1"].extracted_evidence[0].source_url == fresh_url
    assert any(r.url == fresh_url for r in sr_out.get("q1", []))
