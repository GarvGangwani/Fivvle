"""Tests for app/reliability/rate_limit.py.

Tests the key functions (unit), the custom 429 handler, and the SlowAPI
integration using a lightweight in-process test app with very low limits
(2–3/minute).  No real sleep is used — we simply exhaust the request count
inside a single test call.  SlowAPI uses in-memory storage by default, and
each test creates a fresh Limiter instance, so counts never bleed between
tests.

Decorator order note (critical for slowapi to work):
    @app.get("/path")           ← outer: applied SECOND, registers async_wrapper
    @limiter.limit("N/minute")  ← inner: applied FIRST, wraps the function
    async def handler(request: Request, response: Response): ...

FastAPI calls the outer-registered function (async_wrapper from the inner
decorator). async_wrapper checks the rate limit then calls the original
handler. The `response: Response` parameter is required so FastAPI injects
a Response object that async_wrapper can write X-RateLimit-* headers into.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request as StarletteRequest

from app.middleware.error_handler import generic_exception_handler
from app.reliability.rate_limit import ip_key, rate_limit_exceeded_handler, user_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_starlette_request(
    client_host: str = "127.0.0.1",
    user_id: str | None = None,
) -> StarletteRequest:
    """Build a minimal Starlette Request for key-function unit tests."""
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
        "client": (client_host, 12345),
    }
    request = StarletteRequest(scope)
    if user_id is not None:
        user = MagicMock()
        user.id = user_id
        request.state.current_user = user
    return request


def _build_test_app(
    limit: str = "3/minute",
    key_func: Any = None,
    include_500_route: bool = False,
    user_id_from_header: bool = False,
    fixed_user_id: str | None = None,
) -> FastAPI:
    """Build a minimal FastAPI app for rate-limit integration tests.

    A fresh Limiter is created per call so in-memory counters are always
    clean — no shared state between tests.

    Decorator order (CRITICAL): the route decorator (@app.get) is OUTER
    (applied second) and @limiter.limit is INNER (applied first).  This
    ensures FastAPI registers the rate-limit wrapper, not the bare handler.

    Middleware registration (LIFO → innermost first):
      1. SlowAPI — innermost (delegates to the route decorator for limit checks)
      2. RequestID-like — sets request_id from X-Request-ID header
      3. User-like — sets current_user from X-Test-User-ID header or fixed value

    The `response: Response` parameter on test routes is required so that
    slowapi's async_wrapper can inject X-RateLimit-* headers after a
    successful (non-rate-limited) request.
    """
    if key_func is None:
        key_func = user_key

    local_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[],
        headers_enabled=True,
    )
    app = FastAPI()
    app.state.limiter = local_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    # Innermost: SlowAPI — for exempt routes (those with @limiter.limit decorator)
    # it defers immediately to the decorator wrapper via call_next.
    app.add_middleware(SlowAPIMiddleware)

    # Outer: sets request_id so rate_limit_exceeded_handler can read it.
    @app.middleware("http")
    async def _set_request_id(request: Request, call_next: Any) -> Any:
        request.state.request_id = request.headers.get("X-Request-ID", "test-req-id")
        response = await call_next(request)
        return response

    # Outer: sets current_user so user_key can read it.
    @app.middleware("http")
    async def _set_user(request: Request, call_next: Any) -> Any:
        uid: str | None = None
        if user_id_from_header:
            uid = request.headers.get("X-Test-User-ID")
        elif fixed_user_id is not None:
            uid = fixed_user_id
        if uid is not None:
            user = MagicMock()
            user.id = uid
            request.state.current_user = user
        return await call_next(request)

    # CORRECT decorator order: route (outer) wraps limiter wrapper (inner).
    # FastAPI registers the async_wrapper returned by @local_limiter.limit.
    @app.get("/test")
    @local_limiter.limit(limit, key_func=key_func)
    async def _test_route(request: Request, response: Response) -> dict:
        return {"ok": True}

    if include_500_route:
        @app.get("/error-route")
        @local_limiter.limit("10/minute", key_func=ip_key)
        async def _error_route(request: Request, response: Response) -> dict:
            raise ValueError("intentional error for testing")

    return app


# ---------------------------------------------------------------------------
# 1. Unit tests — key functions
# ---------------------------------------------------------------------------


def test_user_key_returns_user_id_when_current_user_set() -> None:
    """user_key returns 'user:<uuid>' when request.state.current_user exists."""
    uid = "550e8400-e29b-41d4-a716-446655440000"
    request = _make_starlette_request(user_id=uid)
    result = user_key(request)
    assert result == f"user:{uid}"


def test_user_key_falls_back_to_ip_when_no_current_user() -> None:
    """user_key returns 'ip:<addr>' when current_user is absent."""
    request = _make_starlette_request(client_host="10.0.0.1")
    result = user_key(request)
    assert result == "ip:10.0.0.1"


def test_ip_key_returns_ip() -> None:
    """ip_key always returns 'ip:<addr>'."""
    request = _make_starlette_request(client_host="192.168.1.42")
    result = ip_key(request)
    assert result == "ip:192.168.1.42"


# ---------------------------------------------------------------------------
# 2. User-keyed rate limiting
# ---------------------------------------------------------------------------


def test_user_rate_limit_allows_up_to_limit() -> None:
    """First 3 requests from same user all return 200."""
    app = _build_test_app(limit="3/minute", key_func=user_key, fixed_user_id="user-abc")
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(3):
            resp = client.get("/test")
            assert resp.status_code == 200


def test_user_rate_limit_returns_429_on_excess() -> None:
    """4th request from same user returns 429 with structured body."""
    app = _build_test_app(limit="3/minute", key_func=user_key, fixed_user_id="user-abc")
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(3):
            client.get("/test")
        resp = client.get("/test")

    assert resp.status_code == 429
    body = resp.json()
    assert body["error"] == "Rate limit exceeded"
    assert "request_id" in body
    assert "retry_after_seconds" in body
    assert isinstance(body["retry_after_seconds"], int)
    assert resp.headers.get("Retry-After") is not None


def test_different_users_have_isolated_rate_limits() -> None:
    """User A exhausting the limit does not affect User B."""
    app = _build_test_app(
        limit="3/minute",
        key_func=user_key,
        user_id_from_header=True,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(3):
            client.get("/test", headers={"X-Test-User-ID": "user-a"})
        resp_a = client.get("/test", headers={"X-Test-User-ID": "user-a"})
        resp_b = client.get("/test", headers={"X-Test-User-ID": "user-b"})

    assert resp_a.status_code == 429
    assert resp_b.status_code == 200


# ---------------------------------------------------------------------------
# 3. 429 response correlation with X-Request-ID
# ---------------------------------------------------------------------------


def test_429_body_contains_request_id_matching_inbound_header() -> None:
    """429 body request_id matches the inbound X-Request-ID header value."""
    app = _build_test_app(limit="2/minute", key_func=user_key, fixed_user_id="user-xyz")
    custom_id = "my-test-req-id-12345"
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/test", headers={"X-Request-ID": custom_id})
        client.get("/test", headers={"X-Request-ID": custom_id})
        resp = client.get("/test", headers={"X-Request-ID": custom_id})

    assert resp.status_code == 429
    assert resp.json()["request_id"] == custom_id
    assert resp.headers.get("X-Request-ID") == custom_id


def test_429_retry_after_header_is_positive_integer_string() -> None:
    """Retry-After header on 429 is a non-empty string representing a positive int."""
    app = _build_test_app(limit="2/minute", key_func=user_key, fixed_user_id="user-xyz")
    with TestClient(app, raise_server_exceptions=False) as client:
        for _ in range(2):
            client.get("/test")
        resp = client.get("/test")

    assert resp.status_code == 429
    retry_after = resp.headers.get("Retry-After", "")
    assert retry_after != ""
    assert int(retry_after) > 0


# ---------------------------------------------------------------------------
# 4. IP-keyed rate limiting
# ---------------------------------------------------------------------------


def test_ip_rate_limit_returns_429_after_limit() -> None:
    """IP-keyed route: 3rd call from same IP returns 429."""
    app = _build_test_app(limit="2/minute", key_func=ip_key)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.get("/test")
        client.get("/test")
        resp = client.get("/test")

    assert resp.status_code == 429
    assert resp.json()["error"] == "Rate limit exceeded"


# ---------------------------------------------------------------------------
# 5. Regression: rate limiting does not break the 500 error handler
# ---------------------------------------------------------------------------


def test_rate_limiting_does_not_interfere_with_500_handler() -> None:
    """A route raising ValueError still returns structured 500, not 429."""
    app = _build_test_app(include_500_route=True)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/error-route")

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "Something went wrong"
    assert "request_id" in body
