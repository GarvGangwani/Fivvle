"""Record / amend founder Signal decisions (CAS on founder_decision_version)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus, FounderDecision
from app.db.models.experiment import Experiment


class FounderDecisionVersionConflict(Exception):
    """Raised when base_version does not match the row's current version."""

    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(
            f"founder_decision_version conflict: current={current_version}"
        )


class FounderDecisionArchivedError(Exception):
    """Raised when recording a decision on an ARCHIVED experiment."""


def current_founder_decision_version(experiment: Experiment) -> int:
    """CAS compare value: NULL (never recorded) is treated as 0."""
    if experiment.founder_decision_version is None:
        return 0
    return experiment.founder_decision_version


def apply_founder_decision(
    experiment: Experiment,
    *,
    decision: FounderDecision,
    note: str | None,
    base_version: int,
) -> None:
    """Compare-and-swap the founder decision onto the ORM row (no commit).

    First write: base_version=0 against a never-recorded row → version 1.
    Amendments: base_version must equal the stored version; bumps by 1.
    Sets founder_decision_at via clock_timestamp() (not now()).
    Does not touch experiment.status. Caller commits.
    """
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise FounderDecisionArchivedError()

    current = current_founder_decision_version(experiment)
    if base_version != current:
        raise FounderDecisionVersionConflict(current)

    experiment.founder_decision = decision
    experiment.founder_decision_note = note
    experiment.founder_decision_at = func.clock_timestamp()
    experiment.founder_decision_version = current + 1
