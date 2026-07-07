"""Synthesizer prompt tests for Voices / v8."""

from __future__ import annotations

from app.llm.prompts.synthesizer import (
    PROMPT_NAME_V8_CACHED,
    SYNTHESIZER_ZONE_A_INSTRUCTIONS,
    build_synthesizer_v8_user_prompt,
)
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.refinement import RefinedIdea
from app.schemas.voices import VoicesEvidence, VoicesOutput
from app.services.synthesizer_input import build_synthesizer_input


def _flatten(text: str) -> str:
    return " ".join(text.split())


_VALID_RISKS = ["Risk one?", "Risk two?", "Risk three?"]


def _idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="India payroll SaaS",
        target_audience="HR at Indian startups",
        value_proposition="Automates compliance filings",
        risks=_VALID_RISKS,
        headline="Payroll without pain",
        subheadline="Built for India",
        cta_text="Join waitlist",
    )


def _plan() -> ResearchPlan:
    return ResearchPlan(
        questions=[
            ResearchQuestion(
                id=f"q{i}",
                question=f"Question {i}?",
                rationale="r",
                search_queries=[f"q{i}"],
            )
            for i in range(1, 6)
        ]
    )


def test_synthesizer_prompt_name_bumped_to_v8() -> None:
    assert PROMPT_NAME_V8_CACHED == "synthesizer_v8_cached"


def test_synthesizer_prompt_includes_voices_absence_rules_always() -> None:
    flat = _flatten(SYNTHESIZER_ZONE_A_INSTRUCTIONS)
    assert "voices_section_rules" in flat
    assert "subreddit_selection_returned_empty" in flat


def test_synthesizer_prompt_includes_voices_block_when_atoms_present() -> None:
    atom = VoicesEvidence(
        source_url="https://www.reddit.com/r/india/comments/x/",
        subreddit="india",
        kind="post",
        verbatim_quote="We need better payroll tools",
        pain_pattern="Founders struggle with payroll compliance.",
        on_target_geography=True,
        signal_strength="strong",
    )
    voices = VoicesOutput(
        atoms=[atom],
        subreddits_searched=["india"],
        threads_fetched=1,
        comments_fetched=0,
    )
    synth_input = build_synthesizer_input(
        refined_idea=_idea(),
        research_plan=_plan(),
        reader_outputs={},
        rubric_version="v1",
        voices_output=voices,
    )
    prompt = build_synthesizer_v8_user_prompt(synth_input, for_cache=False)
    flat = _flatten(prompt)
    assert "<voices_evidence>" in flat
    assert "We need better payroll tools" in flat


def test_synthesizer_prompt_includes_skip_metadata_when_empty() -> None:
    voices = VoicesOutput(
        atoms=[],
        skipped_reason="subreddit_selection_returned_empty",
    )
    synth_input = build_synthesizer_input(
        refined_idea=_idea(),
        research_plan=_plan(),
        reader_outputs={},
        rubric_version="v1",
        voices_output=voices,
    )
    prompt = build_synthesizer_v8_user_prompt(synth_input, for_cache=False)
    flat = _flatten(prompt)
    assert "voices_phase_result" in flat
    assert "subreddit_selection_returned_empty" in flat
