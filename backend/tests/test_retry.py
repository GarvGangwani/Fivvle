"""Tests for app.reliability.retry.

All tests are purely in-process — no network, no database.

Covers:
- Single-attempt success (coro called exactly once)
- Retry on transient failures with eventual success
- No retry on non-transient exceptions
- No retry on CircuitOpenError
- No retry on asyncio.CancelledError
- Exhausted retries re-raise the last exception
- Delay values follow the expected exponential ± jitter range
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.reliability.circuit_breakers import CircuitOpenError
from app.reliability.retry import retry_async

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_failing_then_ok(fail_times: int, exc_factory=None):
    """Return an async callable that raises *fail_times* times, then returns 'ok'."""
    if exc_factory is None:
        def exc_factory():  # noqa: E306
            return httpx.TimeoutException("timeout", request=None)
    call_count = 0

    async def _fn():
        nonlocal call_count
        call_count += 1
        if call_count <= fail_times:
            raise exc_factory()
        return "ok"

    _fn.call_count_ref = lambda: call_count
    return _fn


# ---------------------------------------------------------------------------
# Basic success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_success_on_first_attempt_called_once():
    """A succeeding coro is called exactly once."""
    mock_coro = AsyncMock(return_value="ok")

    @retry_async()
    async def _fn():
        return await mock_coro()

    result = await _fn()
    assert result == "ok"
    mock_coro.assert_called_once()


# ---------------------------------------------------------------------------
# Transient retries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fails_twice_then_succeeds_on_third_returns_success():
    """2 transient failures then success → returns the success value."""
    with patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock):
        fn = _make_failing_then_ok(2)

        @retry_async()
        async def _wrapped():
            return await fn()

        result = await _wrapped()
    assert result == "ok"
    assert fn.call_count_ref() == 3


@pytest.mark.asyncio
async def test_all_four_attempts_fail_reraises_last():
    """4 consecutive transient failures → re-raise the last exception."""
    call_count = 0

    async def _always_fail():
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("refused")

    with patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock):

        @retry_async(max_retries=3)
        async def _wrapped():
            return await _always_fail()

        with pytest.raises(httpx.ConnectError):
            await _wrapped()

    assert call_count == 4  # 1 initial + 3 retries


# ---------------------------------------------------------------------------
# No retry on non-retryable exceptions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_transient_not_retried():
    """ValueError is not transient — called exactly once, exception propagates."""
    call_count = 0

    async def _raise_value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("bad input")

    @retry_async()
    async def _wrapped():
        return await _raise_value_error()

    with pytest.raises(ValueError):
        await _wrapped()

    assert call_count == 1


@pytest.mark.asyncio
async def test_circuit_open_error_not_retried():
    """CircuitOpenError propagates immediately without retry."""
    call_count = 0

    async def _raise_open():
        nonlocal call_count
        call_count += 1
        raise CircuitOpenError("test_breaker", 30.0)

    @retry_async()
    async def _wrapped():
        return await _raise_open()

    with pytest.raises(CircuitOpenError):
        await _wrapped()

    assert call_count == 1


@pytest.mark.asyncio
async def test_cancelled_error_not_retried():
    """asyncio.CancelledError propagates immediately without retry."""
    call_count = 0

    async def _raise_cancelled():
        nonlocal call_count
        call_count += 1
        raise asyncio.CancelledError()

    import asyncio

    @retry_async()
    async def _wrapped():
        return await _raise_cancelled()

    with pytest.raises(asyncio.CancelledError):
        await _wrapped()

    assert call_count == 1


# ---------------------------------------------------------------------------
# Delay values
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delay_values_follow_exponential_with_jitter():
    """asyncio.sleep is called with values in the expected exponential ± 25 % range."""
    sleep_calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    always_fail_count = 0

    async def _always_transient():
        nonlocal always_fail_count
        always_fail_count += 1
        raise httpx.TimeoutException("timeout", request=None)

    with patch("app.reliability.retry.asyncio.sleep", side_effect=_fake_sleep):

        @retry_async(max_retries=3, base_delay=0.5, multiplier=2.0, max_delay=8.0, jitter=0.25)
        async def _wrapped():
            return await _always_transient()

        with pytest.raises(httpx.TimeoutException):
            await _wrapped()

    # 3 retries → 3 sleep calls
    assert len(sleep_calls) == 3

    # attempt 0 → base 0.5 * uniform(0.75, 1.25) → [0.375, 0.625]
    assert 0.375 <= sleep_calls[0] <= 0.625, f"attempt-1 delay {sleep_calls[0]} out of range"

    # attempt 1 → base 1.0 * uniform(0.75, 1.25) → [0.75, 1.25]
    assert 0.75 <= sleep_calls[1] <= 1.25, f"attempt-2 delay {sleep_calls[1]} out of range"

    # attempt 2 → base 2.0 * uniform(0.75, 1.25) → [1.5, 2.5]
    assert 1.5 <= sleep_calls[2] <= 2.5, f"attempt-3 delay {sleep_calls[2]} out of range"
