"""Unit tests for InProcessLandingPageDispatcher launch-kit auto-dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.dispatchers.in_process_landing_page import (
    InProcessLandingPageDispatcher,
    _active_tasks,
)
from app.services.landing_page_service import LandingPageGenerationError

# ---------------------------------------------------------------------------
# Fake session / sessionmaker / launch-kit dispatcher
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
        self.rollback_count = 0

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def execute(self, stmt: object) -> _FakeResult:
        return _FakeResult(self._experiment)


class _FakeSessionMaker:
    def __init__(self, experiment: Experiment | None) -> None:
        self._experiment = experiment
        self.sessions: list[_FakeSession] = []

    def __call__(self) -> _FakeSession:
        session = _FakeSession(self._experiment)
        self.sessions.append(session)
        return session


class _FakeLaunchKitDispatcher:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[UUID] = []
        self._fail = fail

    async def dispatch(self, experiment_id: UUID) -> None:
        self.calls.append(experiment_id)
        if self._fail:
            raise RuntimeError("launch kit dispatch boom")


def _make_dispatcher(
    experiment: Experiment | None,
    *,
    launch_kit: _FakeLaunchKitDispatcher | None = None,
) -> tuple[InProcessLandingPageDispatcher, _FakeSessionMaker, _FakeLaunchKitDispatcher]:
    sm = _FakeSessionMaker(experiment)
    lk = launch_kit or _FakeLaunchKitDispatcher()

    def get_sessionmaker() -> _FakeSessionMaker:
        return sm

    return (
        InProcessLandingPageDispatcher(
            get_sessionmaker=get_sessionmaker,
            launch_kit_dispatcher=lk,
        ),
        sm,
        lk,
    )


async def _await_dispatched(experiment_id: UUID) -> None:
    task = _active_tasks.get(experiment_id)
    assert task is not None
    await task


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_happy_path_dispatches_launch_kit_once() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for landing page dispatch.",
        status=ExperimentStatus.LANDING_GENERATING,
    )
    dispatcher, _sm, launch_kit = _make_dispatcher(experiment)

    async def noop_generate(
        session: object,
        experiment_id: UUID,
        *,
        page_goal: str,
        template_id: str,
        regeneration_hint: str | None = None,
    ) -> None:
        pass

    with patch(
        "app.dispatchers.in_process_landing_page.generate_landing_page",
        noop_generate,
    ):
        await dispatcher.dispatch(
            exp_id,
            page_goal="waitlist",
            template_id="minimal",
        )
        await _await_dispatched(exp_id)

    assert experiment.status == ExperimentStatus.LANDING_DRAFT
    assert launch_kit.calls == [exp_id]


@pytest.mark.anyio
async def test_launch_kit_dispatch_failure_does_not_change_landing_status() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for landing page dispatch.",
        status=ExperimentStatus.LANDING_GENERATING,
    )
    launch_kit = _FakeLaunchKitDispatcher(fail=True)
    dispatcher, _sm, _ = _make_dispatcher(experiment, launch_kit=launch_kit)

    async def noop_generate(
        session: object,
        experiment_id: UUID,
        *,
        page_goal: str,
        template_id: str,
        regeneration_hint: str | None = None,
    ) -> None:
        pass

    with patch(
        "app.dispatchers.in_process_landing_page.generate_landing_page",
        noop_generate,
    ):
        await dispatcher.dispatch(
            exp_id,
            page_goal="waitlist",
            template_id="minimal",
        )
        await _await_dispatched(exp_id)

    assert experiment.status == ExperimentStatus.LANDING_DRAFT
    assert launch_kit.calls == [exp_id]


@pytest.mark.anyio
async def test_exhausted_retries_does_not_dispatch_launch_kit() -> None:
    exp_id = uuid4()
    experiment = Experiment(
        id=exp_id,
        user_id=uuid4(),
        raw_idea="Test idea for landing page dispatch.",
        status=ExperimentStatus.LANDING_GENERATING,
    )
    dispatcher, _sm, launch_kit = _make_dispatcher(experiment)

    async def always_fail(
        session: object,
        experiment_id: UUID,
        *,
        page_goal: str,
        template_id: str,
        regeneration_hint: str | None = None,
    ) -> None:
        raise LandingPageGenerationError("boom")

    with patch(
        "app.dispatchers.in_process_landing_page.generate_landing_page",
        always_fail,
    ):
        with patch(
            "app.dispatchers.in_process_landing_page.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await dispatcher.dispatch(
                exp_id,
                page_goal="waitlist",
                template_id="minimal",
            )
            await _await_dispatched(exp_id)

    assert experiment.status == ExperimentStatus.RESEARCH_READY
    assert launch_kit.calls == []
