"""Tests for _log_llm_call session lock serialization."""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session_lock import lock_for
from app.llm.client import _log_llm_call

_LOG_KWARGS = {
    "experiment_id": None,
    "phase": None,
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "cost_usd": Decimal("0.001"),
    "latency_ms": 100,
    "request_id": "req-1",
}


@pytest.mark.asyncio
async def test_log_llm_call_uses_same_lock_for_session() -> None:
    """lock_for(session) returns the same asyncio.Lock before and after _log_llm_call."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()

    lock_before = lock_for(session)

    await _log_llm_call(session, prompt_name="test", **_LOG_KWARGS)

    lock_after = lock_for(session)
    assert lock_before is lock_after
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_concurrent_log_llm_call_serializes_flush() -> None:
    """Concurrent _log_llm_call on one session must not overlap flush.

    Without ``async with lock_for(db):`` around add+flush, both coroutines
    would enter flush concurrently and reproduce the Session-is-already-flushing
    race from Reader's asyncio.gather fan-out.
    """
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()

    flush_events: list[tuple[str, str, float]] = []
    call_counter = 0

    async def _slow_flush() -> None:
        nonlocal call_counter
        call_counter += 1
        label = "A" if call_counter == 1 else "B"
        flush_events.append(("start", label, time.perf_counter()))
        await asyncio.sleep(0.05)
        flush_events.append(("end", label, time.perf_counter()))

    session.flush = AsyncMock(side_effect=_slow_flush)

    async def _call(label: str) -> None:
        await _log_llm_call(
            session,
            prompt_name=f"test-{label}",
            **_LOG_KWARGS,
        )

    await asyncio.gather(_call("A"), _call("B"))

    a_end = next(t for kind, lbl, t in flush_events if kind == "end" and lbl == "A")
    b_start = next(t for kind, lbl, t in flush_events if kind == "start" and lbl == "B")

    assert b_start >= a_end, (
        f"B flush started before A finished: A_end={a_end}, B_start={b_start}"
    )


class _NoOpLock:
    """Dummy lock that does not serialize — reproduces the pre-fix race."""

    async def __aenter__(self) -> _NoOpLock:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.mark.asyncio
async def test_without_lock_concurrent_flush_can_overlap() -> None:
    """Regression: a no-op lock allows concurrent flush overlap (pre-fix behavior)."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()

    flush_events: list[tuple[str, str, float]] = []
    call_counter = 0

    async def _slow_flush() -> None:
        nonlocal call_counter
        call_counter += 1
        label = "A" if call_counter == 1 else "B"
        flush_events.append(("start", label, time.perf_counter()))
        await asyncio.sleep(0.05)
        flush_events.append(("end", label, time.perf_counter()))

    session.flush = AsyncMock(side_effect=_slow_flush)

    async def _call(label: str) -> None:
        await _log_llm_call(
            session,
            prompt_name=f"test-{label}",
            **_LOG_KWARGS,
        )

    with patch("app.llm.client.lock_for", return_value=_NoOpLock()):
        await asyncio.gather(_call("A"), _call("B"))

    a_end = next(t for kind, lbl, t in flush_events if kind == "end" and lbl == "A")
    b_start = next(t for kind, lbl, t in flush_events if kind == "start" and lbl == "B")

    assert b_start < a_end, "Expected concurrent overlap when lock is bypassed"
