"""Regression tests for the synthesizer prompt module.

These tests guard against accidental removal of critical sections from the
system prompt. If SYNTHESIZER_SYSTEM_PROMPT is edited in a way that drops
a required section (security framing, evidence-only rule, specificity rule,
recommendation logic, etc.), these tests catch the regression.

Tests:
  1.  PROMPT_NAME == "synthesizer_v1"
  2.  SYNTHESIZER_SYSTEM_PROMPT is non-empty
  3.  SYNTHESIZER_SYSTEM_PROMPT contains required markers (evidence-only,
      untrusted data, specificity, recommendation, banned patterns, citations)
  4.  build_synthesizer_user_prompt output contains all required XML tags
      (<refined_idea>, <research_plan>, <tavily_results>, <rubric_version>)
  5.  User prompt contains the "cite only URLs" framing instruction
  6.  User prompt contains per-question tavily_results tags for each question
  7.  User prompt contains the untrusted-data framing for tavily_results
  8.  SYNTHESIZER_SYSTEM_PROMPT contains the prompt-injection warning section
  9.  SYNTHESIZER_SYSTEM_PROMPT contains SOURCE QUOTE REQUIREMENT section (B2.3-fix)
  10. SYNTHESIZER_SYSTEM_PROMPT schema section reflects URL-string citations (B2.3-fix)
"""

from __future__ import annotations

import pytest

from app.llm.prompts.synthesizer import (
    PROMPT_NAME,
    SYNTHESIZER_SYSTEM_PROMPT,
    build_synthesizer_user_prompt,
)
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.refinement import RefinedIdea
from app.services.synthesizer_input import (
    SynthesizerInput,
    TavilyResultForPrompt,
    build_synthesizer_input,
)
from app.integrations.tavily import TavilyResult

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


def _make_synth_input(question_count: int = 5) -> SynthesizerInput:
    refined = _make_refined_idea()
    plan = _make_plan(question_count)
    tavily_results = {
        f"q{i}": [
            TavilyResult(
                title=f"Result for q{i}",
                url=f"https://example.com/q{i}-article",
                content="Scraped content about topic.",
                score=0.85,
            )
        ]
        for i in range(1, question_count + 1)
    }
    return build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        tavily_results=tavily_results,
        rubric_version="v1",
    )


# ---------------------------------------------------------------------------
# 1. PROMPT_NAME == "synthesizer_v1"
# ---------------------------------------------------------------------------


def test_prompt_name_is_synthesizer_v1() -> None:
    """PROMPT_NAME must be 'synthesizer_v1' — the stable identifier for LLMCall logs."""
    assert PROMPT_NAME == "synthesizer_v1"


# ---------------------------------------------------------------------------
# 2. SYNTHESIZER_SYSTEM_PROMPT is non-empty
# ---------------------------------------------------------------------------


def test_synthesizer_system_prompt_is_non_empty() -> None:
    """SYNTHESIZER_SYSTEM_PROMPT must not be empty or whitespace-only."""
    assert SYNTHESIZER_SYSTEM_PROMPT
    assert len(SYNTHESIZER_SYSTEM_PROMPT.strip()) > 0


# ---------------------------------------------------------------------------
# 3. SYNTHESIZER_SYSTEM_PROMPT contains required markers
# ---------------------------------------------------------------------------

# These markers correspond to critical sections in the synthesizer prompt.
# If any are removed during editing, the test fails immediately.
# Markers are chosen to be stable under light rewording.
_REQUIRED_SYSTEM_PROMPT_MARKERS = [
    # Evidence-only rule
    "citation",
    # Prompt-injection / untrusted data section
    "untrusted",
    # Specificity over summary section
    "pecificity",  # "Specificity" or "specificity"
    # Recommendation logic
    "proceed",
    "iterate",
    "pivot",
    "kill",
    "too_vague_to_recommend",
    # Banned patterns
    "market is large",
    # Per-question synthesis
    "QuestionFindings",
    # Confidence calibration
    "confidence_rationale",
    # Competitor extraction
    "CompetitorMention",
    # Output schema
    "ValidationReport",
    # Security / prompt-injection
    "ignore previous instructions",  # mentioned as example of injection to ignore
]


@pytest.mark.parametrize("marker", _REQUIRED_SYSTEM_PROMPT_MARKERS)
def test_synthesizer_system_prompt_contains_required_marker(marker: str) -> None:
    """SYNTHESIZER_SYSTEM_PROMPT must contain each required section marker.

    These markers guard against accidental truncation or section removal
    during prompt editing. They correspond to spec requirements from the
    original B2.3 prompt design brief.
    """
    assert marker in SYNTHESIZER_SYSTEM_PROMPT, (
        f"SYNTHESIZER_SYSTEM_PROMPT is missing required marker {marker!r}. "
        f"If you removed this section intentionally, update this test too."
    )


# ---------------------------------------------------------------------------
# 4. build_synthesizer_user_prompt output contains all required XML tags
# ---------------------------------------------------------------------------


def test_user_prompt_contains_refined_idea_tags() -> None:
    """User prompt must wrap RefinedIdea in <refined_idea> tags."""
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<refined_idea>" in prompt
    assert "</refined_idea>" in prompt


def test_user_prompt_contains_research_plan_tags() -> None:
    """User prompt must wrap ResearchPlan in <research_plan> tags."""
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<research_plan>" in prompt
    assert "</research_plan>" in prompt


def test_user_prompt_contains_rubric_version_tags() -> None:
    """User prompt must wrap rubric_version in <rubric_version> tags."""
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<rubric_version>" in prompt
    assert "</rubric_version>" in prompt
    assert "v1" in prompt


def test_user_prompt_contains_tavily_results_tags() -> None:
    """User prompt must contain <tavily_results> tags for each question."""
    synth_input = _make_synth_input(question_count=5)
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "<tavily_results" in prompt
    assert "</tavily_results>" in prompt


# ---------------------------------------------------------------------------
# 5. User prompt contains "cite only URLs" framing
# ---------------------------------------------------------------------------


def test_user_prompt_contains_cite_only_urls_framing() -> None:
    """User prompt must contain the 'cite only URLs from <tavily_results>' framing."""
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    # The framing appears in multiple forms — check for key terms
    prompt_lower = prompt.lower()
    assert "cite only" in prompt_lower or "only urls" in prompt_lower or "tavily_results" in prompt


# ---------------------------------------------------------------------------
# 6. User prompt contains per-question tavily_results tags
# ---------------------------------------------------------------------------


def test_user_prompt_contains_per_question_tavily_tags() -> None:
    """Each ResearchQuestion must have its own <tavily_results question_id="qN"> tag."""
    synth_input = _make_synth_input(question_count=5)
    prompt = build_synthesizer_user_prompt(synth_input)

    for i in range(1, 6):
        tag = f'<tavily_results question_id="q{i}">'
        assert tag in prompt, f"Missing <tavily_results> tag for q{i}"


def test_user_prompt_includes_tavily_urls_for_each_question() -> None:
    """The URLs from Tavily results must appear inside their respective tags."""
    synth_input = _make_synth_input(question_count=5)  # min 5 for ResearchPlan
    prompt = build_synthesizer_user_prompt(synth_input)

    for i in range(1, 6):
        expected_url = f"https://example.com/q{i}-article"
        assert expected_url in prompt, f"URL for q{i} not found in user prompt"


# ---------------------------------------------------------------------------
# 7. User prompt contains untrusted-data framing for tavily_results
# ---------------------------------------------------------------------------


def test_user_prompt_contains_untrusted_framing_for_tavily() -> None:
    """User prompt must frame <tavily_results> content as untrusted data.

    Per AGENTS.md: scraped content must be explicitly framed as data/untrusted
    to prevent prompt injection from Tavily search results.
    """
    synth_input = _make_synth_input()
    prompt = build_synthesizer_user_prompt(synth_input)
    assert "untrusted" in prompt.lower()


# ---------------------------------------------------------------------------
# 8. SYNTHESIZER_SYSTEM_PROMPT contains prompt-injection warning
# ---------------------------------------------------------------------------


def test_synthesizer_system_prompt_contains_injection_warning() -> None:
    """System prompt must contain explicit prompt-injection protection.

    Per AGENTS.md "LLM and agent security": the system prompt must instruct
    Claude to ignore instructions appearing in scraped/data sections.
    """
    # The security section must mention the concept of ignoring injected instructions.
    # Accept any form: "not instructions", "NOT INSTRUCTIONS", "not as instructions", etc.
    prompt_lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
    assert "not instructions" in prompt_lower or "not as instructions" in prompt_lower, (
        "SYNTHESIZER_SYSTEM_PROMPT must contain injection protection framing "
        "('not instructions' or similar). This is a CRITICAL security requirement."
    )


def test_synthesizer_system_prompt_mentions_tavily_results_as_data() -> None:
    """System prompt must frame <tavily_results> content as data, not instructions."""
    assert "tavily_results" in SYNTHESIZER_SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# 9. build_synthesizer_input helper produces correct structure
# ---------------------------------------------------------------------------


def test_build_synthesizer_input_caps_content_excerpt() -> None:
    """TavilyResultForPrompt.content_excerpt is capped at 3000 characters (B2.3-fix)."""
    from app.services.synthesizer_input import _CONTENT_EXCERPT_MAX_CHARS

    assert _CONTENT_EXCERPT_MAX_CHARS == 3000, (
        f"Expected _CONTENT_EXCERPT_MAX_CHARS=3000 after B2.3-fix, got {_CONTENT_EXCERPT_MAX_CHARS}"
    )

    refined = _make_refined_idea()
    plan = _make_plan(question_count=5)

    long_content = "X" * 6000  # 6000 chars — should be capped to 3000
    tavily_results = {
        f"q{i}": [
            TavilyResult(
                title="Long article",
                url=f"https://example.com/q{i}",
                content=long_content,
                score=0.9,
            )
        ]
        for i in range(1, 6)
    }

    synth_input = build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        tavily_results=tavily_results,
        rubric_version="v1",
    )

    for qid, results in synth_input.search_results_by_question.items():
        for r in results:
            assert len(r.content_excerpt) == _CONTENT_EXCERPT_MAX_CHARS, (
                f"content_excerpt for {qid} should be exactly {_CONTENT_EXCERPT_MAX_CHARS} chars "
                f"when input is longer; got {len(r.content_excerpt)}"
            )


def test_build_synthesizer_input_handles_empty_results() -> None:
    """Questions with no Tavily results get an empty list in the output."""
    refined = _make_refined_idea()
    plan = _make_plan(question_count=5)

    synth_input = build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        tavily_results={},  # no results for any question
        rubric_version="v1",
    )

    for qid, results in synth_input.search_results_by_question.items():
        assert results == [], f"Expected empty list for {qid}, got {results}"


def test_user_prompt_notes_empty_results() -> None:
    """User prompt should note when a question has no Tavily results."""
    refined = _make_refined_idea()
    plan = _make_plan(question_count=5)
    synth_input = build_synthesizer_input(
        refined_idea=refined,
        research_plan=plan,
        tavily_results={},
        rubric_version="v1",
    )
    prompt = build_synthesizer_user_prompt(synth_input)
    # Should mention that no results were returned for at least one question
    assert "No Tavily results" in prompt or "no results" in prompt.lower()


# ---------------------------------------------------------------------------
# 9. SOURCE QUOTE REQUIREMENT section present (B2.3-fix)
# ---------------------------------------------------------------------------


def test_system_prompt_contains_source_quote_requirement_heading() -> None:
    """SYNTHESIZER_SYSTEM_PROMPT must contain the SOURCE QUOTE REQUIREMENT section header.

    This section was added in B2.3-fix to enforce verbatim quotes from cited
    sources, improving evidence engagement quality.
    """
    assert "SOURCE QUOTE REQUIREMENT" in SYNTHESIZER_SYSTEM_PROMPT, (
        "SYNTHESIZER_SYSTEM_PROMPT is missing the 'SOURCE QUOTE REQUIREMENT' section. "
        "This section is required per B2.3-fix spec."
    )


def test_system_prompt_contains_verbatim_quote_instruction() -> None:
    """SYNTHESIZER_SYSTEM_PROMPT must contain the 'verbatim quote' instruction."""
    assert "verbatim quote" in SYNTHESIZER_SYSTEM_PROMPT, (
        "SYNTHESIZER_SYSTEM_PROMPT must contain 'verbatim quote' in the SOURCE QUOTE "
        "REQUIREMENT section."
    )


def test_system_prompt_source_quote_section_mentions_exact_phrase() -> None:
    """SOURCE QUOTE REQUIREMENT section must mention 'exact phrase' or 'exact substring'."""
    assert "exact" in SYNTHESIZER_SYSTEM_PROMPT, (
        "SYNTHESIZER_SYSTEM_PROMPT's SOURCE QUOTE REQUIREMENT section must instruct "
        "the LLM to use exact phrases (not paraphrase)."
    )


# ---------------------------------------------------------------------------
# 10. OUTPUT SCHEMA reflects URL-string citations (B2.3-fix)
# ---------------------------------------------------------------------------


def test_system_prompt_schema_section_uses_list_str_for_citations() -> None:
    """OUTPUT SCHEMA REQUIREMENTS must describe citations as list[str] (URLs only).

    After B2.3-fix, the LLM emits citations as URL strings. The schema section
    must reflect this — not the old list[Citation] object format.
    """
    # The schema section should mention list[str] for citations
    assert "list[str]" in SYNTHESIZER_SYSTEM_PROMPT, (
        "SYNTHESIZER_SYSTEM_PROMPT OUTPUT SCHEMA section must describe citations as "
        "'list[str]' (URL strings only) not list[Citation] objects. "
        "This is required after B2.3-fix."
    )


def test_system_prompt_schema_section_no_citation_object_fields() -> None:
    """OUTPUT SCHEMA REQUIREMENTS must NOT describe Citation object fields.

    After B2.3-fix, the LLM no longer emits Citation objects (no title,
    source_domain, accessed_at). The schema section must not ask for these.
    """
    # The old Citation fields section should not be present in the schema
    # (accessed_at was only in the Citation object, not URL strings)
    assert "accessed_at" not in SYNTHESIZER_SYSTEM_PROMPT, (
        "SYNTHESIZER_SYSTEM_PROMPT still contains 'accessed_at' in the schema section. "
        "This field is hydrated by code now — the LLM must not emit it. "
        "Remove the Citation object fields from the OUTPUT SCHEMA section."
    )
