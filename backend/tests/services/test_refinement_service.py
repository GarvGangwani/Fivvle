"""Unit tests for app.services.refinement_service and app.schemas.refinement.

All LLM calls are mocked — these tests exercise:
  1. Pydantic schema validation (field constraints)
  2. Service wiring (correct arguments forwarded to complete_structured)
  3. Prompt builder integration (XML tags present in user prompt)
  4. Exception propagation (service does not swallow LLM errors)

No real DB connection required. The AsyncSession is mocked via AsyncMock so
LLMCall write-through in the client wrapper is also short-circuited.

Pattern: patch complete_structured at the service module's import reference
    patch("app.services.refinement_service.llm_client.complete_structured", ...)
  This is the safest target: it patches the exact reference the service uses
  regardless of how it imported the function.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.schemas.refinement import RefinedIdea
from app.services.experiment_service import create_experiment_with_refinement
from app.services.refinement_service import (
    PROMPT_NAME,
    _REFINEMENT_MODEL,
    _REFINEMENT_PROVIDER,
    refine_idea,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_VALID_RISKS = [
    "Is the market large enough to support a venture-scale business at current TAM?",
    "Do existing enterprise tools already solve this problem for most buyers?",
    "Can the unit economics work at the target price point given CAC estimates?",
]


def _make_valid_refined_idea(**overrides) -> RefinedIdea:
    """Build a valid RefinedIdea, optionally overriding specific fields."""
    defaults = {
        "refined_one_liner": "A Slack bot that answers HR policy questions instantly.",
        "target_audience": (
            "Operations managers at 50-500 person companies who manually answer "
            "20-30 repeated policy questions per week in Slack."
        ),
        "value_proposition": (
            "Eliminates the 30-minute weekly Slack interrupt so ops managers can "
            "focus on actual operations work instead of being a walking FAQ."
        ),
        "risks": _VALID_RISKS,
        "headline": "Stop answering the same policy questions every week.",
        "subheadline": (
            "An AI trained on your handbook handles every 'what's the policy on X?' "
            "question so you don't have to."
        ),
        "cta_text": "Join the waitlist",
    }
    defaults.update(overrides)
    return RefinedIdea(**defaults)


@pytest.fixture
def valid_refined_idea() -> RefinedIdea:
    return _make_valid_refined_idea()


def _make_mock_llm_result() -> MagicMock:
    """Minimal LLMResult mock that complete_structured would return."""
    meta = MagicMock()
    meta.prompt_tokens = 400
    meta.completion_tokens = 250
    meta.cost_usd = Decimal("0.005750")
    return meta


def _risk0_overflow_validation_error() -> ValidationError:
    """Synthetic string_too_long at risks[0] for graceful-retry tests."""
    long_risk = "r" * 251
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(risks=[long_risk, _VALID_RISKS[1], _VALID_RISKS[2]])
    return exc_info.value


# ---------------------------------------------------------------------------
# 1. Schema: valid model is accepted
# ---------------------------------------------------------------------------


def test_refined_idea_schema_accepts_valid_model(valid_refined_idea: RefinedIdea) -> None:
    """A fully valid RefinedIdea should be constructed without error."""
    assert valid_refined_idea.refined_one_liner
    assert len(valid_refined_idea.risks) == 3
    assert len(valid_refined_idea.headline) <= 80
    assert len(valid_refined_idea.cta_text) <= 30


# ---------------------------------------------------------------------------
# 2. Schema: oversized fields are rejected
# ---------------------------------------------------------------------------


def test_refined_idea_schema_rejects_oversized_one_liner() -> None:
    """refined_one_liner exceeding 200 chars should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(refined_one_liner="x" * 201)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("refined_one_liner",) for e in errors)


def test_refined_idea_schema_rejects_oversized_target_audience() -> None:
    """target_audience exceeding 300 chars should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(target_audience="y" * 301)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("target_audience",) for e in errors)


def test_refined_idea_schema_rejects_oversized_headline() -> None:
    """headline exceeding 80 chars should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(headline="h" * 81)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("headline",) for e in errors)


def test_refined_idea_schema_rejects_oversized_cta_text() -> None:
    """cta_text exceeding 30 chars should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(cta_text="c" * 31)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("cta_text",) for e in errors)


def test_refined_idea_schema_rejects_oversized_risk_item() -> None:
    """A risk item exceeding 250 chars should raise ValidationError."""
    long_risk = "r" * 251
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(risks=[long_risk, "short risk a", "short risk b"])
    assert exc_info.value.errors()


# ---------------------------------------------------------------------------
# 3. Schema: too few / too many risks are rejected
# ---------------------------------------------------------------------------


def test_refined_idea_schema_rejects_too_few_risks() -> None:
    """risks list with fewer than 3 items should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(risks=["Only one risk here.", "And a second."])
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("risks",) for e in errors)


def test_refined_idea_schema_rejects_too_many_risks() -> None:
    """risks list with more than 5 items should raise ValidationError."""
    too_many = [f"Risk number {i}?" for i in range(6)]
    with pytest.raises(ValidationError) as exc_info:
        _make_valid_refined_idea(risks=too_many)
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("risks",) for e in errors)


def test_refined_idea_schema_accepts_five_risks() -> None:
    """risks list with exactly 5 items (the maximum) should be accepted."""
    five_risks = [f"Risk question number {i}?" for i in range(5)]
    idea = _make_valid_refined_idea(risks=five_risks)
    assert len(idea.risks) == 5


# ---------------------------------------------------------------------------
# 4. Service: calls complete_structured with the correct arguments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refine_idea_calls_complete_structured_correctly(
    valid_refined_idea: RefinedIdea,
) -> None:
    """refine_idea() should forward the right provider, model, and schema."""
    db = AsyncMock(spec=AsyncSession)
    experiment_id = uuid4()
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(valid_refined_idea, mock_meta))

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await refine_idea(
            db=db,
            raw_idea="A tool for nurses to automate shift handoff notes.",
            experiment_id=experiment_id,
        )

    assert result is valid_refined_idea
    mock_complete.assert_awaited_once()

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["provider"] == _REFINEMENT_PROVIDER
    assert call_kwargs["model"] == _REFINEMENT_MODEL
    assert call_kwargs["prompt_name"] == PROMPT_NAME
    assert call_kwargs["response_model"] is RefinedIdea
    assert call_kwargs["experiment_id"] == experiment_id
    assert call_kwargs["phase"] == "refinement"
    assert call_kwargs["max_retries"] == 0


@pytest.mark.asyncio
async def test_refine_idea_returns_parsed_model(valid_refined_idea: RefinedIdea) -> None:
    """refine_idea() should return the parsed model, not the full (parsed, meta) tuple."""
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        AsyncMock(return_value=(valid_refined_idea, mock_meta)),
    ):
        result = await refine_idea(db=db, raw_idea="Any idea.")

    assert isinstance(result, RefinedIdea)


# ---------------------------------------------------------------------------
# 5. Service: previous_refinement and feedback are passed through to prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refine_idea_with_previous_and_feedback_includes_xml_tags(
    valid_refined_idea: RefinedIdea,
) -> None:
    """When previous_refinement and feedback are supplied, the user prompt must
    contain <raw_idea>, <previous_refinement>, and <founder_feedback> tags."""
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(valid_refined_idea, mock_meta))

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        await refine_idea(
            db=db,
            raw_idea="Original idea text goes here.",
            previous_refinement=valid_refined_idea,
            feedback="Make the target audience more specific — which teams exactly?",
        )

    _, call_kwargs = mock_complete.call_args
    user_prompt: str = call_kwargs["user"]

    assert "<raw_idea>" in user_prompt
    assert "</raw_idea>" in user_prompt
    assert "<previous_refinement>" in user_prompt
    assert "</previous_refinement>" in user_prompt
    assert "<founder_feedback>" in user_prompt
    assert "</founder_feedback>" in user_prompt


@pytest.mark.asyncio
async def test_refine_idea_first_pass_has_no_previous_tags(
    valid_refined_idea: RefinedIdea,
) -> None:
    """First-pass refinement (no previous_refinement) should NOT include
    <previous_refinement> or <founder_feedback> tags in the user prompt."""
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(valid_refined_idea, mock_meta))

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        await refine_idea(db=db, raw_idea="First-pass idea text.")

    _, call_kwargs = mock_complete.call_args
    user_prompt: str = call_kwargs["user"]

    assert "<raw_idea>" in user_prompt
    assert "<previous_refinement>" not in user_prompt
    assert "<founder_feedback>" not in user_prompt


# ---------------------------------------------------------------------------
# 6. Service: exceptions from the LLM client propagate — not swallowed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refine_idea_propagates_llm_exceptions() -> None:
    """If complete_structured raises, refine_idea must re-raise without catching."""
    db = AsyncMock(spec=AsyncSession)

    class _FakeLLMError(RuntimeError):
        pass

    mock_complete = AsyncMock(side_effect=_FakeLLMError("provider blew up"))

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        with pytest.raises(_FakeLLMError, match="provider blew up"):
            await refine_idea(db=db, raw_idea="Some idea.")


# ---------------------------------------------------------------------------
# 7. Service: experiment_id=None is valid (pre-DB-write calls)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refine_idea_accepts_none_experiment_id(
    valid_refined_idea: RefinedIdea,
) -> None:
    """experiment_id=None should be forwarded as-is (valid before the DB row exists)."""
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()

    mock_complete = AsyncMock(return_value=(valid_refined_idea, mock_meta))

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        await refine_idea(db=db, raw_idea="Pre-DB idea.", experiment_id=None)

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] is None


# ---------------------------------------------------------------------------
# 8. Schema: extra fields are rejected (model_config extra="forbid")
# ---------------------------------------------------------------------------


def test_refined_idea_schema_rejects_extra_fields() -> None:
    """Extra fields not in the schema should raise ValidationError."""
    with pytest.raises(ValidationError):
        RefinedIdea(
            refined_one_liner="Valid one-liner.",
            target_audience="Valid audience.",
            value_proposition="Valid value prop.",
            risks=_VALID_RISKS,
            headline="Valid headline.",
            subheadline="Valid subheadline.",
            cta_text="Join waitlist",
            unknown_field="this should be rejected",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# 9. Prompt PROMPT_NAME is the expected version string
# ---------------------------------------------------------------------------


def test_prompt_name_is_versioned() -> None:
    """PROMPT_NAME should follow the refinement_vN convention."""
    from app.llm.prompts.refinement import PROMPT_NAME as pn

    assert pn.startswith("refinement_v")
    assert pn[len("refinement_v") :].isdigit()


# ---------------------------------------------------------------------------
# 10. UUID type is enforced for experiment_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refine_idea_passes_uuid_experiment_id(
    valid_refined_idea: RefinedIdea,
) -> None:
    """experiment_id typed as UUID should be passed through correctly."""
    db = AsyncMock(spec=AsyncSession)
    mock_meta = _make_mock_llm_result()
    eid = UUID("12345678-1234-5678-1234-567812345678")

    mock_complete = AsyncMock(return_value=(valid_refined_idea, mock_meta))

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        await refine_idea(db=db, raw_idea="Some idea.", experiment_id=eid)

    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["experiment_id"] == eid


# ---------------------------------------------------------------------------
# 11. Service: graceful validation retry on string length overflow
# ---------------------------------------------------------------------------

_REFINEMENT_V1_RETRY = "refinement_v1_retry"


@pytest.mark.asyncio
async def test_refinement_validation_error_triggers_graceful_retry_then_succeeds(
    valid_refined_idea: RefinedIdea,
) -> None:
    """When first LLM attempt fails Pydantic validation on field length,
    service auto-retries ONCE with explicit length-correction instruction.
    Founder sees normal REFINED state. Distinct prompt_name values correspond
    to two LLMCall rows when complete_structured is not mocked."""

    db = AsyncMock(spec=AsyncSession)
    user = MagicMock()
    user.id = uuid4()
    mock_meta = _make_mock_llm_result()
    ve_first = _risk0_overflow_validation_error()

    mock_complete = AsyncMock(side_effect=[ve_first, (valid_refined_idea, mock_meta)])

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        experiment = await create_experiment_with_refinement(db, user, "B" * 50)

    assert experiment.status == ExperimentStatus.REFINED
    assert mock_complete.await_count == 2

    first_kw = mock_complete.await_args_list[0].kwargs
    second_kw = mock_complete.await_args_list[1].kwargs

    assert first_kw["prompt_name"] == PROMPT_NAME
    assert first_kw["max_retries"] == 0

    assert second_kw["prompt_name"] == _REFINEMENT_V1_RETRY
    assert second_kw["max_retries"] == 0
    retry_user = second_kw["user"]
    assert "risks[0]" in retry_user
    assert "limit" in retry_user.lower()

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refinement_two_validation_errors_returns_to_draft() -> None:
    """When both LLM attempts fail Pydantic validation, service rolls back
    experiment to DRAFT and re-raises. Distinct prompt_name values correspond
    to two LLMCall rows when complete_structured is not mocked."""

    db = AsyncMock(spec=AsyncSession)
    user = MagicMock()
    user.id = uuid4()

    created_experiments: list[Experiment] = []

    def _capture_add(obj: object) -> None:
        if isinstance(obj, Experiment):
            created_experiments.append(obj)

    db.add.side_effect = _capture_add

    ve = _risk0_overflow_validation_error()
    mock_complete = AsyncMock(side_effect=[ve, ve])

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        mock_complete,
    ):
        with pytest.raises(ValidationError):
            await create_experiment_with_refinement(db, user, "C" * 50)

    assert len(created_experiments) == 1
    assert created_experiments[0].status == ExperimentStatus.DRAFT
    assert mock_complete.await_count == 2

    assert mock_complete.await_args_list[0].kwargs["prompt_name"] == PROMPT_NAME
    assert mock_complete.await_args_list[1].kwargs["prompt_name"] == _REFINEMENT_V1_RETRY

    db.commit.assert_not_awaited()
