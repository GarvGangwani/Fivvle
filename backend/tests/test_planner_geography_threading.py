"""Unit tests for geography/targeting threading in the planner prompt."""

from __future__ import annotations

from app.db.enums import ExperimentStage
from app.llm.prompts.planner import (
    PROMPT_NAME,
    PROMPT_NAME_V1_CACHED_LEGACY,
    PROMPT_NAME_V2_CACHED_LEGACY,
    build_planner_user_prompt,
)
from app.schemas.refinement import RefinedIdea
from app.schemas.targeting import ExperimentTargeting

_VALID_RISKS = [
    "Is the market large enough to support a venture-scale business?",
    "Do incumbents already solve this for the target segment?",
    "Can unit economics work at the proposed price point?",
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


def _full_targeting() -> ExperimentTargeting:
    return ExperimentTargeting(
        target_geography="India — tier-1 cities",
        audience_bracket="urban middle-class families in tier-1 cities",
        stage=ExperimentStage.IDEA,
        why_now="New state fee-disclosure rules make comparison timely.",
    )


def test_null_targeting_no_targeting_tag_or_geography_scoping() -> None:
    prompt = build_planner_user_prompt(_make_refined_idea(), targeting=None)
    assert "<targeting>" not in prompt
    assert "GEOGRAPHY SCOPING" not in prompt


def test_full_targeting_includes_targeting_block_and_geography_scoping() -> None:
    prompt = build_planner_user_prompt(_make_refined_idea(), targeting=_full_targeting())
    assert "<targeting>" in prompt
    assert "target_geography: India — tier-1 cities" in prompt
    assert "audience_bracket: urban middle-class families in tier-1 cities" in prompt
    assert "founder_stage: idea" in prompt
    assert "why_now: New state fee-disclosure rules make comparison timely." in prompt
    assert "GEOGRAPHY SCOPING" in prompt


def test_geography_only_targeting_no_founder_stage_line() -> None:
    targeting = ExperimentTargeting(target_geography="India")
    prompt = build_planner_user_prompt(_make_refined_idea(), targeting=targeting)
    assert "<targeting>" in prompt
    assert "target_geography: India" in prompt
    assert "founder_stage:" not in prompt
    assert "GEOGRAPHY SCOPING" in prompt


def test_audience_bracket_only_no_geography_scoping() -> None:
    targeting = ExperimentTargeting(audience_bracket="solo SaaS founders")
    prompt = build_planner_user_prompt(_make_refined_idea(), targeting=targeting)
    assert "<targeting>" in prompt
    assert "audience_bracket: solo SaaS founders" in prompt
    assert "GEOGRAPHY SCOPING" not in prompt


def test_prompt_name_constants() -> None:
    assert PROMPT_NAME == "planner_v3_cached"
    assert PROMPT_NAME_V2_CACHED_LEGACY == "planner_v2_cached"
    assert PROMPT_NAME_V1_CACHED_LEGACY == "planner_v1_cached"


def test_planner_prompt_includes_local_competitor_hunt_when_geography_set() -> None:
    targeting = ExperimentTargeting(target_geography="India")
    prompt = build_planner_user_prompt(_make_refined_idea(), targeting=targeting)
    assert "LOCAL COMPETITOR IDENTIFICATION" in prompt
    assert "studios in India are experimenting" in prompt
    assert "India-based companies" in prompt


def test_planner_prompt_omits_local_competitor_hunt_when_geography_null() -> None:
    prompt = build_planner_user_prompt(_make_refined_idea(), targeting=None)
    assert "LOCAL COMPETITOR IDENTIFICATION" not in prompt


def test_planner_prompt_name_bumped_to_v3() -> None:
    assert PROMPT_NAME == "planner_v3_cached"
    assert PROMPT_NAME_V2_CACHED_LEGACY == "planner_v2_cached"
