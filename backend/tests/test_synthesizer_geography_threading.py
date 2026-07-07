"""Unit tests for geography/targeting threading in the synthesizer prompt."""

from __future__ import annotations

from app.db.enums import ExperimentStage
from app.llm.prompts.synthesizer import (
    PROMPT_NAME_V4_CACHED,
    PROMPT_NAME_V4_CACHED_LEGACY,
    PROMPT_NAME_V5_CACHED,
    PROMPT_NAME_V6_CACHED,
    PROMPT_NAME_V6_CACHED_LEGACY,
    PROMPT_NAME_V7_CACHED,
    SYNTHESIZER_ZONE_A_INSTRUCTIONS,
    build_synthesizer_v7_user_prompt,
)
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.targeting import ExperimentTargeting
from app.services.synthesizer_input import build_synthesizer_input

def _flatten(s: str) -> str:
    return " ".join(s.split())


_VALID_RISKS = [
    "Are incumbents already solving this in India?",
    "Do parents trust third-party fee comparisons?",
    "Will schools block scraping of fee data?",
]


def _make_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="A tool for Indian tier-1 families to compare school fees.",
        target_audience=(
            "Urban middle-class parents in Bengaluru comparing private school fees."
        ),
        value_proposition="Cuts weeks of school research into a single comparison view.",
        risks=_VALID_RISKS,
        headline="Compare school fees without ten browser tabs",
        subheadline="Built for tier-1 city parents weighing private school options.",
        cta_text="Join the waitlist",
    )


def _make_plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"What is the market size for school fee comparison in India (q{i})?",
                rationale="Sizes the opportunity.",
                search_queries=[f"India school fee market q{i}"],
            )
            for i in range(1, 6)
        ]
    )


def _make_reader_outputs() -> dict[str, ReaderOutput]:
    return {
        "q1": ReaderOutput(
            question_id="q1",
            extracted_evidence=[
                ExtractedEvidence(
                    source_url="https://example.com/india-schools",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="Indian private school market context.",
                    named_entities=["India"],
                ),
            ],
            evidence_gap_note=None,
        )
    }


def _full_targeting() -> ExperimentTargeting:
    return ExperimentTargeting(
        target_geography="India",
        audience_bracket="urban middle-class families",
        stage=ExperimentStage.BUILDING,
        why_now="Fee transparency regulation just passed.",
    )


def test_null_targeting_no_targeting_or_geography_rules() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(),
        reader_outputs=_make_reader_outputs(),
        rubric_version="v1",
        targeting=None,
    )
    prompt = build_synthesizer_v7_user_prompt(synth_input, for_cache=False)
    assert "<targeting>" not in prompt
    assert "<geography_scoping_rules" not in prompt


def test_full_targeting_blocks_present_in_correct_order() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(),
        reader_outputs=_make_reader_outputs(),
        rubric_version="v1",
        targeting=_full_targeting(),
    )
    prompt = build_synthesizer_v7_user_prompt(synth_input, for_cache=False)
    assert "<targeting>" in prompt
    assert '<geography_scoping_rules geography="India">' in prompt
    plan_idx = prompt.index("</research_plan>")
    targeting_idx = prompt.index("<targeting>")
    reader_idx = prompt.index("<reader_evidence_q1")
    geo_idx = prompt.index("<geography_scoping_rules")
    assert plan_idx < targeting_idx < geo_idx < reader_idx


def test_geography_rules_contain_proxy_sentence_template() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(),
        reader_outputs=_make_reader_outputs(),
        rubric_version="v1",
        targeting=ExperimentTargeting(target_geography="India"),
    )
    prompt = build_synthesizer_v7_user_prompt(synth_input, for_cache=False)
    assert "Using [US|global]" in prompt
    assert "India-specific market data was not found in this research" in prompt


def test_synthesizer_prompt_includes_defunct_filter_when_geography_set() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(),
        reader_outputs=_make_reader_outputs(),
        rubric_version="v1",
        targeting=ExperimentTargeting(target_geography="India"),
    )
    prompt = build_synthesizer_v7_user_prompt(synth_input, for_cache=False)
    flat = _flatten(prompt).lower()
    assert "exclude defunct products" in flat
    assert "a cancelled product is not a competitor" in flat


def test_synthesizer_prompt_includes_absence_rule_when_geography_set() -> None:
    synth_input = build_synthesizer_input(
        refined_idea=_make_refined_idea(),
        research_plan=_make_plan(),
        reader_outputs=_make_reader_outputs(),
        rubric_version="v1",
        targeting=ExperimentTargeting(target_geography="India"),
    )
    prompt = build_synthesizer_v7_user_prompt(synth_input, for_cache=False)
    flat = _flatten(prompt).lower()
    assert "state absence in market_signals" in flat
    assert "market_signals field must include" in flat
    assert "leave the competitors[] list empty" in flat
    assert (
        "no currently-shipping competitors operating in india were named in the "
        "research evidence"
    ) in flat


def test_prompt_includes_section_length_discipline() -> None:
    flat = _flatten(SYNTHESIZER_ZONE_A_INSTRUCTIONS).lower()
    assert "section length discipline" in flat
    assert "75-80%" in SYNTHESIZER_ZONE_A_INSTRUCTIONS


def test_prompt_includes_competitor_count_guidance() -> None:
    flat = _flatten(SYNTHESIZER_ZONE_A_INSTRUCTIONS).lower()
    assert "competitor count" in flat
    assert "typical 3-6, ceiling 10, floor 0" in flat


def test_synthesizer_prompt_name_bumped_to_v7() -> None:
    assert PROMPT_NAME_V7_CACHED == "synthesizer_v7_cached"
    assert PROMPT_NAME_V6_CACHED_LEGACY == "synthesizer_v6_cached"
    assert PROMPT_NAME_V6_CACHED == "synthesizer_v6_cached"
    assert PROMPT_NAME_V5_CACHED == "synthesizer_v5_cached"
    assert PROMPT_NAME_V4_CACHED_LEGACY == "synthesizer_v4_cached"
    assert PROMPT_NAME_V4_CACHED == "synthesizer_v4_cached"
