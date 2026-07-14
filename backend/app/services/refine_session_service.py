"""Refine session finalize / reset (canvas Refine deep-dive)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.logging_config import get_logger

_logger = get_logger(__name__)


class RefineSessionError(Exception):
    """Domain error for refine finalize/reset (mapped to HTTP by the router)."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def get_owned_experiment(
    db: AsyncSession,
    experiment_id: UUID,
    user: User,
) -> Experiment:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user.id:
        raise RefineSessionError("Experiment not found", status_code=404)
    return experiment


async def finalize_refinement(
    db: AsyncSession,
    experiment: Experiment,
) -> Experiment:
    """Copy WIP refined_idea_current → refined_idea and mark REFINED.

    Does not dispatch research — that remains POST /experiments/{id}/confirm.
    May be called again after further chat to re-finalize with an updated WIP.
    """
    if not experiment.refined_idea_current:
        raise RefineSessionError(
            "No refined idea to finalize. Continue the conversation until "
            "the Refiner produces a refined idea."
        )

    experiment.refined_idea = experiment.refined_idea_current

    if experiment.status in (
        ExperimentStatus.SPARK,
        ExperimentStatus.REFINING,
        ExperimentStatus.DRAFT,
        ExperimentStatus.REFINED,
    ):
        experiment.status = ExperimentStatus.REFINED

    await db.commit()
    _logger.info(
        "refine_finalize",
        experiment_id=str(experiment.id),
        status=experiment.status.value,
    )
    return experiment


async def _has_downstream_evidence(db: AsyncSession, experiment_id: UUID) -> bool:
    result = await db.execute(
        select(ValidationReport.id).where(
            ValidationReport.experiment_id == experiment_id
        )
    )
    return result.scalar_one_or_none() is not None


async def reset_refinement_session(
    db: AsyncSession,
    experiment: Experiment,
) -> Experiment:
    """Delete refine chat messages; clear refined idea WIP if Evidence has not run."""
    if experiment.thread_id is not None:
        thread = await db.get(ChatThread, experiment.thread_id)
        if thread is not None:
            thread.active_leaf_message_id = None
            await db.flush()
        await db.execute(
            delete(ChatMessage).where(ChatMessage.thread_id == experiment.thread_id)
        )

    experiment.refined_idea_current = None
    experiment.refined_idea_updated_at = None

    has_downstream = await _has_downstream_evidence(db, experiment.id)
    if not has_downstream:
        experiment.refined_idea = None
        experiment.refinement_count = 0
        if experiment.status == ExperimentStatus.REFINED:
            experiment.status = ExperimentStatus.SPARK
            experiment.refinement_started_at = None

    await db.commit()
    _logger.info(
        "refine_session_reset",
        experiment_id=str(experiment.id),
        cleared_refined_idea=not has_downstream,
        status=experiment.status.value,
    )
    return experiment
