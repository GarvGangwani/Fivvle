"""H-3 semantic equivalence: synthesizer_v3_cached matches v2 when trends_signals is None."""

from __future__ import annotations

from app.llm.client import USER_CACHE_ZONE_BOUNDARY
from app.llm.prompts.synthesizer import (
    build_synthesizer_user_prompt,
    build_synthesizer_v3_user_prompt,
)
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.services.synthesizer_input import build_synthesizer_input

_VALID_RISKS = [
    "Are ops managers already using Guru?",
    "Do HR teams have compliance concerns?",
    "Is handbook staleness the real blocker?",
]


def _make_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="An AI Slack bot that answers HR policy questions.",
        target_audience="Operations managers at 50-500 person companies.",
        value_proposition="Cuts weekly burden of answering repeat policy questions.",
        risks=_VALID_RISKS,
        headline="Policy answers in Slack",
        subheadline="Connect your handbook.",
        cta_text="Join the waitlist",
    )


def _make_plan(question_count: int = 5) -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Test question {i}",
                rationale=f"Rationale for q{i}",
                search_queries=[f"query for q{i}"],
            )
            for i in range(1, question_count + 1)
        ]
    )


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


def test_v3_cached_user_prompt_byte_identical_to_v2_when_trends_signals_none() -> None:
    """ADR 0016: absent Trends must not change Zone B or add Zone C content."""
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(5),
        reader_outputs=_make_reader_outputs(5),
        rubric_version="v1",
        trends_signals=None,
    )
    v2_prompt = build_synthesizer_user_prompt(synth_input, for_cache=True)
    v3_prompt = build_synthesizer_v3_user_prompt(synth_input, for_cache=True)
    assert v3_prompt == v2_prompt
    assert v3_prompt.count(USER_CACHE_ZONE_BOUNDARY) == 2
