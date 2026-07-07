"""Unit tests for refinement chat system prompt (v5 single-topic questions)."""

from __future__ import annotations

from app.llm.prompts.refinement import (
    PROMPT_NAME_V2_CHAT,
    PROMPT_NAME_V3_CHAT_LEGACY,
    PROMPT_NAME_V4_CHAT,
    PROMPT_NAME_V4_CHAT_LEGACY,
    PROMPT_NAME_V5_CHAT,
    REFINEMENT_V2_CHAT_SYSTEM_PROMPT,
)


def _flatten(s: str) -> str:
    return " ".join(s.split())


def test_priority_order_section_present() -> None:
    flat = _flatten(REFINEMENT_V2_CHAT_SYSTEM_PROMPT).lower()
    assert "priority order" in flat
    assert "geography first" in flat


def test_structured_options_section_present() -> None:
    flat = _flatten(REFINEMENT_V2_CHAT_SYSTEM_PROMPT).lower()
    assert "structured options" in flat
    assert "india" in flat
    assert "germany" in flat
    assert "indonesia" in flat
    assert "united states" in flat


def test_prompt_name_bumped_to_v5() -> None:
    assert PROMPT_NAME_V5_CHAT == "refinement_v5_chat"
    assert PROMPT_NAME_V2_CHAT == "refinement_v5_chat"
    assert PROMPT_NAME_V4_CHAT_LEGACY == "refinement_v4_chat"
    assert PROMPT_NAME_V4_CHAT == "refinement_v4_chat"
    assert PROMPT_NAME_V3_CHAT_LEGACY == "refinement_v3_chat"


def test_prompt_includes_single_topic_rule() -> None:
    flat = _flatten(REFINEMENT_V2_CHAT_SYSTEM_PROMPT).lower()
    assert "single topic per question" in flat
    assert "forbidden patterns" in flat


def test_prompt_includes_option_consistency_rule() -> None:
    flat = _flatten(REFINEMENT_V2_CHAT_SYSTEM_PROMPT).lower()
    assert "option consistency" in flat
    assert "what motivates heroes to sign up?" in flat
    assert "if no hero accepts, request auto-escalates to 112" in flat


def test_existing_dimensions_unchanged() -> None:
    flat = _flatten(REFINEMENT_V2_CHAT_SYSTEM_PROMPT).lower()
    assert "what specific problem? how painful is it?" in flat
    assert "who exactly? be specific enough to find them in the wild" in flat
    assert "what do people use today? why is that insufficient?" in flat
    assert "what specifically does the product do?" in flat
    assert "how would this make money? who pays" in flat
    assert "where the founder is: idea only, building, or launched" in flat
