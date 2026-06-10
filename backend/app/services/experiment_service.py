"""Experiment service — business logic for experiment creation and refinement.

State machine transitions (B1 scope):
    DRAFT → REFINING → REFINED   (create_experiment_with_refinement)
    REFINED → REFINING → REFINED  (regenerate_refinement)

This module does NOT handle HTTP concerns. Exceptions propagate to the router
(app.routers.experiments), which translates them to HTTP responses.

Per AGENTS.md "Logging hygiene":
    NEVER log raw_idea or refined_idea content.
    Log experiment_id, user_id, and character counts only.

Per .cursorrules "Cost Tracking & Limits":
    Refinement regeneration cap: 5 per experiment (_REFINEMENT_REGENERATION_CAP).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea
from app.services.refinement_service import refine_idea

_logger = get_logger(__name__)

# Per .cursorrules "Cost Tracking & Limits".
_REFINEMENT_REGENERATION_CAP = 5

# Per USER_FLOW Stage 2 Step 2.1: founder writes "2-5 sentences in their own words".
_RAW_IDEA_MIN_LEN = 50
_RAW_IDEA_MAX_LEN = 2000


# ---------------------------------------------------------------------------
# Domain exceptions — translated to HTTP at the router layer.
# ---------------------------------------------------------------------------


class DomainError(Exception):
    """Base for domain-level exceptions raised by Fivvle services."""


class RefinementLimitExceeded(DomainError):  # noqa: N818
    """Regeneration cap (_REFINEMENT_REGENERATION_CAP) reached for this experiment."""


class InvalidExperimentState(DomainError):  # noqa: N818
    """Experiment status does not permit the requested operation."""


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


_NAME_MAX_LEN = 100


async def create_experiment_with_refinement(
    db: AsyncSession,
    user: User,
    raw_idea: str,
    name: str | None = None,
) -> Experiment:
    """Create an Experiment and run first-pass AI refinement synchronously.

    State transitions: DRAFT → REFINING → REFINED.

    Args:
        db: AsyncSession from the caller's request. The LLM client writes a
            LLMCall row inside this session for cost tracking.
        user: Authenticated User — ownership is established at creation.
        raw_idea: Founder's raw idea text. Validated server-side here.

    Returns:
        Refreshed Experiment in REFINED state with refinement_count=1.

    Raises:
        ValueError: raw_idea length constraint violated (50–2000 chars).
        Any exception from refine_idea (anthropic.APIError, instructor
            InstructorRetryException, pydantic.ValidationError) — experiment
            status is reset to DRAFT in memory before re-raising, then the
            get_session rollback removes the uncommitted experiment row.
    """
    stripped = raw_idea.strip()
    if len(stripped) < _RAW_IDEA_MIN_LEN:
        raise ValueError(
            f"raw_idea must contain at least {_RAW_IDEA_MIN_LEN} non-whitespace characters"
        )
    if len(raw_idea) > _RAW_IDEA_MAX_LEN:
        raise ValueError(f"raw_idea must be at most {_RAW_IDEA_MAX_LEN} characters")

    stored_name: str | None = None
    if name is not None:
        stripped_name = name.strip()
        if len(stripped_name) > _NAME_MAX_LEN:
            raise ValueError(f"name must be at most {_NAME_MAX_LEN} characters")
        stored_name = stripped_name or None

    experiment = Experiment(
        user_id=user.id,
        raw_idea=raw_idea,
        name=stored_name,
        status=ExperimentStatus.DRAFT,
        refinement_count=0,
    )
    db.add(experiment)
    await db.flush()  # assigns experiment.id via Python-side uuid4 default

    _logger.info(
        "experiment created",
        experiment_id=str(experiment.id),
        user_id=str(user.id),
    )

    experiment.status = ExperimentStatus.REFINING
    await db.flush()

    _logger.info(
        "experiment refinement started",
        experiment_id=str(experiment.id),
        user_id=str(user.id),
        idea_length=len(raw_idea),
    )

    try:
        refined: RefinedIdea = await refine_idea(
            db=db,
            raw_idea=raw_idea,
            experiment_id=experiment.id,
        )
    except Exception:
        # Reset in-memory status before propagating. The get_session rollback will
        # remove the uncommitted experiment row from the DB — no stuck REFINING rows.
        experiment.status = ExperimentStatus.DRAFT
        _logger.warning(
            "experiment refinement failed — rolling back to DRAFT",
            experiment_id=str(experiment.id),
            user_id=str(user.id),
        )
        raise

    experiment.refined_idea = refined.model_dump()
    experiment.status = ExperimentStatus.REFINED
    experiment.refinement_count = 1

    await db.commit()
    await db.refresh(experiment)

    _logger.info(
        "experiment refinement completed",
        experiment_id=str(experiment.id),
        user_id=str(user.id),
        refinement_count=experiment.refinement_count,
    )

    return experiment


async def regenerate_refinement(
    db: AsyncSession,
    experiment: Experiment,
    feedback: str | None = None,
) -> Experiment:
    """Re-run refinement on an existing experiment with optional founder feedback.

    Caller MUST verify ownership before calling this function — it does not
    perform ownership checks (per AGENTS.md "Authentication and authorization",
    authentication and authorization are separate steps; this service owns neither).

    State transitions: REFINED → REFINING → REFINED.
    REFINING is also permitted as a starting state (defensive: handles experiments
    stuck in REFINING from a prior failed transition).

    Args:
        db: AsyncSession from the caller's request.
        experiment: Loaded Experiment in REFINED (or REFINING) state.
        feedback: Optional guidance from the founder for the regeneration.

    Returns:
        Refreshed Experiment in REFINED state with incremented refinement_count.

    Raises:
        RefinementLimitExceeded: refinement_count >= 5.
        InvalidExperimentState: status not in {REFINED, REFINING}.
        ValueError: feedback exceeds 1000 characters.
        Any exception from refine_idea — experiment status is reset to its prior
            state in memory, then get_session rollback restores it in the DB.
    """
    if experiment.refinement_count >= _REFINEMENT_REGENERATION_CAP:
        raise RefinementLimitExceeded(
            f"Regeneration limit ({_REFINEMENT_REGENERATION_CAP}) reached "
            f"for experiment {experiment.id}"
        )

    allowed_states = {ExperimentStatus.REFINED, ExperimentStatus.REFINING}
    if experiment.status not in allowed_states:
        raise InvalidExperimentState(
            f"Experiment {experiment.id} is in state {experiment.status!r}, "
            f"which does not allow regeneration"
        )

    if feedback is not None and len(feedback) > 1000:
        raise ValueError("feedback must be at most 1000 characters")

    previous_refinement: RefinedIdea | None = None
    if experiment.refined_idea:
        previous_refinement = RefinedIdea.model_validate(experiment.refined_idea)

    prior_status = experiment.status
    experiment.status = ExperimentStatus.REFINING
    await db.flush()

    _logger.info(
        "experiment regeneration started",
        experiment_id=str(experiment.id),
        user_id=str(experiment.user_id),
        refinement_count=experiment.refinement_count,
        has_feedback=feedback is not None,
    )

    try:
        refined: RefinedIdea = await refine_idea(
            db=db,
            raw_idea=experiment.raw_idea,
            previous_refinement=previous_refinement,
            feedback=feedback,
            experiment_id=experiment.id,
        )
    except Exception:
        # Restore prior status. get_session rollback will undo the REFINING
        # flush, leaving the DB experiment in its original REFINED state.
        experiment.status = prior_status
        _logger.warning(
            "experiment regeneration failed — rolling back status",
            experiment_id=str(experiment.id),
            user_id=str(experiment.user_id),
            rolled_back_to=str(prior_status),
        )
        raise

    experiment.refined_idea = refined.model_dump()
    experiment.status = ExperimentStatus.REFINED
    experiment.refinement_count += 1

    await db.commit()
    await db.refresh(experiment)

    _logger.info(
        "experiment regeneration completed",
        experiment_id=str(experiment.id),
        user_id=str(experiment.user_id),
        refinement_count=experiment.refinement_count,
    )

    return experiment
