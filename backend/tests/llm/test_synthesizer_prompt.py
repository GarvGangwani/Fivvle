"""Regression tests for the synthesizer prompt module (synthesizer_v2).

Guards prompt structure after ADR 0012: Reader-only evidence in user prompt,
PROMPT_NAME bump, and security framing.
"""

from __future__ import annotations

import pytest

from app.llm.prompts.synthesizer import (
    PROMPT_NAME,
    SYNTHESIZER_SYSTEM_PROMPT,
    build_synthesizer_user_prompt,
)
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.services.synthesizer_input import SynthesizerInput, build_synthesizer_input

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
                question=f"Does tool q{i} solve the core use case?",
                rationale=f"Critical for q{i} evaluation.",
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
                    source_url=f"https://example.com/q{i}-article",
                    relevance="high",
                    verbatim_quote=None,
                    paraphrase="Evidence about the topic.",
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


# ---------------------------------------------------------------------------
# 1. PROMPT_NAME
# ---------------------------------------------------------------------------


def test_prompt_name_is_synthesizer_v2() -> None:
    assert PROMPT_NAME == "synthesizer_v2"


# ---------------------------------------------------------------------------
# 2. SYNTHESIZER_SYSTEM_PROMPT is non-empty
# ---------------------------------------------------------------------------


def test_synthesizer_system_prompt_is_non_empty() -> None:
    assert SYNTHESIZER_SYSTEM_PROMPT
    assert len(SYNTHESIZER_SYSTEM_PROMPT.strip()) > 0


# ---------------------------------------------------------------------------
# 3. SYNTHESIZER_SYSTEM_PROMPT contains required markers
# ---------------------------------------------------------------------------

_REQUIRED_SYSTEM_PROMPT_MARKERS = [
    "citation",
    "untrusted",
    "SPECIFICITY OVER SUMMARY",
    "proceed",
    "iterate",
    "pivot",
    "kill",
    "too_vague_to_recommend",
    "generic market language",
    "QuestionFindings",
    "confidence_rationale",
    "CompetitorMention",
    "ValidationReport",
    "pseudo system prompts",
    "reader_evidence",
]


@pytest.mark.parametrize("marker", _REQUIRED_SYSTEM_PROMPT_MARKERS)
def test_synthesizer_system_prompt_contains_required_marker(marker: str) -> None:
    assert marker in SYNTHESIZER_SYSTEM_PROMPT, (
        f"SYNTHESIZER_SYSTEM_PROMPT is missing required marker {marker!r}. "
        f"If you removed this section intentionally, update this test too."
    )


# ---------------------------------------------------------------------------
# 4. User prompt XML tags
# ---------------------------------------------------------------------------


def test_user_prompt_contains_refined_idea_tags() -> None:
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<refined_idea>" in prompt
    assert "</refined_idea>" in prompt


def test_user_prompt_contains_research_plan_tags() -> None:
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<research_plan>" in prompt
    assert "</research_plan>" in prompt


def test_user_prompt_contains_rubric_version_tags() -> None:
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<closing_instruction>" in prompt
    assert "rubric_version_used" in prompt
    assert "v1" in prompt


def test_user_prompt_contains_reader_evidence_tags() -> None:
    synth_input = _make_synth_input(question_count=5)
    prompt = build_synthesizer_user_prompt(synth_input)
    assert '<reader_evidence_q1 question_id="q1">' in prompt
    assert "</reader_evidence_q1>" in prompt


# ---------------------------------------------------------------------------
# 5. Cite-only-URL framing
# ---------------------------------------------------------------------------


def test_user_prompt_contains_cite_only_urls_framing() -> None:
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    prompt_lower = prompt.lower()
    assert "source_url" in prompt_lower
    assert "cite only" in prompt_lower or "only urls" in prompt_lower


# ---------------------------------------------------------------------------
# 6. Per-question reader blocks
# ---------------------------------------------------------------------------


def test_user_prompt_contains_per_question_reader_evidence_tags() -> None:
    synth_input = _make_synth_input(question_count=5)
    prompt = build_synthesizer_user_prompt(synth_input)

    for i in range(1, 6):
        assert f'<reader_evidence_q{i} question_id="q{i}">' in prompt


def test_user_prompt_includes_evidence_urls_for_each_question() -> None:
    synth_input = _make_synth_input(question_count=5)
    prompt = build_synthesizer_user_prompt(synth_input)

    for i in range(1, 6):
        expected_url = f"https://example.com/q{i}-article"
        assert expected_url in prompt, f"URL for q{i} not found in user prompt"


# ---------------------------------------------------------------------------
# 7. Untrusted framing
# ---------------------------------------------------------------------------


def test_user_prompt_contains_untrusted_framing_for_reader_evidence() -> None:
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "untrusted" in prompt.lower()


def test_synthesizer_system_prompt_contains_injection_warning() -> None:
    prompt_lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
    assert "not instructions" in prompt_lower or "not as instructions" in prompt_lower, (
        "SYNTHESIZER_SYSTEM_PROMPT must contain injection protection framing."
    )


def test_synthesizer_system_prompt_mentions_reader_blocks_as_data() -> None:
    assert "reader_evidence" in SYNTHESIZER_SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# 8. build_synthesizer_input with reader_outputs
# ---------------------------------------------------------------------------


def test_build_synthesizer_input_stores_reader_outputs() -> None:
    refined = _make_refined_idea()
    plan = _make_plan(5)
    outputs = _make_reader_outputs(5)
    synth_input = build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        reader_outputs=outputs,
        rubric_version="v1",
    )
    assert synth_input.reader_outputs == outputs
    assert all(
        len(synth_input.reader_outputs[f"q{i}"].extracted_evidence) >= 1
        for i in range(1, 6)
    )


def test_build_synthesizer_input_handles_sparse_reader_outputs() -> None:
    """Planner questions exist; reader_outputs may omit keys — prompt builder fills gaps."""
    refined = _make_refined_idea()
    plan = _make_plan(5)
    synth_input = build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        reader_outputs={},
        rubric_version="v1",
    )
    assert synth_input.reader_outputs == {}


def test_user_prompt_notes_missing_reader_blocks() -> None:
    """When reader_outputs is empty, closing instruction still references evidence rules."""
    refined = _make_refined_idea()
    plan = _make_plan(5)
    synth_input = build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        reader_outputs={},
        rubric_version="v1",
    )
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "no reader output" in prompt.lower() or "reader_evidence" in prompt


# ---------------------------------------------------------------------------
# 9. Quote discipline (v2 QUOTES section)
# ---------------------------------------------------------------------------


def test_system_prompt_contains_quotes_section() -> None:
    assert "QUOTES —" in SYNTHESIZER_SYSTEM_PROMPT


def test_system_prompt_contains_verbatim_quote_instruction() -> None:
    assert "verbatim_quote" in SYNTHESIZER_SYSTEM_PROMPT


def test_system_prompt_source_quote_section_mentions_exact_phrase() -> None:
    assert "exact" in SYNTHESIZER_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 10. OUTPUT SCHEMA — URL-string citations
# ---------------------------------------------------------------------------


def test_system_prompt_schema_section_describes_url_string_citations() -> None:
    assert "URL strings only" in SYNTHESIZER_SYSTEM_PROMPT


def test_system_prompt_schema_section_no_citation_object_fields() -> None:
    assert "accessed_at" not in SYNTHESIZER_SYSTEM_PROMPT
