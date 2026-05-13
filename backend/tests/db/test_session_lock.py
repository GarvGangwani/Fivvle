"""Tests for app.db.session_lock.lock_for."""

from __future__ import annotations

import asyncio
import gc
import weakref
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.session_lock import _locks, lock_for


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


def test_lock_for_returns_same_lock_for_same_session() -> None:
    session = MagicMock(spec=AsyncSession)
    lock_a = lock_for(session)
    lock_b = lock_for(session)
    assert lock_a is lock_b


def test_lock_for_returns_different_locks_for_different_sessions() -> None:
    session_one = MagicMock(spec=AsyncSession)
    session_two = MagicMock(spec=AsyncSession)
    assert lock_for(session_one) is not lock_for(session_two)


@pytest.mark.asyncio
async def test_lock_is_released_when_session_garbage_collected() -> None:
    # Sweep stale entries left by earlier tests so `before` is a clean baseline.
    gc.collect()
    before = len(_locks)

    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    session_ref = None
    async with sm() as session:
        lock_for(session)
        session_ref = weakref.ref(session)
        assert len(_locks) == before + 1, "Lock was not registered for new session"

    await engine.dispose()
    # `session` variable still exists here; delete it so no strong ref remains.
    del session
    gc.collect()

    assert session_ref() is None, "Session was not garbage collected"
    assert len(_locks) == before, (
        f"Lock was not released. _locks went from {before} to {len(_locks)}"
    )


@pytest.mark.asyncio
async def test_lock_for_is_thread_safe_under_concurrent_first_access(
    db_session: AsyncSession,
) -> None:

    async def grab() -> asyncio.Lock:
        return lock_for(db_session)

    locks_out = await asyncio.gather(*(grab() for _ in range(50)))
    assert all(lock is locks_out[0] for lock in locks_out)
