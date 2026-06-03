"""Unit tests for app.services.dispatch_service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import DispatchTrigger, ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.dispatchers.protocol import DispatchError
from app.services.dispatch_service import transition_to_researching_and_dispatch
from app.services.experiment_service import InvalidExperimentState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_experiment(
    status: ExperimentStatus,
    *,
    research_error_detail: str | None = None,
) -> Experiment:
    return Experiment(
        id=uuid4(),
        user_id=uuid4(),
        raw_idea="A slack bot that answers HR policy questions so ops managers don't have to.",
        status=status,
        research_error_detail=research_error_detail,
    )


class _RecordingDispatcher:
    def __init__(self, *, raise_on_dispatch: Exception | None = None) -> None:
        self.dispatched: list[object] = []
        self._raise = raise_on_dispatch

    async def dispatch(self, experiment_id: object) -> None:
        if self._raise is not None:
            raise self._raise
        self.dispatched.append(experiment_id)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh async session per test; independent of FastAPI lifespan."""
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _persist_experiment(
    db: AsyncSession,
    status: ExperimentStatus,
    *,
    research_error_detail: str | None = None,
) -> Experiment:
    user = User(
        firebase_uid=f"dispatch-svc-{uuid4()}",
        email=f"dispatch-{uuid4()}@example.com",
        name="Dispatch Test User",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        raw_idea="A slack bot that answers HR policy questions so ops managers don't have to.",
        status=status,
        research_error_detail=research_error_detail,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


async def _reload_experiment(experiment_id: object) -> Experiment:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            result = await session.execute(
                select(Experiment).where(Experiment.id == experiment_id)
            )
            row = result.scalar_one()
            await session.refresh(row)
            return row
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Success paths (mocked session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_confirm_from_refined_success() -> None:
    experiment = _make_experiment(ExperimentStatus.REFINED)
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    await transition_to_researching_and_dispatch(
        db,
        experiment,
        DispatchTrigger.USER_CONFIRM,
        dispatcher,
    )

    assert experiment.status == ExperimentStatus.RESEARCHING
    assert experiment.dispatch_trigger == DispatchTrigger.USER_CONFIRM
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    assert dispatcher.dispatched == [experiment.id]


@pytest.mark.asyncio
async def test_user_confirm_from_research_failed_clears_error_and_dispatches() -> None:
    experiment = _make_experiment(
        ExperimentStatus.RESEARCH_FAILED,
        research_error_detail="planner:TimeoutError: upstream timed out",
    )
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    await transition_to_researching_and_dispatch(
        db,
        experiment,
        DispatchTrigger.USER_CONFIRM,
        dispatcher,
    )

    assert experiment.research_error_detail is None
    assert experiment.status == ExperimentStatus.RESEARCHING
    assert experiment.dispatch_trigger == DispatchTrigger.USER_CONFIRM
    assert dispatcher.dispatched == [experiment.id]


@pytest.mark.asyncio
async def test_auto_fire_from_refined_success() -> None:
    experiment = _make_experiment(ExperimentStatus.REFINED)
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    await transition_to_researching_and_dispatch(
        db,
        experiment,
        DispatchTrigger.AUTO_FIRE,
        dispatcher,
    )

    assert experiment.status == ExperimentStatus.RESEARCHING
    assert experiment.dispatch_trigger == DispatchTrigger.AUTO_FIRE
    assert dispatcher.dispatched == [experiment.id]


@pytest.mark.asyncio
async def test_auto_fire_from_refining_success() -> None:
    experiment = _make_experiment(ExperimentStatus.REFINING)
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    await transition_to_researching_and_dispatch(
        db,
        experiment,
        DispatchTrigger.AUTO_FIRE,
        dispatcher,
    )

    assert experiment.status == ExperimentStatus.RESEARCHING
    assert experiment.dispatch_trigger == DispatchTrigger.AUTO_FIRE
    assert dispatcher.dispatched == [experiment.id]


# ---------------------------------------------------------------------------
# Invalid state guards (mocked session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_confirm_from_draft_raises_invalid_state() -> None:
    experiment = _make_experiment(ExperimentStatus.DRAFT)
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    with pytest.raises(InvalidExperimentState):
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.USER_CONFIRM,
            dispatcher,
        )

    assert experiment.status == ExperimentStatus.DRAFT
    assert dispatcher.dispatched == []
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_user_confirm_from_refining_raises_invalid_state() -> None:
    experiment = _make_experiment(ExperimentStatus.REFINING)
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    with pytest.raises(InvalidExperimentState):
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.USER_CONFIRM,
            dispatcher,
        )

    assert experiment.status == ExperimentStatus.REFINING
    assert dispatcher.dispatched == []


@pytest.mark.asyncio
async def test_auto_fire_from_research_failed_raises_invalid_state() -> None:
    experiment = _make_experiment(ExperimentStatus.RESEARCH_FAILED)
    db = AsyncMock(spec=AsyncSession)
    dispatcher = _RecordingDispatcher()

    with pytest.raises(InvalidExperimentState):
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.AUTO_FIRE,
            dispatcher,
        )

    assert experiment.status == ExperimentStatus.RESEARCH_FAILED
    assert dispatcher.dispatched == []


# ---------------------------------------------------------------------------
# DispatchError — status committed, not rolled back (real DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_error_leaves_status_researching_in_db(db_session: AsyncSession) -> None:
    experiment = await _persist_experiment(db_session, ExperimentStatus.REFINED)
    experiment_id = experiment.id
    dispatcher = _RecordingDispatcher(raise_on_dispatch=DispatchError("scheduler unavailable"))

    with pytest.raises(DispatchError):
        await transition_to_researching_and_dispatch(
            db_session,
            experiment,
            DispatchTrigger.USER_CONFIRM,
            dispatcher,
        )

    reloaded = await _reload_experiment(experiment_id)
    assert reloaded.status == ExperimentStatus.RESEARCHING
    assert reloaded.dispatch_trigger == DispatchTrigger.USER_CONFIRM
