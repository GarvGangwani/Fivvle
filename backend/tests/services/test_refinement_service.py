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

from app.db.enums import ExperimentStage, ExperimentStatus
from app.db.models.experiment import Experiment
from app.llm.client import USER_CACHE_ZONE_BOUNDARY, _anthropic_structured_system_and_messages
from app.llm.prompts.refinement import (
    PROMPT_NAME_V5_CHAT,
    REFINEMENT_V2_CHAT_SYSTEM_PROMPT,
    build_refinement_v2_chat_user_prompt,
)
from app.schemas.refinement import ClarifyingQuestion, RefinedIdea, RefinementTurnDecision
from app.schemas.targeting import ExperimentTargeting
from app.config import get_settings
from app.services.experiment_service import create_experiment_with_refinement
from app.services.refinement_service import (
    PROMPT_NAME,
    REFINEMENT_CHAT_CACHE_BREAKPOINTS,
    refine_idea,
    run_turn,
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
    settings = get_settings()
    assert call_kwargs["provider"] == settings.refinement_provider
    assert call_kwargs["model"] == settings.refinement_model
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

    with (
        patch(
            "app.services.refinement_service.llm_client.complete_structured",
            mock_complete,
        ),
        patch(
            "app.services.experiment_service.persist_experiment_tags",
            new_callable=AsyncMock,
        ),
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


# ---------------------------------------------------------------------------
# Chat-mode refinement: RefinementTurnDecision schema + run_turn()
# ---------------------------------------------------------------------------


def _make_experiment_for_run_turn(refinement_count: int = 0) -> Experiment:
    return Experiment(
        user_id=uuid4(),
        raw_idea="I want to build something for fitness people.",
        status=ExperimentStatus.REFINING,
        refinement_count=refinement_count,
    )


def _sample_clarifying_questions() -> list[ClarifyingQuestion]:
    return [
        ClarifyingQuestion(
            question="Who specifically feels this pain day to day?",
            selection_mode="multiple",
            options=["CrossFit coaches", "Personal trainers", "Gym owners"],
        ),
    ]


def _make_clarify_decision(**overrides) -> RefinementTurnDecision:
    defaults = {
        "decision": "clarify",
        "assistant_message": "Got it — let's narrow the audience.",
        "clarifying_dimension": "problem",
        "clarifying_questions": _sample_clarifying_questions(),
        "refined_idea": None,
        "reasoning_trace": "need problem grounding",
    }
    defaults.update(overrides)
    return RefinementTurnDecision(**defaults)


def _make_ready_clarify_decision(
    refined_idea: RefinedIdea | None = None,
    **overrides,
) -> RefinementTurnDecision:
    """Clarify with empty questions + WIP refined_idea (user may finalize)."""
    defaults = {
        "decision": "clarify",
        "assistant_message": (
            "Here's a draft one-liner for CrossFit coaches speeding up program design. "
            "Finalize when you're ready, or keep exploring."
        ),
        "clarifying_dimension": None,
        "clarifying_questions": [],
        "refined_idea": refined_idea or _make_valid_refined_idea(),
        "reasoning_trace": "enough signal for WIP draft",
    }
    defaults.update(overrides)
    return RefinementTurnDecision(**defaults)


@pytest.mark.asyncio
async def test_run_turn_clarify_on_turn_zero_increments_count_and_strips_trace(
    valid_refined_idea: RefinedIdea,
) -> None:
    """Clarify on turn 0 increments refinement_count to 1; reasoning_trace stripped."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=0)
    decision = _make_clarify_decision()
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        AsyncMock(return_value=(decision, mock_meta)),
    ):
        result = await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[],
            latest_message="I want to build something for fitness people.",
        )

    assert result.decision == "clarify"
    assert result.reasoning_trace == ""
    assert experiment.refinement_count == 1
    assert experiment.refined_idea is None


@pytest.mark.asyncio
async def test_run_turn_without_bump_leaves_refinement_count(
    valid_refined_idea: RefinedIdea,
) -> None:
    """Retry/edit path must not increment refinement_count."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=2)
    decision = _make_clarify_decision(
        assistant_message="Alternate take — who pays first?",
    )
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        AsyncMock(return_value=(decision, mock_meta)),
    ):
        await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[],
            latest_message="Same user message again.",
            bump_refinement_count=False,
        )

    assert experiment.refinement_count == 2


@pytest.mark.asyncio
async def test_run_turn_clarify_pivot_resolution_resets_count(
    valid_refined_idea: RefinedIdea,
) -> None:
    """pivot_resolution clarify resets refinement_count to 0."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=2)
    decision = _make_clarify_decision(
        clarifying_dimension="pivot_resolution",
        assistant_message="Got it, pivoting — who is the new target user?",
    )
    mock_meta = _make_mock_llm_result()

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        AsyncMock(return_value=(decision, mock_meta)),
    ):
        await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[("user", "SAT tutor"), ("assistant", "What's the gap?")],
            latest_message="Actually AP Bio instead.",
        )

    assert experiment.refinement_count == 0


@pytest.mark.asyncio
async def test_run_turn_wip_refined_idea_writes_current_not_refined(
    valid_refined_idea: RefinedIdea,
) -> None:
    """Ready clarify writes refined_idea_current; does not set refined_idea."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=0)
    decision = _make_ready_clarify_decision(refined_idea=valid_refined_idea)
    mock_meta = _make_mock_llm_result()

    with (
        patch(
            "app.services.refinement_service.llm_client.complete_structured",
            AsyncMock(return_value=(decision, mock_meta)),
        ),
        patch(
            "app.services.refinement_service.persist_experiment_tags",
            new_callable=AsyncMock,
        ),
    ):
        result = await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[],
            latest_message="AI weekly exec summaries for EMs at 50-500 person orgs.",
        )

    assert result.decision == "clarify"
    assert experiment.refinement_count == 1
    assert experiment.refined_idea is None
    assert experiment.refined_idea_current == valid_refined_idea.model_dump()
    assert experiment.refined_idea_updated_at is not None


@pytest.mark.asyncio
async def test_run_turn_soft_ceiling_prompt_prefers_empty_questions(
    valid_refined_idea: RefinedIdea,
) -> None:
    """When refinement_count hits the soft ceiling, user prompt prefers empty questions."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=6)
    decision = _make_ready_clarify_decision(refined_idea=valid_refined_idea)
    mock_meta = _make_mock_llm_result()
    mock_complete = AsyncMock(return_value=(decision, mock_meta))

    with (
        patch(
            "app.services.refinement_service.llm_client.complete_structured",
            mock_complete,
        ),
        patch(
            "app.services.refinement_service.persist_experiment_tags",
            new_callable=AsyncMock,
        ),
    ):
        await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[
                ("user", "fitness app"),
                ("assistant", "Who specifically?"),
            ],
            latest_message="CrossFit coaches only.",
        )

    user_prompt: str = mock_complete.call_args.kwargs["user"]
    assert "Soft ceiling reached" in user_prompt
    assert "empty clarifying_questions" in user_prompt
    assert mock_complete.call_args.kwargs["prompt_name"] == PROMPT_NAME_V5_CHAT
    assert mock_complete.call_args.kwargs["phase"] == "refinement_chat"


@pytest.mark.asyncio
async def test_run_turn_passes_cache_breakpoints_to_client(
    valid_refined_idea: RefinedIdea,
) -> None:
    """Chat-mode refinement must cache the stable Zone A system prompt."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=1)
    decision = _make_clarify_decision()
    mock_meta = _make_mock_llm_result()
    captured: dict = {}

    async def capture_complete(*_a, **kw):
        captured.update(kw)
        return decision, mock_meta

    with patch(
        "app.services.refinement_service.llm_client.complete_structured",
        AsyncMock(side_effect=capture_complete),
    ):
        await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[("user", "B2B invoicing SaaS")],
            latest_message="Germany Mittelstand.",
        )

    assert captured["cache_breakpoints"] == REFINEMENT_CHAT_CACHE_BREAKPOINTS
    assert captured["cache_breakpoints"][0].position == "system_end"
    assert captured["cache_breakpoints"][0].ttl == "1h"
    assert captured["system"] == REFINEMENT_V2_CHAT_SYSTEM_PROMPT
    assert "SINGLE TOPIC PER QUESTION" in captured["system"]
    assert USER_CACHE_ZONE_BOUNDARY not in captured["user"]


def test_run_turn_cache_breakpoints_apply_ephemeral_to_zone_a_only() -> None:
    """Zone A system block gets cache_control; per-turn user content does not."""
    user_prompt = build_refinement_v2_chat_user_prompt(
        chat_history=[("user", "fitness coaches")],
        latest_message="CrossFit gyms in Austin.",
        turn_count=1,
        max_clarifying_turns=get_settings().refinement_max_clarifying_turns,
        min_turns_before_finalize=get_settings().refinement_min_clarifying_turns_before_finalize,
    )

    sys_out, msgs = _anthropic_structured_system_and_messages(
        system=REFINEMENT_V2_CHAT_SYSTEM_PROMPT,
        user=user_prompt,
        cache_breakpoints=REFINEMENT_CHAT_CACHE_BREAKPOINTS,
    )

    assert isinstance(sys_out, list)
    assert len(sys_out) == 1
    assert sys_out[0]["type"] == "text"
    assert sys_out[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "SINGLE TOPIC PER QUESTION" in sys_out[0]["text"]
    assert msgs == [{"role": "user", "content": user_prompt}]
    assert "cache_control" not in msgs[0]["content"]


def test_refinement_turn_decision_clarify_requires_dimension() -> None:
    """Clarify without clarifying_dimension raises ValidationError."""
    with pytest.raises(ValidationError):
        RefinementTurnDecision(
            decision="clarify",
            assistant_message="Got it — let's narrow the audience.",
            clarifying_dimension=None,
            clarifying_questions=_sample_clarifying_questions(),
            refined_idea=None,
        )


def test_refinement_turn_decision_rejects_finalize() -> None:
    """decision='finalize' is invalid — the user owns finalize."""
    with pytest.raises(ValidationError):
        RefinementTurnDecision(
            decision="finalize",  # type: ignore[arg-type]
            assistant_message="Starting research on your fitness tool.",
            refined_idea=_make_valid_refined_idea(),
        )


def test_refinement_turn_decision_rejects_banned_filler_phrase() -> None:
    """Banned filler phrases in assistant_message raise ValidationError."""
    with pytest.raises(ValidationError):
        RefinementTurnDecision(
            decision="clarify",
            assistant_message="Great question — who is your target user?",
            clarifying_dimension="audience",
            clarifying_questions=_sample_clarifying_questions(),
        )


def test_refinement_turn_decision_empty_questions_require_null_dimension() -> None:
    """Empty clarifying_questions must have clarifying_dimension=None."""
    with pytest.raises(ValidationError):
        RefinementTurnDecision(
            decision="clarify",
            assistant_message="Tell me more about your target user?",
            clarifying_dimension="audience",
            clarifying_questions=[],
        )


def test_refinement_turn_decision_empty_questions_with_wip_idea_ok() -> None:
    """Empty questions + null dimension + refined_idea is valid (ready to finalize)."""
    decision = RefinementTurnDecision(
        decision="clarify",
        assistant_message="Draft ready — finalize when you like.",
        clarifying_dimension=None,
        clarifying_questions=[],
        refined_idea=_make_valid_refined_idea(),
    )
    assert decision.decision == "clarify"
    assert decision.clarifying_questions == []
    assert decision.refined_idea is not None


def test_build_refinement_v2_chat_user_prompt_prefers_clarify_early() -> None:
    """Prompt builder prefers asking before the minimum clarifying turn count."""
    prompt = build_refinement_v2_chat_user_prompt(
        chat_history=[("user", "earlier"), ("assistant", "Who?")],
        latest_message="CrossFit coaches.",
        turn_count=2,
        max_clarifying_turns=6,
        min_turns_before_finalize=3,
    )
    assert "<chat_history>" in prompt
    assert "[user]: CrossFit coaches." in prompt
    assert "Clarifying turns used so far: 2" in prompt
    assert "you NEVER finalize" in prompt
    assert "Prefer asking ONE clarifying question" in prompt


def test_build_refinement_v2_chat_user_prompt_soft_ceiling_at_six() -> None:
    """Prompt builder prefers empty questions once the soft ceiling is reached."""
    prompt = build_refinement_v2_chat_user_prompt(
        chat_history=[("user", "earlier"), ("assistant", "Who?")],
        latest_message="CrossFit coaches.",
        turn_count=6,
        max_clarifying_turns=6,
        min_turns_before_finalize=3,
    )
    assert "soft ceiling reached" in prompt.lower()
    assert "empty clarifying_questions" in prompt.lower()
    assert "you never finalize" in prompt.lower()


@pytest.mark.asyncio
async def test_run_turn_wip_with_targeting_sets_experiment_columns(
    valid_refined_idea: RefinedIdea,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=3)
    targeting = ExperimentTargeting(
        target_geography="India",
        audience_bracket="urban families",
        stage=ExperimentStage.IDEA,
        why_now="Regulatory window opening.",
    )
    decision = _make_ready_clarify_decision(
        refined_idea=valid_refined_idea,
        targeting=targeting,
    )
    mock_meta = _make_mock_llm_result()

    with (
        patch(
            "app.services.refinement_service.llm_client.complete_structured",
            AsyncMock(return_value=(decision, mock_meta)),
        ),
        patch(
            "app.services.refinement_service.persist_experiment_tags",
            new_callable=AsyncMock,
        ),
    ):
        await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[("user", "India market idea")],
            latest_message="Ready to research.",
        )

    assert experiment.refined_idea is None
    assert experiment.refined_idea_current == valid_refined_idea.model_dump()
    assert experiment.target_geography == "India"
    assert experiment.audience_bracket == "urban families"
    assert experiment.stage == ExperimentStage.IDEA
    assert experiment.why_now == "Regulatory window opening."


@pytest.mark.asyncio
async def test_run_turn_wip_without_targeting_leaves_columns_none(
    valid_refined_idea: RefinedIdea,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment_for_run_turn(refinement_count=3)
    decision = _make_ready_clarify_decision(
        refined_idea=valid_refined_idea,
        targeting=None,
    )
    mock_meta = _make_mock_llm_result()

    with (
        patch(
            "app.services.refinement_service.llm_client.complete_structured",
            AsyncMock(return_value=(decision, mock_meta)),
        ),
        patch(
            "app.services.refinement_service.persist_experiment_tags",
            new_callable=AsyncMock,
        ),
    ):
        await run_turn(
            db=db,
            experiment=experiment,
            chat_history=[],
            latest_message="Go.",
        )

    assert experiment.refined_idea_current == valid_refined_idea.model_dump()
    assert experiment.target_geography is None
    assert experiment.audience_bracket is None
    assert experiment.stage is None
    assert experiment.why_now is None


def test_refinement_turn_decision_targeting_requires_refined_idea() -> None:
    with pytest.raises(ValidationError):
        RefinementTurnDecision(
            decision="clarify",
            assistant_message="Who is the target user?",
            clarifying_dimension="audience",
            clarifying_questions=_sample_clarifying_questions(),
            targeting=ExperimentTargeting(target_geography="India"),
        )
