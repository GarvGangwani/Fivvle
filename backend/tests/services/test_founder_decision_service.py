"""Tests for apply_founder_decision CAS / archived guard."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.enums import ExperimentStatus, FounderDecision
from app.db.models.experiment import Experiment
from app.services.founder_decision_service import (
    FounderDecisionArchivedError,
    FounderDecisionVersionConflict,
    apply_founder_decision,
    current_founder_decision_version,
)


def _experiment(**kwargs: object) -> Experiment:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "user_id": uuid4(),
        "raw_idea": "A" * 50,
        "status": ExperimentStatus.INSIGHT_READY,
    }
    defaults.update(kwargs)
    return Experiment(**defaults)  # type: ignore[arg-type]


def test_first_write_accepts_base_version_zero() -> None:
    experiment = _experiment()
    assert current_founder_decision_version(experiment) == 0
    apply_founder_decision(
        experiment,
        decision=FounderDecision.PROCEED,
        note="Ship it",
        base_version=0,
    )
    assert experiment.founder_decision == FounderDecision.PROCEED
    assert experiment.founder_decision_note == "Ship it"
    assert experiment.founder_decision_version == 1
    assert experiment.status == ExperimentStatus.INSIGHT_READY
    # SQLAlchemy ClauseElement until flush; assignment used clock_timestamp().
    assert experiment.founder_decision_at is not None


def test_amendment_requires_matching_version() -> None:
    experiment = _experiment(
        founder_decision=FounderDecision.ITERATE,
        founder_decision_version=1,
    )
    with pytest.raises(FounderDecisionVersionConflict) as exc_info:
        apply_founder_decision(
            experiment,
            decision=FounderDecision.PROCEED,
            note=None,
            base_version=0,
        )
    assert exc_info.value.current_version == 1

    apply_founder_decision(
        experiment,
        decision=FounderDecision.PROCEED,
        note=None,
        base_version=1,
    )
    assert experiment.founder_decision == FounderDecision.PROCEED
    assert experiment.founder_decision_version == 2
    assert experiment.status == ExperimentStatus.INSIGHT_READY


def test_archived_rejected() -> None:
    experiment = _experiment(status=ExperimentStatus.ARCHIVED)
    with pytest.raises(FounderDecisionArchivedError):
        apply_founder_decision(
            experiment,
            decision=FounderDecision.KILL,
            note=None,
            base_version=0,
        )
    assert experiment.founder_decision is None
    assert experiment.status == ExperimentStatus.ARCHIVED


def test_status_unchanged_on_record() -> None:
    experiment = _experiment(status=ExperimentStatus.LANDING_LIVE)
    apply_founder_decision(
        experiment,
        decision=FounderDecision.PIVOT,
        note=None,
        base_version=0,
    )
    assert experiment.status == ExperimentStatus.LANDING_LIVE
