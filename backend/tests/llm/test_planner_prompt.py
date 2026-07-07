"""Regression tests for the planner prompt module.

These tests act as guards: if PLANNER_ZONE_A_INSTRUCTIONS is edited in a way that
drops a critical section (security framing, honesty rules, coverage discipline,
etc.), these tests catch the regression before the change ships.

Tests:
  1. PLANNER_ZONE_A_INSTRUCTIONS is non-empty and contains specific required markers
  2. PROMPT_NAME == "planner_v2_cached"
  3. build_planner_user_prompt() output contains <refined_idea> XML tags
  4. build_planner_user_prompt() output contains the untrusted-data framing line

These are structural regression tests, not LLM quality tests.
"""

from __future__ import annotations

import pytest

from app.llm.prompts.planner import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_ZONE_A_INSTRUCTIONS,
    PROMPT_NAME,
    build_planner_user_prompt,
)
from app.schemas.refinement import RefinedIdea

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_RISKS = [
    "Is Guru already solving Slack policy questions for this audience?",
    "Do legal teams block AI bots from citing HR policies due to liability?",
    "Is handbook staleness the real problem rather than question routing?",
]


def _make_refined_idea(**overrides) -> RefinedIdea:  # type: ignore[no-untyped-def]
    defaults = {
        "refined_one_liner": "An AI bot that answers HR policy questions in Slack.",
        "target_audience": (
            "Operations managers at 50-500 person companies spending 2-3 hours/week "
            "answering repeat policy questions in Slack."
        ),
        "value_proposition": (
            "Eliminates the weekly ops-manager burden of answering handbook questions "
            "by routing them to an AI trained on company documents."
        ),
        "risks": _VALID_RISKS,
        "headline": "Policy answers in Slack — without tagging ops every time",
        "subheadline": "Connect your handbook. The bot handles repeat questions.",
        "cta_text": "Join the waitlist",
    }
    defaults.update(overrides)
    return RefinedIdea(**defaults)


# ---------------------------------------------------------------------------
# 1. PLANNER_ZONE_A_INSTRUCTIONS is non-empty and contains required markers
# ---------------------------------------------------------------------------

# These markers correspond to critical sections of the system prompt.
# If any of these are removed during editing, the test fails immediately.
_REQUIRED_MARKERS = [
    "untrusted data",      # security framing — data/instruction separation
    "ResearchPlan",        # output structure declaration
    "5-7",                 # question count requirement
    "COVERAGE QUOTAS",     # required coverage quotas section
    "honesty",             # vague-idea honesty rules
    "search_queries",      # search query craft guidance
]


def test_planner_zone_a_instructions_is_non_empty() -> None:
    """Instructions moved to user Zone A; legacy system constant is empty."""
    assert PLANNER_SYSTEM_PROMPT == ""
    assert PLANNER_ZONE_A_INSTRUCTIONS.strip()


@pytest.mark.parametrize("marker", _REQUIRED_MARKERS)
def test_planner_zone_a_instructions_contains_required_marker(marker: str) -> None:
    """PLANNER_ZONE_A_INSTRUCTIONS must contain each required section marker.

    These markers guard against accidental truncation or section removal
    during prompt editing. They correspond to the spec requirements:
      - 'untrusted data': AGENTS.md data/instruction separation
      - 'ResearchPlan': output structure explicitness
      - '5-7': question count discipline
      - 'coverage': coverage dimension requirement
      - 'honesty': vague-idea honesty mechanism
      - 'search_queries': Tavily query craft guidance
    """
    assert marker in PLANNER_ZONE_A_INSTRUCTIONS, (
        f"PLANNER_ZONE_A_INSTRUCTIONS is missing required marker {marker!r}. "
        f"If you removed this section intentionally, update this test too."
    )


# ---------------------------------------------------------------------------
# 2. PROMPT_NAME == "planner_v2_cached"
# ---------------------------------------------------------------------------


def test_prompt_name_is_planner_v3_cached() -> None:
    """PROMPT_NAME must be 'planner_v3_cached' — LLMCall logs + cache layout suffix."""
    assert PROMPT_NAME == "planner_v3_cached"


# ---------------------------------------------------------------------------
# 3. build_planner_user_prompt() wraps RefinedIdea in <refined_idea> XML tags
# ---------------------------------------------------------------------------


def test_build_planner_user_prompt_contains_refined_idea_open_tag() -> None:
    """User prompt must contain opening <refined_idea> tag."""
    idea = _make_refined_idea()
    prompt = build_planner_user_prompt(idea)
    assert "<refined_idea>" in prompt


def test_build_planner_user_prompt_contains_refined_idea_close_tag() -> None:
    """User prompt must contain closing </refined_idea> tag."""
    idea = _make_refined_idea()
    prompt = build_planner_user_prompt(idea)
    assert "</refined_idea>" in prompt


# ---------------------------------------------------------------------------
# 4. build_planner_user_prompt() contains the untrusted-data framing line
# ---------------------------------------------------------------------------


def test_build_planner_user_prompt_contains_untrusted_framing() -> None:
    """User prompt must contain an explicit untrusted-data framing instruction.

    Per AGENTS.md: the user prompt must frame the data section as untrusted
    input, not as instructions — even though the content came from the
    refinement LLM, it ultimately derived from founder-submitted text.
    """
    idea = _make_refined_idea()
    prompt = build_planner_user_prompt(idea)
    # The framing must contain some form of "untrusted" — matches both
    # "untrusted data" and "untrusted input" and similar phrases.
    assert "untrusted" in prompt.lower()


def test_build_planner_user_prompt_contains_task_instruction() -> None:
    """User prompt must contain the task instruction for ResearchPlan output."""
    idea = _make_refined_idea()
    prompt = build_planner_user_prompt(idea)
    assert "ResearchPlan" in prompt


def test_build_planner_user_prompt_serializes_refined_idea_content() -> None:
    """User prompt must contain field content from the RefinedIdea (JSON-serialized)."""
    idea = _make_refined_idea()
    prompt = build_planner_user_prompt(idea)
    # The one-liner should appear inside the serialized JSON
    assert "AI bot that answers HR policy questions" in prompt
