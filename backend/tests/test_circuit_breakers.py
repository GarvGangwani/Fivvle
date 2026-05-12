"""Tests for app.reliability.circuit_breakers.

All tests are purely in-process — no network, no database.

Covers:
- State machine transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure counting and threshold
- Cooldown timing (monotonic clock is mocked for determinism)
- Transient vs. non-transient failure discrimination
- CircuitOpenError attributes
- Module-level registry behaviour
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.reliability.circuit_breakers import (
    CircuitBreaker,
    CircuitOpenError,
    _breakers,
    _is_transient_failure,
    get_breaker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_registry():
    """Clear the module-level breaker registry before and after each test."""
    _breakers.clear()
    yield
    _breakers.clear()


async def _succeed():
    return "ok"


async def _fail_connect():
    raise httpx.ConnectError("connection refused")


async def _fail_timeout():
    raise httpx.TimeoutException("timed out", request=None)


async def _fail_value_error():
    raise ValueError("bad input")


# ---------------------------------------------------------------------------
# Basic CLOSED behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_breaker_starts_closed_and_allows_calls():
    breaker = CircuitBreaker(name="test_new")
    result = await breaker.call(_succeed)
    assert result == "ok"


@pytest.mark.asyncio
async def test_non_transient_failure_does_not_count_and_propagates():
    """ValueError is not transient; counter stays at 0 and breaker stays CLOSED."""
    breaker = CircuitBreaker(name="test_nontransient")
    with pytest.raises(ValueError):
        await breaker.call(_fail_value_error)
    assert breaker._consecutive_failures == 0
    assert breaker._state.value == "closed"


@pytest.mark.asyncio
async def test_four_failures_then_success_stays_closed():
    """4 consecutive transient failures followed by 1 success → counter reset, CLOSED."""
    breaker = CircuitBreaker(name="test_4fail_1ok", failure_threshold=5)
    for _ in range(4):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)
    assert breaker._consecutive_failures == 4
    await breaker.call(_succeed)
    assert breaker._consecutive_failures == 0
    assert breaker._state.value == "closed"


# ---------------------------------------------------------------------------
# CLOSED → OPEN transition
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_five_consecutive_failures_open_breaker():
    breaker = CircuitBreaker(name="test_5fail_open", failure_threshold=5)
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)
    assert breaker._state.value == "open"


@pytest.mark.asyncio
async def test_sixth_call_raises_circuit_open_without_invoking_coro():
    """After 5 failures the 6th call must raise CircuitOpenError, not invoke the coro."""
    call_count = 0

    async def _counting_fail():
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("err")

    breaker = CircuitBreaker(name="test_6th_rejected", failure_threshold=5)
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_counting_fail)

    assert call_count == 5
    with pytest.raises(CircuitOpenError) as exc_info:
        await breaker.call(_counting_fail)
    assert call_count == 5  # coro NOT invoked on 6th call
    assert exc_info.value.breaker_name == "test_6th_rejected"
    assert exc_info.value.cooldown_remaining_seconds >= 0


# ---------------------------------------------------------------------------
# OPEN → cooldown → HALF_OPEN probe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_open_before_cooldown_raises_circuit_open_with_positive_remaining():
    breaker = CircuitBreaker(
        name="test_before_cooldown", failure_threshold=5, cooldown_seconds=60.0
    )
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)

    # Simulate that only 10 s have elapsed since the last failure.
    frozen_base = breaker._last_failure_time
    with patch("app.reliability.circuit_breakers.time") as mock_time:
        mock_time.monotonic.return_value = frozen_base + 10.0
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.call(_succeed)
    assert exc_info.value.cooldown_remaining_seconds > 0


@pytest.mark.asyncio
async def test_after_cooldown_call_transitions_to_half_open_and_goes_through():
    """After cooldown, the next call is the HALF_OPEN probe and should succeed."""
    breaker = CircuitBreaker(name="test_probe_success", failure_threshold=5, cooldown_seconds=60.0)
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)

    frozen_base = breaker._last_failure_time
    with patch("app.reliability.circuit_breakers.time") as mock_time:
        # Simulate 61 s elapsed so cooldown has passed.
        mock_time.monotonic.return_value = frozen_base + 61.0
        result = await breaker.call(_succeed)

    assert result == "ok"
    assert breaker._state.value == "closed"


@pytest.mark.asyncio
async def test_half_open_probe_success_resets_and_closes():
    """HALF_OPEN probe success → CLOSED, failure counter reset."""
    breaker = CircuitBreaker(
        name="test_half_open_close", failure_threshold=5, cooldown_seconds=60.0
    )
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)

    frozen_base = breaker._last_failure_time
    with patch("app.reliability.circuit_breakers.time") as mock_time:
        mock_time.monotonic.return_value = frozen_base + 61.0
        await breaker.call(_succeed)

    assert breaker._state.value == "closed"
    assert breaker._consecutive_failures == 0

    # Subsequent calls should go through normally.
    result = await breaker.call(_succeed)
    assert result == "ok"


@pytest.mark.asyncio
async def test_half_open_probe_failure_reopens_and_restarts_timer():
    """HALF_OPEN probe failure → back to OPEN, timer restarts."""
    breaker = CircuitBreaker(name="test_probe_fail", failure_threshold=5, cooldown_seconds=60.0)
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)

    frozen_base = breaker._last_failure_time
    with patch("app.reliability.circuit_breakers.time") as mock_time:
        mock_time.monotonic.return_value = frozen_base + 61.0
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)

    assert breaker._state.value == "open"
    # Timer should have been reset — last_failure_time should be ~frozen_base+61.
    assert breaker._last_failure_time >= frozen_base + 61.0


# ---------------------------------------------------------------------------
# CircuitOpenError does NOT itself count as a failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circuit_open_error_not_double_counted():
    """CircuitOpenError raised by THIS breaker must not increment the counter again."""
    breaker = CircuitBreaker(name="test_no_double_count", failure_threshold=5)
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_fail_connect)

    assert breaker._consecutive_failures == 5

    # Multiple rejected calls should not change the failure count.
    for _ in range(3):
        with pytest.raises(CircuitOpenError):
            await breaker.call(_succeed)

    assert breaker._consecutive_failures == 5


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_get_breaker_returns_same_instance():
    b1 = get_breaker("anthropic")
    b2 = get_breaker("anthropic")
    assert b1 is b2


def test_get_breaker_creates_different_instances_for_different_names():
    b_a = get_breaker("anthropic")
    b_g = get_breaker("groq")
    assert b_a is not b_g


# ---------------------------------------------------------------------------
# _is_transient_failure predicate (spot-checks)
# ---------------------------------------------------------------------------

def test_asyncio_timeout_is_transient():
    assert _is_transient_failure(TimeoutError())


def test_httpx_connect_error_is_transient():
    assert _is_transient_failure(httpx.ConnectError("refused"))


def test_httpx_timeout_is_transient():
    assert _is_transient_failure(httpx.TimeoutException("timeout", request=None))


def test_value_error_is_not_transient():
    assert not _is_transient_failure(ValueError("bad"))


def test_exception_with_503_status_code_is_transient():
    exc = Exception("server error")
    exc.status_code = 503  # type: ignore[attr-defined]
    assert _is_transient_failure(exc)


def test_exception_with_400_status_code_is_not_transient():
    exc = Exception("bad request")
    exc.status_code = 400  # type: ignore[attr-defined]
    assert not _is_transient_failure(exc)


def test_string_marker_overloaded_is_transient():
    assert _is_transient_failure(Exception("The model is overloaded, please retry"))


@pytest.mark.asyncio
async def test_non_transient_does_not_advance_failure_count():
    """Non-transient failures don't move the breaker toward OPEN."""
    breaker = CircuitBreaker(name="test_nontransient_count", failure_threshold=5)
    for _ in range(10):
        with pytest.raises(ValueError):
            await breaker.call(_fail_value_error)
    # Should still be CLOSED with 0 counted failures.
    assert breaker._state.value == "closed"
    assert breaker._consecutive_failures == 0
