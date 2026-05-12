"""Unit tests for app.services.experiment_service.

All LLM calls are mocked via:
    patch("app.services.experiment_service.refine_idea", AsyncMock(...))

This exercises the experiment service end-to-end (state transitions, domain
exception logic, rollback-on-failure) without hitting Anthropic or the DB.
The AsyncSession is mocked via AsyncMock so LLMCall logging and DB writes are
short-circuited.

Mirrors the pattern in tests/services/test_refinement_service.py.

Per .cursorrules "Cost Tracking & Limits": regeneration cap is 5 per experiment.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.schemas.refinement import RefinedIdea
from app.services.experiment_service import (
    InvalidExperimentState,
    RefinementLimitExceeded,
    create_experiment_with_refinement,
    regenerate_refinement,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_VALID_RISKS = [
    "Is there existing tooling that solves this for enterprise buyers today?",
    "Can unit economics work at target price given estimated CAC?",
    "Is the market TAM large enough to sustain a venture-scale outcome?",
]


def _make_valid_refined_idea(**overrides: object) -> RefinedIdea:
    defaults: dict = {
        "refined_one_liner": "A tool that cuts nurse shift-handoff time from 40 min to 5.",
        "target_audience": (
            "Night-shift nurses at understaffed regional hospitals who spend "
            "40 minutes per shift writing manual handoff notes."
        ),
        "value_proposition": (
            "Reduces handoff documentation time by 87%, freeing nurses for "
            "direct patient care during critical shift transitions."
        ),
        "risks": _VALID_RISKS,
        "headline": "Cut shift-handoff time from 40 minutes to 5.",
        "subheadline": "AI trained on your hospital's protocols handles every handoff note automatically.",
        "cta_text": "Join the waitlist",
    }
    defaults.update(overrides)
    return RefinedIdea(**defaults)


def _make_experiment(
    status: ExperimentStatus = ExperimentStatus.REFINED,
    refinement_count: int = 1,
    with_refined_idea: bool = True,
) -> Experiment:
    """Build an in-memory Experiment without a DB session."""
    exp = Experiment(
        user_id=uuid4(),
        raw_idea="A tool that automates nurse shift-handoff notes in hospitals.",
        status=status,
        refinement_count=refinement_count,
    )
    if with_refined_idea:
        exp.refined_idea = _make_valid_refined_idea().model_dump()
    return exp


# ---------------------------------------------------------------------------
# create_experiment_with_refinement — happy path
# ---------------------------------------------------------------------------


async def test_create_experiment_happy_path() -> None:
    """DRAFT → REFINING → REFINED; refined_idea populated; refinement_count=1."""
    db = AsyncMock(spec=AsyncSession)
    user = MagicMock()
    user.id = uuid4()

    refined = _make_valid_refined_idea()

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=refined),
    ):
        experiment = await create_experiment_with_refinement(
            db, user, "A" * 50
        )

    assert experiment.status == ExperimentStatus.REFINED
    assert experiment.refinement_count == 1
    assert experiment.refined_idea == refined.model_dump()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


# ---------------------------------------------------------------------------
# create_experiment_with_refinement — input validation
# ---------------------------------------------------------------------------


async def test_create_experiment_raises_on_too_short_raw_idea() -> None:
    """raw_idea that is whitespace-only or shorter than 50 non-whitespace chars raises ValueError."""
    db = AsyncMock(spec=AsyncSession)
    user = MagicMock()
    user.id = uuid4()

    with pytest.raises(ValueError, match="at least 50"):
        await create_experiment_with_refinement(db, user, " " * 50)


async def test_create_experiment_raises_on_too_long_raw_idea() -> None:
    """raw_idea exceeding 2000 characters raises ValueError."""
    db = AsyncMock(spec=AsyncSession)
    user = MagicMock()
    user.id = uuid4()

    with pytest.raises(ValueError, match="at most 2000"):
        await create_experiment_with_refinement(db, user, "A" * 2001)


# ---------------------------------------------------------------------------
# create_experiment_with_refinement — LLM failure rollback
# ---------------------------------------------------------------------------


async def test_create_experiment_llm_failure_rolls_back_status() -> None:
    """On LLM failure, experiment status is reset to DRAFT and exception propagates.

    commit() must NOT be called — the get_session rollback will discard the row.
    """
    db = AsyncMock(spec=AsyncSession)
    user = MagicMock()
    user.id = uuid4()

    class _FakeLLMError(RuntimeError):
        pass

    created_experiments: list[Experiment] = []

    def _capture_add(obj: object) -> None:
        # Capture the Experiment reference so we can assert on its status after failure.
        # Do NOT call the original mock — that would cause infinite recursion since
        # side_effect replaces the mock call entirely.
        if isinstance(obj, Experiment):
            created_experiments.append(obj)

    db.add.side_effect = _capture_add

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(side_effect=_FakeLLMError("provider blew up")),
    ):
        with pytest.raises(_FakeLLMError, match="provider blew up"):
            await create_experiment_with_refinement(db, user, "A" * 50)

    assert len(created_experiments) == 1
    assert created_experiments[0].status == ExperimentStatus.DRAFT
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# regenerate_refinement — happy path
# ---------------------------------------------------------------------------


async def test_regenerate_refinement_happy_path() -> None:
    """refinement_count incremented; refine_idea called with previous_refinement."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(refinement_count=1)

    new_refined = _make_valid_refined_idea(refined_one_liner="Updated one-liner.")
    mock_refine = AsyncMock(return_value=new_refined)

    with patch("app.services.experiment_service.refine_idea", mock_refine):
        result = await regenerate_refinement(db, experiment, feedback="Make it more specific.")

    assert result.status == ExperimentStatus.REFINED
    assert result.refinement_count == 2
    assert result.refined_idea == new_refined.model_dump()

    # previous_refinement must be passed through to refine_idea
    _, call_kwargs = mock_refine.call_args
    assert call_kwargs["previous_refinement"] is not None
    assert isinstance(call_kwargs["previous_refinement"], RefinedIdea)
    assert call_kwargs["feedback"] == "Make it more specific."
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


# ---------------------------------------------------------------------------
# regenerate_refinement — cap enforcement
# ---------------------------------------------------------------------------


async def test_regenerate_refinement_at_cap_raises() -> None:
    """refinement_count >= 5 raises RefinementLimitExceeded before calling the LLM."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(refinement_count=5)

    with pytest.raises(RefinementLimitExceeded):
        await regenerate_refinement(db, experiment)


# ---------------------------------------------------------------------------
# regenerate_refinement — wrong state
# ---------------------------------------------------------------------------


async def test_regenerate_refinement_wrong_state_raises() -> None:
    """Status not in {REFINED, REFINING} raises InvalidExperimentState."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(status=ExperimentStatus.DRAFT, refinement_count=1)

    with pytest.raises(InvalidExperimentState):
        await regenerate_refinement(db, experiment)


async def test_regenerate_refinement_researching_state_raises() -> None:
    """RESEARCHING state also raises InvalidExperimentState."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(status=ExperimentStatus.RESEARCHING, refinement_count=1)

    with pytest.raises(InvalidExperimentState):
        await regenerate_refinement(db, experiment)


# ---------------------------------------------------------------------------
# regenerate_refinement — LLM failure rollback
# ---------------------------------------------------------------------------


async def test_regenerate_refinement_llm_failure_rolls_back_status() -> None:
    """On LLM failure, status reverts to REFINED and refinement_count is NOT incremented."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(status=ExperimentStatus.REFINED, refinement_count=2)
    original_count = experiment.refinement_count

    class _FakeLLMError(RuntimeError):
        pass

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(side_effect=_FakeLLMError("network timeout")),
    ):
        with pytest.raises(_FakeLLMError):
            await regenerate_refinement(db, experiment)

    assert experiment.status == ExperimentStatus.REFINED
    assert experiment.refinement_count == original_count
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# regenerate_refinement — feedback length validation
# ---------------------------------------------------------------------------


async def test_regenerate_refinement_feedback_too_long_raises() -> None:
    """Feedback exceeding 1000 characters raises ValueError before calling the LLM."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(refinement_count=1)

    with pytest.raises(ValueError, match="1000"):
        await regenerate_refinement(db, experiment, feedback="x" * 1001)


# ---------------------------------------------------------------------------
# regenerate_refinement — REFINING state is allowed defensively
# ---------------------------------------------------------------------------


async def test_regenerate_refinement_from_refining_state_is_allowed() -> None:
    """An experiment stuck in REFINING can be regenerated (defensive case)."""
    db = AsyncMock(spec=AsyncSession)
    experiment = _make_experiment(status=ExperimentStatus.REFINING, refinement_count=1)

    new_refined = _make_valid_refined_idea()
    with patch("app.services.experiment_service.refine_idea", AsyncMock(return_value=new_refined)):
        result = await regenerate_refinement(db, experiment)

    assert result.status == ExperimentStatus.REFINED
