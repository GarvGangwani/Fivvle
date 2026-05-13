"""Async retry decorator with exponential backoff and jitter.

Hand-rolled — no tenacity/backoff dependency per .cursorrules ADR.

Policy (per .cursorrules "Retry policy"):
  - Max 3 retries → 4 total attempts (initial + 3 retries).
  - Base delay 0.5 s, multiplier 2.0, per-attempt cap 8 s.
  - Jitter: delay × uniform(0.75, 1.25)  (i.e. ±25 %).
  - Only retry on *transient* failures (same predicate as circuit breakers).
  - Never retry on CircuitOpenError — the breaker already controls back-off.
  - Never retry on asyncio.CancelledError — honour cooperative cancellation.
  - Allow-list classifier (see _is_transient_failure in circuit_breakers.py):
    non-listed exceptions are never retried, regardless of message content.

Usage:
    @retry_async(max_retries=3)
    async def _call_through_breaker() -> SomeResult:
        return await get_breaker("anthropic").call(_do_call)
"""

from __future__ import annotations

import asyncio
import functools
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.logging_config import get_logger
from app.reliability.circuit_breakers import CircuitOpenError, _is_transient_failure

_logger = get_logger(__name__)

T = TypeVar("T")


def retry_async(
    *,
    max_retries: int = 3,
    base_delay: float = 0.5,
    multiplier: float = 2.0,
    max_delay: float = 8.0,
    jitter: float = 0.25,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Return a decorator that retries an async function on transient failures.

    Args:
        max_retries: Maximum number of *retry* attempts after the initial call
            (so total attempts = max_retries + 1).
        base_delay: Delay in seconds before the first retry.
        multiplier: Exponential growth factor for subsequent delays.
        max_delay: Per-attempt delay ceiling before jitter is applied.
        jitter: Fractional jitter range.  Actual delay is multiplied by
            ``random.uniform(1 - jitter, 1 + jitter)``.

    Returns:
        A decorator wrapping the target async callable with retry logic.
    """

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> T:
            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except asyncio.CancelledError:
                    # Honour cooperative cancellation — never suppress.
                    raise
                except CircuitOpenError:
                    # Retrying when the breaker is open is exactly what the
                    # breaker exists to prevent.  Propagate immediately.
                    raise
                except Exception as exc:
                    is_last = attempt >= max_retries
                    if not _is_transient_failure(exc) or is_last:
                        raise

                    # Exponential backoff with jitter.
                    raw_delay = min(base_delay * (multiplier**attempt), max_delay)
                    jittered_delay = raw_delay * random.uniform(1 - jitter, 1 + jitter)

                    _logger.info(
                        "retry_async: transient failure, will retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_s=round(jittered_delay, 3),
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(jittered_delay)

            # Unreachable: the for loop always raises or returns before here.
            raise RuntimeError("retry_async: unexpected loop exit")  # pragma: no cover

        return wrapper

    return decorator
