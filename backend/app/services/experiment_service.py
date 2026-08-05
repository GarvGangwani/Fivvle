"""Experiment service — business logic for experiment creation and refinement.

State machine transitions (Spark + B1 scope):
    SPARK                          (create_experiment_spark — name only)
    SPARK → REFINING               (begin_refinement_from_spark)
    DRAFT → REFINING → REFINED     (legacy create_experiment_with_refinement)
    REFINED → REFINING → REFINED   (regenerate_refinement)

This module does NOT handle HTTP concerns. Exceptions propagate to the router
(app.routers.experiments), which translates them to HTTP responses.

Per AGENTS.md "Logging hygiene":
    NEVER log raw_idea or refined_idea content.
    Log experiment_id, user_id, and character counts only.

Per .cursorrules "Cost Tracking & Limits":
    Refinement regeneration cap: 5 per experiment (_REFINEMENT_REGENERATION_CAP).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.logging_config import get_logger
from app.utils.experiment_naming import apply_llm_name_if_unset, normalize_experiment_name
from app.schemas.refinement import RefinedIdea
from app.services.refinement_service import refine_idea
from app.services.tag_service import persist_experiment_tags

_logger = get_logger(__name__)

# Per .cursorrules "Cost Tracking & Limits".
_REFINEMENT_REGENERATION_CAP = 5

# Enforced when leaving Spark / starting Refine — not at experiment creation.
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


def validate_raw_idea_for_refine(raw_idea: str) -> str:
    """Validate idea content when leaving Spark / starting Refine."""
    stripped = raw_idea.strip()
    if len(stripped) < _RAW_IDEA_MIN_LEN:
        raise ValueError(
            f"raw_idea must contain at least {_RAW_IDEA_MIN_LEN} non-whitespace characters"
        )
    if len(raw_idea) > _RAW_IDEA_MAX_LEN:
        raise ValueError(f"raw_idea must be at most {_RAW_IDEA_MAX_LEN} characters")
    return stripped


async def create_experiment_spark(
    db: AsyncSession,
    user: User,
    name: str,
) -> Experiment:
    """Create an experiment in SPARK with name only and empty raw_idea."""
    stored_name = normalize_experiment_name(name)
    if not stored_name or len(stored_name) < 3:
        raise ValueError("name must be at least 3 characters")
    if len(stored_name) > _NAME_MAX_LEN:
        raise ValueError(f"name must be at most {_NAME_MAX_LEN} characters")

    experiment = Experiment(
        user_id=user.id,
        raw_idea="",
        name=stored_name,
        status=ExperimentStatus.SPARK,
        refinement_count=0,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)

    _logger.info(
        "experiment created in SPARK",
        experiment_id=str(experiment.id),
        user_id=str(user.id),
    )
    return experiment


async def begin_refinement_from_spark(
    db: AsyncSession,
    experiment: Experiment,
) -> Experiment:
    """SPARK → REFINING when the first Refine message is sent."""
    if experiment.status != ExperimentStatus.SPARK:
        return experiment

    # Post-capture: original_idea is the sealed seed; copy into raw_idea if
    # the working copy was never filled (name-only Spark create).
    if not (experiment.raw_idea or "").strip() and experiment.original_idea:
        experiment.raw_idea = experiment.original_idea.strip()

    if experiment.original_idea is not None:
        # Capture already validated length (1–2000). Allow refine handoff on
        # sealed ideas shorter than the legacy Spark min (50).
        stripped = (experiment.raw_idea or "").strip()
        if not stripped:
            raise ValueError(
                "raw_idea must not be empty when starting refine after capture"
            )
        if len(experiment.raw_idea or "") > _RAW_IDEA_MAX_LEN:
            raise ValueError(
                f"raw_idea must be at most {_RAW_IDEA_MAX_LEN} characters"
            )
        experiment.raw_idea = stripped
    else:
        validate_raw_idea_for_refine(experiment.raw_idea)

    now = datetime.now(timezone.utc)
    experiment.status = ExperimentStatus.REFINING
    if experiment.refinement_started_at is None:
        experiment.refinement_started_at = now
    await db.flush()

    _logger.info(
        "experiment SPARK → REFINING",
        experiment_id=str(experiment.id),
        user_id=str(experiment.user_id),
    )
    return experiment


async def create_experiment_with_refinement(
    db: AsyncSession,
    user: User,
    raw_idea: str,
    name: str | None = None,
) -> Experiment:
    """Legacy path: create + immediate refinement (kept for older clients/tests).

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

    stored_name = normalize_experiment_name(name)

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
    apply_llm_name_if_unset(experiment, refined)
    await persist_experiment_tags(db, experiment, refined)
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
    apply_llm_name_if_unset(experiment, refined)
    await persist_experiment_tags(db, experiment, refined)
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


def infer_status_after_unarchive(experiment: Experiment) -> ExperimentStatus:
    """Pick a sensible active status when restoring an archived experiment.

    Previous status is not persisted on archive, so infer from related data.
    Insight-bearing experiments restore to INSIGHT_READY (honest insight terminal).
    """
    if experiment.insight_report is not None:
        return ExperimentStatus.INSIGHT_READY
    if experiment.landing_page is not None:
        return ExperimentStatus.LANDING_DRAFT
    if experiment.validation_report is not None:
        return ExperimentStatus.RESEARCH_READY
    if experiment.refined_idea is not None:
        return ExperimentStatus.REFINED
    return ExperimentStatus.DRAFT


async def delete_experiment(db: AsyncSession, experiment: Experiment) -> None:
    """Permanently delete an experiment and owned child data.

    Cascades remove landing pages, reports, analytics, etc. LLM and external
    API audit rows keep experiment_id NULL. Linked chat thread is removed when
    present.
    """
    from app.db.models.chat_thread import ChatThread

    thread_id = experiment.thread_id
    if thread_id is not None:
        thread = await db.get(ChatThread, thread_id)
        if thread is not None:
            await db.delete(thread)

    experiment_id = experiment.id
    user_id = experiment.user_id
    await db.delete(experiment)
    await db.flush()

    _logger.info(
        "experiment deleted",
        experiment_id=str(experiment_id),
        user_id=str(user_id),
    )


class ExperimentCanvasMetrics(NamedTuple):
    chat_message_count: int
    evidence_atom_count: int
    landing_page_view_count: int
    resource_count: int
    attachment_count: int
    demand_score: int | None
    verdict: str | None


def extract_refined_idea_text(refined: dict | None) -> str | None:
    """Return the refined one-liner for canvas display, or None if not refined yet."""
    if not refined:
        return None
    one_liner = refined.get("refined_one_liner")
    if isinstance(one_liner, str) and one_liner.strip():
        return one_liner.strip()
    return None


def metrics_from_validation_report(
    raw: dict | None,
) -> tuple[int, int | None, str | None]:
    """Finding count, demand score, and verdict from a validation report payload."""
    if not raw:
        return 0, None, None

    qfs = raw.get("questions_and_findings") or []
    finding_count = sum(len(qf.get("findings") or []) for qf in qfs)

    demand_score: int | None = None
    overall_score = raw.get("overall_score")
    if isinstance(overall_score, (int, float)):
        demand_score = max(0, min(100, int(overall_score)))

    verdict = raw.get("overall_recommendation")
    verdict_str = verdict if isinstance(verdict, str) else None

    return finding_count, demand_score, verdict_str


async def fetch_experiment_canvas_metrics(
    db: AsyncSession,
    experiment_id: UUID,
    *,
    thread_id: UUID | None,
    validation_raw: dict | None,
) -> ExperimentCanvasMetrics:
    """Lightweight counts for the experiment canvas — queries run in parallel."""
    from app.db.models.chat_message import ChatMessage
    from app.db.models.experiment_attachment import ExperimentAttachment
    from app.db.models.experiment_resource import ExperimentResource
    from app.db.models.page_view import PageView

    evidence_atom_count, demand_score, verdict = metrics_from_validation_report(
        validation_raw
    )

    if thread_id is not None:
        chat_filter = or_(
            ChatMessage.experiment_id == experiment_id,
            ChatMessage.thread_id == thread_id,
        )
    else:
        chat_filter = ChatMessage.experiment_id == experiment_id

    chat_stmt = select(func.count()).select_from(ChatMessage).where(chat_filter)
    resource_stmt = (
        select(func.count())
        .select_from(ExperimentResource)
        .where(ExperimentResource.experiment_id == experiment_id)
    )
    attachment_stmt = (
        select(func.count())
        .select_from(ExperimentAttachment)
        .where(ExperimentAttachment.experiment_id == experiment_id)
    )
    page_view_stmt = (
        select(func.count()).select_from(PageView).where(PageView.experiment_id == experiment_id)
    )

    chat_result, resource_result, attachment_result, page_view_result = await asyncio.gather(
        db.execute(chat_stmt),
        db.execute(resource_stmt),
        db.execute(attachment_stmt),
        db.execute(page_view_stmt),
    )

    return ExperimentCanvasMetrics(
        chat_message_count=int(chat_result.scalar_one()),
        evidence_atom_count=evidence_atom_count,
        landing_page_view_count=int(page_view_result.scalar_one()),
        resource_count=int(resource_result.scalar_one()),
        attachment_count=int(attachment_result.scalar_one()),
        demand_score=demand_score,
        verdict=verdict,
    )
