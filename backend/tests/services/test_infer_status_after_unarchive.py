"""Tests for infer_status_after_unarchive."""

from __future__ import annotations

from uuid import uuid4

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.services.experiment_service import infer_status_after_unarchive


def _experiment(**kwargs: object) -> Experiment:
    return Experiment(
        id=uuid4(),
        user_id=uuid4(),
        raw_idea="A" * 50,
        status=ExperimentStatus.ARCHIVED,
        **kwargs,
    )


def test_infer_status_draft_when_no_progress() -> None:
    experiment = _experiment()
    assert infer_status_after_unarchive(experiment) == ExperimentStatus.DRAFT


def test_infer_status_refined() -> None:
    experiment = _experiment(refined_idea={"one_liner": "Test"})
    assert infer_status_after_unarchive(experiment) == ExperimentStatus.REFINED


def test_infer_status_research_ready() -> None:
    from app.db.models.validation_report import ValidationReport

    experiment = _experiment()
    experiment.validation_report = ValidationReport(
        id=uuid4(),
        experiment_id=experiment.id,
        raw_report={},
    )
    assert infer_status_after_unarchive(experiment) == ExperimentStatus.RESEARCH_READY


def test_infer_status_insight_ready_when_insight_report_exists() -> None:
    from app.db.models.insight_report import InsightReport

    experiment = _experiment()
    experiment.insight_report = InsightReport(
        id=uuid4(),
        experiment_id=experiment.id,
    )
    assert infer_status_after_unarchive(experiment) == ExperimentStatus.INSIGHT_READY
