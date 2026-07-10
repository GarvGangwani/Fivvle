"""Dispatch service — shared transition to RESEARCHING and pipeline dispatch.

Single source of truth for REFINED|REFINING|RESEARCH_FAILED → RESEARCHING transitions
per ADR 0019 (chat-mode auto-fire and existing /confirm path).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DispatchTrigger, ExperimentStatus
from app.db.models.experiment import Experiment
from app.dispatchers.protocol import DispatchError, ResearchDispatcher
from app.services.experiment_service import InvalidExperimentState

_USER_CONFIRM_ALLOWED = frozenset(
    {ExperimentStatus.REFINED, ExperimentStatus.RESEARCH_FAILED}
)
_AUTO_FIRE_ALLOWED = frozenset({ExperimentStatus.REFINED, ExperimentStatus.REFINING})
_EVIDENCE_RERUN_ALLOWED = frozenset(
    {
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.RESEARCH_FAILED,
        ExperimentStatus.LANDING_GENERATING,
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
    }
)


def _allowed_source_statuses(trigger: DispatchTrigger) -> frozenset[ExperimentStatus]:
    if trigger == DispatchTrigger.USER_CONFIRM:
        return _USER_CONFIRM_ALLOWED
    if trigger == DispatchTrigger.AUTO_FIRE:
        return _AUTO_FIRE_ALLOWED
    if trigger == DispatchTrigger.EVIDENCE_RERUN:
        return _EVIDENCE_RERUN_ALLOWED
    raise ValueError(f"Unknown dispatch trigger: {trigger!r}")


async def transition_to_researching_and_dispatch(
    db: AsyncSession,
    experiment: Experiment,
    trigger: DispatchTrigger,
    dispatcher: ResearchDispatcher,
) -> None:
    """Transition experiment to RESEARCHING and dispatch the pipeline.

    Single source of truth for the REFINED|REFINING|RESEARCH_FAILED -> RESEARCHING transition.
    Raises DispatchError if the dispatcher fails (caller maps to HTTP error).
    Raises InvalidExperimentState if the source state is not allowed for this trigger.
    """
    allowed = _allowed_source_statuses(trigger)
    if experiment.status not in allowed:
        raise InvalidExperimentState(
            f"Cannot transition to RESEARCHING with trigger={trigger} "
            f"from status={experiment.status}"
        )

    if experiment.status == ExperimentStatus.RESEARCH_FAILED:
        experiment.research_error_detail = None
    experiment.status = ExperimentStatus.RESEARCHING
    experiment.dispatch_trigger = trigger
    await db.flush()
    await db.commit()

    await dispatcher.dispatch(experiment.id)
