"""Invariant tests for the eval set data.

These tests verify that the eval set is internally consistent and well-formed.
They do NOT run the research engine or make any LLM/Tavily calls.

Run with: uv run pytest tests/eval/test_eval_data_integrity.py -v

Purpose: if anyone edits ideas.py or gold_standards.py and breaks an
invariant (missing gold standard, invalid RefinedIdea, duplicate id, etc.),
these tests catch it before an eval run wastes money on malformed inputs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.refinement import RefinedIdea
from tests.eval.gold_standards import GOLD_STANDARDS
from tests.eval.ideas import ALLOWED_DOMAINS, EVAL_IDEAS, EvalIdea

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IDEA_IDS: list[str] = [idea.id for idea in EVAL_IDEAS]
_VAGUE_IDEA_ID = "vague-ai-productivity"


# ---------------------------------------------------------------------------
# Basic structural invariants
# ---------------------------------------------------------------------------


def test_eval_ideas_list_has_ten_entries() -> None:
    """Eval set must contain exactly 10 ideas."""
    assert len(EVAL_IDEAS) == 10, f"Expected 10 eval ideas, found {len(EVAL_IDEAS)}"


def test_all_idea_ids_are_unique() -> None:
    """No two EvalIdea entries may share the same id slug."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for idea in EVAL_IDEAS:
        if idea.id in seen:
            duplicates.append(idea.id)
        seen.add(idea.id)
    assert not duplicates, f"Duplicate eval idea ids: {duplicates}"


def test_every_idea_has_corresponding_gold_standard() -> None:
    """Every EvalIdea.id must have an entry in GOLD_STANDARDS."""
    missing = [idea.id for idea in EVAL_IDEAS if idea.id not in GOLD_STANDARDS]
    assert not missing, (
        f"These eval ideas have no gold standard entry: {missing}. "
        "Add a GoldStandard for each in gold_standards.py."
    )


def test_gold_standards_keyed_by_idea_id() -> None:
    """GOLD_STANDARDS dict key must match the GoldStandard.idea_id field."""
    mismatches = [
        (key, gs.idea_id)
        for key, gs in GOLD_STANDARDS.items()
        if key != gs.idea_id
    ]
    assert not mismatches, (
        f"GOLD_STANDARDS dict key does not match GoldStandard.idea_id: {mismatches}"
    )


# ---------------------------------------------------------------------------
# Per-idea field invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_raw_idea_length_in_production_valid_range(idea: EvalIdea) -> None:
    """raw_idea must be 50–2000 chars (mirrors B1 service validation)."""
    length = len(idea.raw_idea)
    assert 50 <= length <= 2000, (
        f"idea '{idea.id}' raw_idea length {length} is outside 50–2000 char range"
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_domain_is_from_allowed_set(idea: EvalIdea) -> None:
    """domain must be one of the values defined in ALLOWED_DOMAINS."""
    assert idea.domain in ALLOWED_DOMAINS, (
        f"idea '{idea.id}' has domain '{idea.domain}' not in ALLOWED_DOMAINS: "
        f"{sorted(ALLOWED_DOMAINS)}"
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_refined_idea_passes_pydantic_validation(idea: EvalIdea) -> None:
    """refined_idea must be a valid RefinedIdea (all constraints pass).

    Re-validates by round-tripping through model_validate — catches any
    hand-authored value that violates a field constraint (length, min items, etc.).
    """
    try:
        RefinedIdea.model_validate(idea.refined_idea.model_dump())
    except ValidationError as exc:
        pytest.fail(
            f"idea '{idea.id}' refined_idea fails RefinedIdea validation:\n{exc}"
        )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_refined_idea_risks_count_in_bounds(idea: EvalIdea) -> None:
    """risks list must have 3–5 items per the RefinedIdea schema."""
    count = len(idea.refined_idea.risks)
    assert 3 <= count <= 5, (
        f"idea '{idea.id}' has {count} risks — must be 3–5"
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_refined_idea_risk_items_within_char_limit(idea: EvalIdea) -> None:
    """Each risk string must be ≤ 200 chars per the _RiskStr annotation."""
    long_risks = [
        (i, len(r), r[:80])
        for i, r in enumerate(idea.refined_idea.risks)
        if len(r) > 200
    ]
    assert not long_risks, (
        f"idea '{idea.id}' has risks exceeding 200 chars: "
        + ", ".join(f"[{i}] {length} chars: '{preview}...'" for i, length, preview in long_risks)
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_refined_idea_field_char_limits(idea: EvalIdea) -> None:
    """All bounded RefinedIdea text fields must be within their declared max lengths."""
    ri = idea.refined_idea
    violations: list[str] = []

    if len(ri.refined_one_liner) > 200:
        violations.append(
            f"refined_one_liner: {len(ri.refined_one_liner)} chars (max 200)"
        )
    if len(ri.target_audience) > 300:
        violations.append(
            f"target_audience: {len(ri.target_audience)} chars (max 300)"
        )
    if len(ri.value_proposition) > 400:
        violations.append(
            f"value_proposition: {len(ri.value_proposition)} chars (max 400)"
        )
    if len(ri.headline) > 80:
        violations.append(f"headline: {len(ri.headline)} chars (max 80)")
    if len(ri.subheadline) > 160:
        violations.append(f"subheadline: {len(ri.subheadline)} chars (max 160)")
    if len(ri.cta_text) > 30:
        violations.append(f"cta_text: {len(ri.cta_text)} chars (max 30)")

    assert not violations, (
        f"idea '{idea.id}' refined_idea field length violations:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_notes_is_non_empty(idea: EvalIdea) -> None:
    """notes must be a non-empty string."""
    assert idea.notes.strip(), f"idea '{idea.id}' has empty notes"


# ---------------------------------------------------------------------------
# Gold standard invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_gold_standard_must_surface_has_at_least_three_items(idea: EvalIdea) -> None:
    """must_surface must have at least 3 items."""
    gs = GOLD_STANDARDS[idea.id]
    assert len(gs.must_surface) >= 3, (
        f"idea '{idea.id}' gold standard must_surface has only "
        f"{len(gs.must_surface)} items — minimum is 3"
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_gold_standard_must_not_invent_has_at_least_three_items(idea: EvalIdea) -> None:
    """must_not_invent must have at least 3 items."""
    gs = GOLD_STANDARDS[idea.id]
    assert len(gs.must_not_invent) >= 3, (
        f"idea '{idea.id}' gold standard must_not_invent has only "
        f"{len(gs.must_not_invent)} items — minimum is 3"
    )


@pytest.mark.parametrize("idea", EVAL_IDEAS, ids=_IDEA_IDS)
def test_gold_standard_should_surface_has_at_least_two_items(idea: EvalIdea) -> None:
    """should_surface must have at least 2 items."""
    gs = GOLD_STANDARDS[idea.id]
    assert len(gs.should_surface) >= 2, (
        f"idea '{idea.id}' gold standard should_surface has only "
        f"{len(gs.should_surface)} items — minimum is 2"
    )


# ---------------------------------------------------------------------------
# Domain coverage invariants
# ---------------------------------------------------------------------------


def test_eval_ideas_cover_at_least_five_distinct_domains() -> None:
    """Eval set should span at least 5 distinct domains for broad coverage."""
    domains = {idea.domain for idea in EVAL_IDEAS}
    assert len(domains) >= 5, (
        f"Eval set only covers {len(domains)} domains: {sorted(domains)}. "
        "At least 5 distinct domains required for meaningful coverage."
    )


def test_no_single_domain_has_more_than_three_ideas() -> None:
    """No domain should dominate the eval set with more than 3 ideas."""
    from collections import Counter

    counts = Counter(idea.domain for idea in EVAL_IDEAS)
    over_represented = {d: c for d, c in counts.items() if c > 3}
    assert not over_represented, (
        f"These domains have more than 3 ideas: {over_represented}. "
        "Distribute ideas more evenly across domains."
    )


# ---------------------------------------------------------------------------
# Special case: vague idea honesty test
# ---------------------------------------------------------------------------


def test_vague_idea_is_present_in_eval_set() -> None:
    """The deliberately-vague idea must be present in the eval set."""
    ids = {idea.id for idea in EVAL_IDEAS}
    assert _VAGUE_IDEA_ID in ids, (
        f"Deliberately-vague idea '{_VAGUE_IDEA_ID}' is missing from EVAL_IDEAS. "
        "It is required to test the research engine's honesty criterion."
    )


def test_vague_idea_gold_standard_flags_too_vague() -> None:
    """The vague idea's gold standard must_surface must include the 'too vague' flag."""
    gs = GOLD_STANDARDS.get(_VAGUE_IDEA_ID)
    assert gs is not None, f"No gold standard found for '{_VAGUE_IDEA_ID}'"

    vague_flag_present = any(
        "too vague" in item.lower() for item in gs.must_surface
    )
    assert vague_flag_present, (
        f"Gold standard for '{_VAGUE_IDEA_ID}' must_surface does not include "
        "a 'too vague to research' item. This is the primary honesty test."
    )


def test_vague_idea_must_not_invent_has_fabrication_checks() -> None:
    """The vague idea's must_not_invent must include fabrication-related checks."""
    gs = GOLD_STANDARDS.get(_VAGUE_IDEA_ID)
    assert gs is not None

    fabrication_check_present = any(
        any(kw in item.lower() for kw in ("fabricat", "invent", "fabricating"))
        for item in gs.must_not_invent
    )
    assert fabrication_check_present, (
        f"Gold standard for '{_VAGUE_IDEA_ID}' must_not_invent does not include "
        "a check against fabricating findings for an undefined product."
    )
