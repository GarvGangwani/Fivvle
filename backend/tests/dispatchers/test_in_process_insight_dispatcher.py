"""Unit tests for InProcessInsightDispatcher."""

from __future__ import annotations

import asyncio
import time
import types
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import structlog.testing

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.dispatchers.in_process_insight import InProcessInsightDispatcher
from app.services.analytics_aggregator import LandingPageNotLiveError
from app.services.insight_service import (
    InsightCitationHallucinatedError,
    MissingValidationReportError,
)

# ---------------------------------------------------------------------------
# Fake session / sessionmaker
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, experiment: Experiment | None) -> None:
        self._experiment = experiment

    def scalar_one_or_none(self) -> Experiment | None:
        return self._experiment


class _FakeSession:
    def __init__(self, experiment: Experiment | None) -> None:
        self._experiment = experiment
        self.commit_count = 0

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def commit(self) -> None:
        self.commit_count += 1

    async def execute(self, stmt: object) -> _FakeResult:
        return _FakeResult(self._experiment)


class _FakeSessionMaker:
    def __init__(self, experiment: Experiment | None) -> None:
        self._experiment = experiment
        self.session: _FakeSession | None = None

    def __call__(self) -> _FakeSession:
        self.session = _FakeSession(self._experiment)
        return self.session


def _make_dispatcher(experiment: Experiment | None) -> InProcessInsightDispatcher:
    sm = _FakeSessionMaker(experiment)

    def get_sessionmaker() -> _FakeSessionMaker:
        return sm

    return InProcessInsightDispatcher(get_sessionmaker=get_sessionmaker), sm


async def _drain_tasks() -> None:
    await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# 1. Happy path → INSIGHT_READY
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_happy_path_sets_insight_ready() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, sm = _make_dispatcher(experiment)

    async def noop_report(session: object, experiment_id: UUID) -> None:
        pass

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        noop_report,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)
            await _drain_tasks()

    assert experiment.status == ExperimentStatus.INSIGHT_READY
    completed = [e for e in cap if e.get("event") == "insight pipeline completed"]
    assert len(completed) == 1
    assert completed[0]["phase"] == "completed"
    assert sm.session is not None
    assert sm.session.commit_count == 2


# ---------------------------------------------------------------------------
# 2–4. Known errors → INSIGHT_FAILED
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_missing_validation_report_sets_insight_failed() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, _sm = _make_dispatcher(experiment)

    async def raise_missing(session: object, experiment_id: UUID) -> None:
        raise MissingValidationReportError(f"No ValidationReport for {experiment_id}")

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        raise_missing,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)
            await _drain_tasks()

    assert experiment.status == ExperimentStatus.INSIGHT_FAILED
    failed = [e for e in cap if e.get("event") == "insight pipeline failed (known error)"]
    assert len(failed) == 1
    assert failed[0]["error_type"] == "MissingValidationReportError"


@pytest.mark.anyio
async def test_landing_page_not_live_sets_insight_failed() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, _sm = _make_dispatcher(experiment)

    async def raise_not_live(session: object, experiment_id: UUID) -> None:
        raise LandingPageNotLiveError(f"Landing page not live for {experiment_id}")

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        raise_not_live,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)
            await _drain_tasks()

    assert experiment.status == ExperimentStatus.INSIGHT_FAILED
    failed = [e for e in cap if e.get("event") == "insight pipeline failed (known error)"]
    assert len(failed) == 1
    assert failed[0]["error_type"] == "LandingPageNotLiveError"


@pytest.mark.anyio
async def test_citation_hallucination_sets_insight_failed() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, _sm = _make_dispatcher(experiment)

    async def raise_hallucination(session: object, experiment_id: UUID) -> None:
        raise InsightCitationHallucinatedError(
            invalid_ids={"q1.f99"},
            valid_ids={"q1.f0"},
            experiment_id=experiment_id,
        )

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        raise_hallucination,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)
            await _drain_tasks()

    assert experiment.status == ExperimentStatus.INSIGHT_FAILED
    failed = [e for e in cap if e.get("event") == "insight pipeline failed (known error)"]
    assert len(failed) == 1
    assert failed[0]["error_type"] == "InsightCitationHallucinatedError"


# ---------------------------------------------------------------------------
# 5. Unknown exception → INSIGHT_FAILED + exception log
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_unknown_exception_sets_insight_failed_and_logs_exception() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, _sm = _make_dispatcher(experiment)

    async def raise_runtime(session: object, experiment_id: UUID) -> None:
        raise RuntimeError("boom")

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        raise_runtime,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)
            await _drain_tasks()

    assert experiment.status == ExperimentStatus.INSIGHT_FAILED
    crashed = [e for e in cap if e.get("event") == "insight pipeline crashed"]
    assert len(crashed) == 1
    assert crashed[0]["error_type"] == "RuntimeError"
    assert crashed[0]["log_level"] == "error"


# ---------------------------------------------------------------------------
# 6. Non-blocking dispatch
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_returns_before_pipeline_completes() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, _sm = _make_dispatcher(experiment)

    async def slow_report(session: object, experiment_id: UUID) -> None:
        await asyncio.sleep(0.5)

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        slow_report,
    ):
        start = time.perf_counter()
        await dispatcher.dispatch(exp_id)
        elapsed = time.perf_counter() - start

    assert elapsed < 0.05
    await _drain_tasks()


# ---------------------------------------------------------------------------
# 7. Dispatched event fires immediately
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_logs_dispatched_event_immediately() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for insight pipeline dispatch.",
        status=ExperimentStatus.INSIGHT_GENERATING,
    )
    dispatcher, _sm = _make_dispatcher(experiment)

    async def noop_report(session: object, experiment_id: UUID) -> None:
        pass

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        noop_report,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)

    dispatched = [e for e in cap if e.get("event") == "insight pipeline dispatched"]
    assert len(dispatched) == 1
    assert dispatched[0]["phase"] == "dispatched"
    assert dispatched[0]["pipeline"] == "insight"
    assert dispatched[0]["dispatcher"] == "in_process"
    assert dispatched[0]["experiment_id"] == str(exp_id)

    await _drain_tasks()


# ---------------------------------------------------------------------------
# 8. Missing Experiment row — status transition is a no-op
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_missing_experiment_row_does_not_raise() -> None:
    exp_id = uuid4()
    dispatcher, sm = _make_dispatcher(experiment=None)

    async def raise_missing(session: object, experiment_id: UUID) -> None:
        raise MissingValidationReportError(f"No ValidationReport for {experiment_id}")

    with patch(
        "app.dispatchers.in_process_insight.generate_insight_report",
        raise_missing,
    ):
        await dispatcher.dispatch(exp_id)
        await _drain_tasks()

    assert sm.session is not None
    assert sm.session.commit_count == 0
