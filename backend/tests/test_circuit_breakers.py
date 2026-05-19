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

from unittest.mock import MagicMock, patch

import anthropic

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


def test_string_marker_overloaded_is_not_transient():
    # Updated for Bug B: allow-list classifier; no string-pattern matching.
    assert not _is_transient_failure(Exception("The model is overloaded, please retry"))


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


# ---------------------------------------------------------------------------
# Allow-list classifier (Bug B regression tests)
# ---------------------------------------------------------------------------

class TestIsTransientFailureAllowList:
    """Pin the allow-list semantics introduced in Bug B.

    Every test here documents a deliberate classification decision.
    Tests named *_is_not_transient prove the delete of string-pattern matching;
    tests named *_is_transient prove the allow-list still retries real signals.
    """

    def _mock_response(self, status_code: int) -> MagicMock:
        """Minimal mock httpx.Response for Anthropic exception construction."""
        r = MagicMock()
        r.status_code = status_code
        r.headers = MagicMock()
        r.request = MagicMock()
        return r

    # --- Tavily ---

    def test_tavily_bad_request_error_is_not_transient(self):
        """Headline Bug B regression: message contains 'connection' but still NOT transient."""
        from tavily import BadRequestError
        # Updated for Bug B: allow-list classifier; no string-pattern matching.
        exc = BadRequestError("connection refused")
        assert _is_transient_failure(exc) is False

    def test_tavily_invalid_api_key_error_is_not_transient(self):
        from tavily import InvalidAPIKeyError
        # Updated for Bug B: allow-list classifier; no string-pattern matching.
        exc = InvalidAPIKeyError("invalid key")
        assert _is_transient_failure(exc) is False

    def test_tavily_usage_limit_exceeded_is_not_transient(self):
        from tavily import UsageLimitExceededError
        # Updated for Bug B: allow-list classifier; no string-pattern matching.
        exc = UsageLimitExceededError("usage limit exceeded")
        assert _is_transient_failure(exc) is False

    # --- Anthropic non-transient ---

    def test_anthropic_bad_request_is_not_transient(self):
        """Message contains 'timeout' but status 400 is NOT in the transient set."""
        # Updated for Bug B: allow-list classifier; no string-pattern matching.
        exc = anthropic.BadRequestError(
            message="Request timeout: invalid content type",
            response=self._mock_response(400),
            body=None,
        )
        assert _is_transient_failure(exc) is False

    def test_anthropic_authentication_error_is_not_transient(self):
        exc = anthropic.AuthenticationError(
            message="authentication failed",
            response=self._mock_response(401),
            body=None,
        )
        assert _is_transient_failure(exc) is False

    def test_anthropic_permission_denied_is_not_transient(self):
        exc = anthropic.PermissionDeniedError(
            message="permission denied",
            response=self._mock_response(403),
            body=None,
        )
        assert _is_transient_failure(exc) is False

    def test_anthropic_not_found_is_not_transient(self):
        exc = anthropic.NotFoundError(
            message="not found",
            response=self._mock_response(404),
            body=None,
        )
        assert _is_transient_failure(exc) is False

    # --- pytrends ---

    def test_pytrends_response_error_is_transient(self):
        from pytrends.exceptions import ResponseError
        # Flaky Trends API — retried per .cursorrules / ADR 0015 trends wrapper.
        exc = ResponseError("response error", MagicMock())
        assert _is_transient_failure(exc) is True

    # --- Anthropic transient ---

    def test_anthropic_rate_limit_error_is_transient(self):
        exc = anthropic.RateLimitError(
            message="rate limited",
            response=self._mock_response(429),
            body=None,
        )
        assert _is_transient_failure(exc) is True

    def test_anthropic_api_connection_error_is_transient(self):
        exc = anthropic.APIConnectionError(request=MagicMock())
        assert _is_transient_failure(exc) is True

    def test_anthropic_internal_server_error_is_transient(self):
        exc = anthropic.InternalServerError(
            message="internal server error",
            response=self._mock_response(500),
            body=None,
        )
        assert _is_transient_failure(exc) is True

    def test_pytrends_too_many_requests_is_transient(self):
        from pytrends.exceptions import TooManyRequestsError
        exc = TooManyRequestsError("too many requests", MagicMock())
        assert _is_transient_failure(exc) is True

    # --- Message-content pins (prove string-pattern matching is gone) ---

    def test_arbitrary_exception_with_misleading_message_is_not_transient(self):
        """RuntimeError whose message matches every old string marker must NOT be transient."""
        # Updated for Bug B: allow-list classifier; no string-pattern matching.
        exc = RuntimeError(
            "connection refused due to timeout overload internal server bad gateway"
        )
        assert _is_transient_failure(exc) is False

    # --- Status code boundary tests ---

    def test_status_code_4xx_is_not_transient(self):
        exc = Exception("bad request")
        exc.status_code = 400  # type: ignore[attr-defined]
        # Updated for Bug B: allow-list classifier; no string-pattern matching.
        assert _is_transient_failure(exc) is False

    def test_status_code_503_is_transient(self):
        exc = Exception("service unavailable")
        exc.status_code = 503  # type: ignore[attr-defined]
        assert _is_transient_failure(exc) is True

    def test_status_code_via_response_attribute_is_detected(self):
        """Covers the nested .response.status_code path used by some SDKs."""
        exc = Exception("rate limited")
        mock_response = MagicMock()
        mock_response.status_code = 429
        exc.response = mock_response  # type: ignore[attr-defined]
        assert _is_transient_failure(exc) is True
