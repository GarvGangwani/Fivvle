"""Unit tests for InProcessDispatcher (ADR 0009).

Three async tests (pytest-anyio auto mode):
  1. dispatch() returns before the pipeline task completes (non-blocking).
  2. dispatch() emits the correct structlog fields via capture_logs().
  3. The created asyncio task calls run_research_engine_pipeline with the
     correct experiment_id.

All tests patch run_research_engine_pipeline (deferred import inside dispatch())
at the module where it lives — that is the import site that runs at dispatch time.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import structlog
import structlog.testing

from app.dispatchers.in_process import InProcessDispatcher

# ---------------------------------------------------------------------------
# Helper: a fake sessionmaker callable
# ---------------------------------------------------------------------------


def _fake_sm() -> object:
    """Zero-arg callable that returns a minimal fake sessionmaker.

    InProcessDispatcher only calls self._get_sessionmaker(); it never calls
    the sessionmaker itself — that happens inside run_research_engine_pipeline,
    which we mock away.
    """
    return object()  # truthy, non-None — the pipeline mock ignores it


# ---------------------------------------------------------------------------
# 1. Non-blocking: dispatch() yields before the pipeline task finishes
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_returns_before_pipeline_completes() -> None:
    """dispatch() creates a background task and returns immediately.

    We gate the fake pipeline on an asyncio.Event so we can confirm that
    dispatch() returned while the task is still blocking on the gate.
    """
    gate = asyncio.Event()
    pipeline_reached = asyncio.Event()

    async def gated_pipeline(experiment_id: object, sessionmaker: object) -> None:
        pipeline_reached.set()
        await gate.wait()  # block until we release

    dispatcher = InProcessDispatcher(get_sessionmaker=_fake_sm)

    with patch(
        "app.services.research_engine_service.run_research_engine_pipeline",
        gated_pipeline,
    ):
        await dispatcher.dispatch(uuid4())

    # dispatch() returned — gate is still closed, so the task is still blocking.
    assert not gate.is_set(), "gate should still be closed: pipeline ran synchronously"

    # Release the gate so the task completes cleanly (avoids 'task pending' warnings).
    gate.set()
    await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# 2. Structlog fields — capture_logs() records the dispatching event
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_logs_dispatching_event_with_correct_structlog_fields() -> None:
    """dispatch() emits dispatcher dispatching with the correct structured fields."""
    exp_id = uuid4()
    dispatcher = InProcessDispatcher(get_sessionmaker=_fake_sm)

    async def noop_pipeline(experiment_id: object, sessionmaker: object) -> None:
        pass

    with patch(
        "app.services.research_engine_service.run_research_engine_pipeline",
        noop_pipeline,
    ):
        with structlog.testing.capture_logs() as cap:
            await dispatcher.dispatch(exp_id)
            await asyncio.sleep(0)  # drain event loop so task's done-callback logs too

    dispatching = [e for e in cap if e.get("event") == "dispatcher dispatching"]
    assert len(dispatching) == 1, f"Expected 1 'dispatcher dispatching' event, got: {cap}"
    evt = dispatching[0]
    assert evt["dispatcher"] == "in_process"
    assert evt["experiment_id"] == str(exp_id)
    assert evt["phase"] == "dispatched"


# ---------------------------------------------------------------------------
# 3. Task invocation — pipeline called with the correct experiment_id
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_creates_task_that_invokes_pipeline_with_correct_experiment_id() -> None:
    """The background task calls run_research_engine_pipeline(experiment_id=...)."""
    exp_id = uuid4()
    calls: list[object] = []

    async def recording_pipeline(experiment_id: object, sessionmaker: object) -> None:
        calls.append(experiment_id)

    dispatcher = InProcessDispatcher(get_sessionmaker=_fake_sm)

    with patch(
        "app.services.research_engine_service.run_research_engine_pipeline",
        recording_pipeline,
    ):
        await dispatcher.dispatch(exp_id)
        await asyncio.sleep(0)  # yield to event loop so the task executes

    assert calls == [exp_id], f"Expected pipeline called with {exp_id}, got: {calls}"
