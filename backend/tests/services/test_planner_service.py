"""Unit tests for app.services.planner_service and app.schemas.planner.

All LLM calls are mocked — these tests exercise:
  1. Pydantic schema validation (field constraints, duplicate id rejection)
  2. Service wiring (correct arguments forwarded to complete_structured)
  3. Prompt builder integration (XML tags present in user prompt)
  4. Exception propagation (service does not swallow LLM errors)

No real DB connection required. The AsyncSession is mocked via AsyncMock so
LLMCall write-through in the client wrapper is also short-circuited.

Pattern: patch complete_structured at the service module's import reference
    patch("app.services.planner_service.llm_client.complete_structured", ...)
  This is the safest target: it patches the exact reference the service uses
  regardless of how it imported the function.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.refinement import RefinedIdea
from app.services.planner_service import (
    _PLANNER_MODEL,
    _PLANNER_PROVIDER,
    PROMPT_NAME,
    plan_research,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_VALID_RISKS = [
    "Are ops managers already using Guru or Notion AI to answer policy questions?",
    "Do HR teams have compliance concerns about AI bots citing PTO policies?",
    "Is handbook staleness the real blocker — making the bot answer incorrectly?",
]


def _make_valid_refined_idea(**overrides) -> RefinedIdea:  # type: ignore[no-untyped-def]
    defaults = {
        "refined_one_liner": "An AI Slack bot that answers HR policy questions from your handbook.",
        "target_audience": (
            "Operations managers at 50-500 person companies who spend 2-3 hours per "
            "week answering Slack messages about PTO rules and expense policies."
        ),
        "value_proposition": (
            "Cuts the 2-3 hour weekly ops-manager burden of answering repeat policy "
            "questions by routing them to an AI that reads the actual handbook."
        ),
        "risks": _VALID_RISKS,
        "headline": "Policy answers in Slack — without tagging ops every time",
        "subheadline": (
            "Connect your handbook. The bot handles 'what's the PTO rule?' so your "
            "ops team stops answering it for the 30th time."
        ),
        "cta_text": "Join the waitlist",
    }
    defaults.update(overrides)
    return RefinedIdea(**defaults)


def _make_valid_question(id: str = "q1") -> ResearchQuestion:
    return ResearchQuestion(
        id=id,
        question="Does Guru already handle Slack policy questions for this audience?",
        rationale=(
            "Guru is the direct competitor — if it already solves this, the market "
            "is contested. Investigable via Guru product pages and G2 reviews."
        ),
        search_queries=[
            "Guru Slack integration HR policy questions",
            "Guru vs Notion AI policy bot",
        ],
    )


def _make_valid_plan(question_count: int = 5) -> ResearchPlan:
    questions = [_make_valid_question(f"q{i}") for i in range(1, question_count + 1)]
    return ResearchPlan(questions=questions)


def _make_mock_llm_result() -> MagicMock:
    meta = MagicMock()
    meta.prompt_tokens = 800
    meta.completion_tokens = 600
    meta.cost_usd = Decimal("0.012000")
    return meta


@pytest.fixture
def valid_refined_idea() -> RefinedIdea:
    return _make_valid_refined_idea()


@pytest.fixture
def valid_plan() -> ResearchPlan:
    return _make_valid_plan()


# ---------------------------------------------------------------------------
# 1. Schema: ResearchPlan accepts a valid plan
# ---------------------------------------------------------------------------


def test_research_plan_schema_accepts_valid_plan() -> None:
    """A valid ResearchPlan with 5 questions should be accepted."""
    plan = _make_valid_plan(5)
    assert len(plan.questions) == 5
    assert plan.notes_for_synthesizer is None


def test_research_plan_schema_accepts_seven_questions() -> None:
    """A ResearchPlan with exactly 7 questions (the maximum) should be accepted."""
    plan = _make_valid_plan(7)
    assert len(plan.questions) == 7


# ---------------------------------------------------------------------------
# 2. Schema: ResearchPlan rejects fewer than 5 questions
# ---------------------------------------------------------------------------


def test_research_plan_schema_rejects_fewer_than_five_questions() -> None:
    """questions list with fewer than 5 items should raise ValidationError."""
    questions = [_make_valid_question(f"q{i}") for i in range(1, 5)]
    with pytest.raises(ValidationError) as exc_info:
        ResearchPlan(questions=questions)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("questions",) for e in errors)


# ---------------------------------------------------------------------------
# 3. Schema: ResearchPlan rejects more than 7 questions
# ---------------------------------------------------------------------------


def test_research_plan_schema_rejects_more_than_seven_questions() -> None:
    """questions list with more than 7 items should raise ValidationError."""
    # Only 7 valid ids exist (q1-q7), so we must use unique ids within range
    # but exceed the max_length constraint on the list itself.
    # Build 8 items — the max_length=7 constraint fires before duplicate-id check.
    questions = [_make_valid_question(f"q{i}") for i in range(1, 8)]
    extra = ResearchQuestion(
        id="q7",  # duplicate id — but list length check fires first
        question="An eighth question that should be rejected.",
        rationale="This should never be accepted since the list exceeds 7 items.",
        search_queries=["extra query here test"],
    )
    with pytest.raises(ValidationError) as exc_info:
        ResearchPlan(questions=[*questions, extra])
    assert exc_info.value.errors()


# ---------------------------------------------------------------------------
# 4. Schema: ResearchPlan rejects duplicate question ids
# ---------------------------------------------------------------------------


def test_research_plan_schema_rejects_duplicate_question_ids() -> None:
    """A ResearchPlan with two questions sharing the same id should raise ValueError."""
    q1a = _make_valid_question("q1")
    q1b = ResearchQuestion(
        id="q1",  # duplicate
        question="A second question with the same id as the first.",
        rationale="This duplicate id should trigger the model_validator.",
        search_queries=["duplicate id test query"],
    )
    q2 = _make_valid_question("q2")
    q3 = _make_valid_question("q3")
    q4 = _make_valid_question("q4")
    with pytest.raises(ValidationError) as exc_info:
        ResearchPlan(questions=[q1a, q1b, q2, q3, q4])
    # model_validator raises ValueError; Pydantic wraps it as ValidationError
    errors = exc_info.value.errors()
    assert errors  # at least one error present


# ---------------------------------------------------------------------------
# 5. Schema: ResearchQuestion rejects malformed id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "q8",        # out of range
        "Q1",        # uppercase
        "question1", # not the qN pattern
        "q0",        # zero not in q1-q7
        "q",         # no digit
        "1q",        # reversed
        " q1",       # leading space
    ],
)
def test_research_question_schema_rejects_malformed_id(bad_id: str) -> None:
    """ResearchQuestion.id not matching ^q[1-7]$ should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ResearchQuestion(
            id=bad_id,
            question="A valid question sentence.",
            rationale="A valid rationale sentence explaining investigability.",
            search_queries=["valid search query here"],
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("id",) for e in errors)


# ---------------------------------------------------------------------------
# 6. Schema: ResearchQuestion rejects empty search_queries list
# ---------------------------------------------------------------------------


def test_research_question_schema_rejects_empty_search_queries() -> None:
    """search_queries must have at least 1 item."""
    with pytest.raises(ValidationError) as exc_info:
        ResearchQuestion(
            id="q1",
            question="A valid question sentence.",
            rationale="A valid rationale sentence.",
            search_queries=[],
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("search_queries",) for e in errors)


# ---------------------------------------------------------------------------
# 7. Schema: ResearchQuestion rejects more than 3 search_queries
# ---------------------------------------------------------------------------


def test_research_question_schema_rejects_more_than_three_search_queries() -> None:
    """search_queries must have at most 3 items."""
    with pytest.raises(ValidationError) as exc_info:
        ResearchQuestion(
            id="q1",
            question="A valid question sentence.",
            rationale="A valid rationale sentence.",
            search_queries=[
                "first valid query",
                "second valid query",
                "third valid query",
                "fourth query that exceeds the limit",
            ],
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("search_queries",) for e in errors)


# ---------------------------------------------------------------------------
# 8. Service: plan_research() calls complete_structured with correct arguments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_research_calls_complete_structured_correctly(
    valid_refined_idea: RefinedIdea,
    valid_plan: ResearchPlan,
) -> None:
    """plan_research() should forward the right provider, model, schema, and phase."""
    db = AsyncMock(spec=AsyncSession)
    experiment_id = uuid4()
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(valid_plan, mock_meta))

    with patch(
        "app.services.planner_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await plan_research(
            db=db,
            refined_idea=valid_refined_idea,
            experiment_id=experiment_id,
        )

    assert result is valid_plan
    mock_complete.assert_awaited_once()

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["provider"] == _PLANNER_PROVIDER
    assert call_kwargs["model"] == _PLANNER_MODEL
    assert call_kwargs["prompt_name"] == PROMPT_NAME
    assert call_kwargs["response_model"] is ResearchPlan
    assert call_kwargs["experiment_id"] == experiment_id
    assert call_kwargs["phase"] == "planner"
    assert call_kwargs["max_retries"] == 1
    assert call_kwargs["max_tokens"] == 2048
    assert call_kwargs["temperature"] == 0.5


# ---------------------------------------------------------------------------
# 9. Service: plan_research() propagates exceptions from complete_structured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_research_propagates_exceptions(
    valid_refined_idea: RefinedIdea,
) -> None:
    """If complete_structured raises, plan_research must re-raise without catching."""
    db = AsyncMock(spec=AsyncSession)

    class _FakeLLMError(RuntimeError):
        pass

    mock_complete = AsyncMock(side_effect=_FakeLLMError("provider blew up"))

    with patch(
        "app.services.planner_service.llm_client.complete_structured",
        mock_complete,
    ), pytest.raises(_FakeLLMError, match="provider blew up"):
        await plan_research(db=db, refined_idea=valid_refined_idea)


# ---------------------------------------------------------------------------
# 10. Service: plan_research() with None experiment_id forwards None through
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_research_forwards_none_experiment_id(
    valid_refined_idea: RefinedIdea,
    valid_plan: ResearchPlan,
) -> None:
    """experiment_id=None should be forwarded as-is (valid for script-level calls)."""
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(valid_plan, mock_meta))

    with patch(
        "app.services.planner_service.llm_client.complete_structured",
        mock_complete,
    ):
        await plan_research(db=db, refined_idea=valid_refined_idea, experiment_id=None)

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] is None


@pytest.mark.asyncio
async def test_planner_emits_field_length_debug_log(
    valid_refined_idea: RefinedIdea,
) -> None:
    """Calibration DEBUG emit: planner_field_lengths must record lengths only.

    FilteringBoundLogger suppresses DEBUG when the app configures INFO;
    recorder patch matches reader_service rationale (capture_logs() after startup).
    """

    captured_debug: list[dict[str, Any]] = []

    def _capture_debug(evt: object, **_kw: object) -> None:
        captured_debug.append({"event": evt, **_kw})

    experiment_id = uuid4()
    notes_blob = "x" * 250
    lengths = [12, 24, 7, 100, 33]
    questions = [
        ResearchQuestion(
            id=f"q{i}",
            question="?" * lengths[i - 1],
            rationale=(
                "Rationale for investigability via public sources; tuned length fits schema."
            ),
            search_queries=[f"tavily query for q{i}"],
        )
        for i in range(1, 6)
    ]
    plan_with_notes = ResearchPlan(questions=questions, notes_for_synthesizer=notes_blob)
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()
    mock_complete = AsyncMock(return_value=(plan_with_notes, mock_meta))

    with patch(
        "app.services.planner_service.llm_client.complete_structured",
        mock_complete,
    ), patch(
        "app.services.planner_service._logger.debug",
        side_effect=_capture_debug,
    ) as dbg_mock:
        await plan_research(
            db=db,
            refined_idea=valid_refined_idea,
            experiment_id=experiment_id,
        )

    field_len_events = [e for e in captured_debug if e.get("event") == "planner_field_lengths"]
    assert dbg_mock.called, "instrumentation uses _logger.debug"
    assert len(field_len_events) == 1, captured_debug

    ev = field_len_events[0]
    assert ev["notes_for_synthesizer_len"] == 250
    assert ev["notes_for_synthesizer_present"] is True
    assert ev["num_research_questions"] == 5
    assert ev["experiment_id"] == str(experiment_id)
    assert ev["prompt_name"] == "planner_v1"
    assert ev["max_question_len"] == max(lengths)

    leaked = notes_blob in json.dumps(captured_debug, default=str, sort_keys=True)
    assert not leaked


# ---------------------------------------------------------------------------
# 11. Smoke test: build_planner_user_prompt wraps RefinedIdea in XML tags
# ---------------------------------------------------------------------------


def test_build_planner_user_prompt_wraps_in_xml_tags(
    valid_refined_idea: RefinedIdea,
) -> None:
    """build_planner_user_prompt() must wrap the RefinedIdea in <refined_idea> tags."""
    from app.llm.prompts.planner import build_planner_user_prompt

    prompt = build_planner_user_prompt(valid_refined_idea)

    assert "<refined_idea>" in prompt
    assert "</refined_idea>" in prompt
