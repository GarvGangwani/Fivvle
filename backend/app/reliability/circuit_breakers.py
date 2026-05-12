"""Async circuit breaker implementation.

Hand-rolled — no circuitbreaker/pybreaker/tenacity dependency per .cursorrules ADR.

States:
  CLOSED    — normal operation; consecutive failure count maintained.
  OPEN      — failing fast; real calls rejected for ``cooldown_seconds``.
  HALF_OPEN — single probe allowed after cooldown expires; success → CLOSED,
              failure → OPEN (timer restarts).

Thresholds per .cursorrules "Circuit breakers around external APIs":
  - 5 consecutive transient failures  → CLOSED → OPEN
  - 60 s cooldown in OPEN             → transition to HALF_OPEN (one probe)

Only *transient* failures count toward the threshold: timeouts, connection
errors, 5xx responses, and 429 rate-limits.  Application-level 4xx errors
(bad request, not found, etc.) are caller bugs and do NOT count.

Usage:
    breaker = get_breaker("anthropic")
    result = await breaker.call(my_async_fn)
"""

from __future__ import annotations

import asyncio
import enum
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.logging_config import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Transient-failure predicate (shared with retry.py)
# ---------------------------------------------------------------------------

def _is_transient_failure(exc: BaseException) -> bool:
    """Return True when *exc* represents a transient transport/service failure.

    Conservative by design: when in doubt we treat an exception as transient
    because the cost of an extra cooldown is small compared to silently missing
    a real service outage.

    Covers:
    - Direct asyncio / httpx transport exceptions.
    - Exceptions from Anthropic/Groq/PRAW SDKs that expose a ``status_code``
      attribute (or nest a ``response.status_code``).
    - String-pattern matching for SDK-wrapped errors that don't expose a clean
      status code (e.g., "Connection reset", "Service unavailable" text from
      provider error messages).
    """
    # --- 1. Direct type checks -------------------------------------------
    if isinstance(
        exc,
        (
            asyncio.TimeoutError,
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    # --- 2. Status code check (Anthropic/Groq SDK, httpx.HTTPStatusError) -
    # Try .status_code directly, then .response.status_code as fallback.
    status_code: int | None = getattr(exc, "status_code", None)
    if status_code is None:
        response_obj = getattr(exc, "response", None)
        if response_obj is not None:
            status_code = getattr(response_obj, "status_code", None)
    if status_code in {408, 429, 500, 502, 503, 504}:
        return True

    # --- 3. String-pattern matching for SDK-wrapped transient errors -------
    exc_str = str(exc).lower()
    _transient_markers = (
        "connection",           # connection reset, connection refused, etc.
        "timeout",              # various SDK timeout messages
        "overloaded",           # Anthropic "overloaded_error"
        "internal server",      # 500 phrasing
        "service unavailable",  # 503 phrasing
        "bad gateway",          # 502 phrasing
        "gateway timeout",      # 504 phrasing
    )
    return any(marker in exc_str for marker in _transient_markers)


# ---------------------------------------------------------------------------
# CircuitOpenError
# ---------------------------------------------------------------------------

class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is OPEN.

    Attributes:
        breaker_name: Name of the circuit breaker that rejected the call.
        cooldown_remaining_seconds: Approximate remaining cooldown (may be 0.0
            when transitioning from HALF_OPEN back to OPEN).
    """

    def __init__(self, breaker_name: str, cooldown_remaining_seconds: float) -> None:
        super().__init__(
            f"Circuit '{breaker_name}' is OPEN; "
            f"retry in ~{cooldown_remaining_seconds:.1f}s"
        )
        self.breaker_name = breaker_name
        self.cooldown_remaining_seconds = cooldown_remaining_seconds


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class _State(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Async circuit breaker for a single named external dependency.

    Thread-safe via an ``asyncio.Lock``; all internal state mutations happen
    under the lock so concurrent coroutines see consistent transitions.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._state: _State = _State.CLOSED
        self._consecutive_failures: int = 0
        self._last_failure_time: float | None = None
        self._probe_in_flight: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers (must be called under _lock)
    # ------------------------------------------------------------------

    def _effective_state(self) -> _State:
        """Return current state, transitioning OPEN→HALF_OPEN if cooldown elapsed."""
        if self._state is _State.OPEN and self._last_failure_time is not None:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.cooldown_seconds:
                self._state = _State.HALF_OPEN
                self._probe_in_flight = False
                _logger.info(
                    "circuit breaker transitioning to half_open",
                    breaker=self.name,
                    elapsed_s=round(elapsed, 1),
                )
        return self._state

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def call(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        """Execute *coro_factory()* guarded by this breaker.

        Args:
            coro_factory: A zero-argument callable that returns an awaitable.
                Called at most once per ``call`` invocation.

        Returns:
            The awaitable's result on success.

        Raises:
            CircuitOpenError: When the breaker is OPEN (or HALF_OPEN with a
                probe already in flight).
            Any exception raised by *coro_factory()*: Re-raised after updating
                internal state.  Transient failures advance the failure counter;
                non-transient failures do NOT count.
        """
        async with self._lock:
            state = self._effective_state()

            if state is _State.OPEN:
                elapsed = time.monotonic() - self._last_failure_time  # type: ignore[operator]
                remaining = max(0.0, self.cooldown_seconds - elapsed)
                raise CircuitOpenError(self.name, remaining)

            if state is _State.HALF_OPEN:
                if self._probe_in_flight:
                    # A probe is already racing; reject parallel callers.
                    raise CircuitOpenError(self.name, 0.0)
                self._probe_in_flight = True

            is_probe = state is _State.HALF_OPEN

        # --- Execute outside the lock so we don't block other callers -----
        try:
            result = await coro_factory()
        except BaseException as exc:
            # CircuitOpenError from a *nested* breaker should not count as a
            # failure in THIS breaker and must not double-count.
            if isinstance(exc, CircuitOpenError):
                if is_probe:
                    async with self._lock:
                        self._probe_in_flight = False
                raise

            if _is_transient_failure(exc):
                async with self._lock:
                    if is_probe:
                        # Probe failure: back to OPEN, restart cooldown timer.
                        self._state = _State.OPEN
                        self._last_failure_time = time.monotonic()
                        self._probe_in_flight = False
                        _logger.info(
                            "circuit breaker probe failed, re-opening",
                            breaker=self.name,
                        )
                    else:
                        # Normal failure in CLOSED state.
                        self._consecutive_failures += 1
                        self._last_failure_time = time.monotonic()
                        if self._consecutive_failures >= self.failure_threshold:
                            self._state = _State.OPEN
                            _logger.info(
                                "circuit breaker opened",
                                breaker=self.name,
                                consecutive_failures=self._consecutive_failures,
                            )
            else:
                # Non-transient failure: don't count, but release probe slot.
                if is_probe:
                    async with self._lock:
                        self._probe_in_flight = False
            raise

        # --- Success path -------------------------------------------------
        async with self._lock:
            if is_probe:
                self._state = _State.CLOSED
                self._consecutive_failures = 0
                self._probe_in_flight = False
                _logger.info(
                    "circuit breaker closed after successful probe",
                    breaker=self.name,
                )
            else:
                # Any success in CLOSED resets the consecutive failure counter.
                if self._consecutive_failures > 0:
                    self._consecutive_failures = 0

        return result


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    """Return (or create) the named circuit breaker.

    Predefined names:
        "anthropic", "groq"        — LLM client (client.py)
        "tavily", "reddit", "google_trends" — integration wrappers
    """
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name)
    return _breakers[name]
