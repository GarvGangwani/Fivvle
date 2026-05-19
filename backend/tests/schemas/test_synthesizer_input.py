"""Schema tests for SynthesizerInput (ADR 0016 fifth field)."""

from __future__ import annotations

from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.search import TrendsPoint, TrendsSeries
from app.services.synthesizer_input import SynthesizerInput, build_synthesizer_input

_VALID_RISKS = [
    "Risk one?",
    "Risk two?",
    "Risk three?",
]


def _minimal_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="Test idea.",
        target_audience="Ops managers.",
        value_proposition="Saves time.",
        risks=_VALID_RISKS,
        headline="Headline",
        subheadline="Subheadline",
        cta_text="Join",
    )


def _minimal_plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Q{i}?",
                rationale="r",
                search_queries=[f"sq{i}"],
            )
            for i in range(1, 6)
        ]
    )


def _minimal_reader_outputs() -> dict[str, ReaderOutput]:
    return {
        f"q{i}": ReaderOutput(
            question_id=f"q{i}",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url=f"https://example.com/{i}",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="p",
                    named_entities=[],
                ),
            ],
            evidence_gap_note=None,
        )
        for i in range(1, 6)
    }


def _trends_fixture() -> dict[str, TrendsSeries]:
    return {
        "foo": TrendsSeries(
            keyword="foo",
            points=[
                TrendsPoint(date="2024-01-01", value=10),
                TrendsPoint(date="2024-06-01", value=50),
            ],
        ),
    }


def test_synthesizer_input_constructs_with_trends_signals_populated() -> None:
    trends = _trends_fixture()
    inp = SynthesizerInput(
        refined_idea=_minimal_refined_idea(),
        research_plan=_minimal_plan(),
        reader_outputs=_minimal_reader_outputs(),
        rubric_version="v1",
        trends_signals=trends,
    )
    assert inp.trends_signals == trends


def test_synthesizer_input_constructs_with_trends_signals_none_default() -> None:
    inp = SynthesizerInput(
        refined_idea=_minimal_refined_idea(),
        research_plan=_minimal_plan(),
        reader_outputs=_minimal_reader_outputs(),
        rubric_version="v1",
        trends_signals=None,
    )
    assert inp.trends_signals is None


def test_synthesizer_input_omitted_trends_signals_defaults_to_none() -> None:
    inp = SynthesizerInput(
        refined_idea=_minimal_refined_idea(),
        research_plan=_minimal_plan(),
        reader_outputs=_minimal_reader_outputs(),
        rubric_version="v1",
    )
    assert inp.trends_signals is None


def test_build_synthesizer_input_forwards_trends_signals() -> None:
    trends = _trends_fixture()
    inp = build_synthesizer_input(
        refined_idea=_minimal_refined_idea(),
        research_plan=_minimal_plan(),
        reader_outputs=_minimal_reader_outputs(),
        rubric_version="v1",
        trends_signals=trends,
    )
    assert inp.trends_signals == trends
