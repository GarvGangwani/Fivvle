"""Tests for the generic production error handler.

Exercises:
- Unhandled exceptions return 500 with a safe generic body (no stack trace).
- HTTPException still returns its normal status code and body (not caught
  by our handler).
- X-Request-ID is present in error responses (set by RequestIDMiddleware).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.error_handler import generic_exception_handler
from app.middleware.request_id import RequestIDMiddleware


def _make_app() -> FastAPI:
    """Minimal app with the error handler and request-ID middleware wired in."""
    mini = FastAPI()

    # Exception handler must be registered before middleware in this factory.
    mini.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    # Request ID middleware so X-Request-ID is available in error responses.
    mini.add_middleware(RequestIDMiddleware)

    @mini.get("/boom")
    async def boom() -> JSONResponse:
        raise ValueError("internal details that must not leak")

    @mini.get("/http-error")
    async def http_error() -> JSONResponse:
        raise HTTPException(status_code=400, detail="bad input")

    @mini.get("/ok")
    async def ok() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return mini


_client = TestClient(_make_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Unhandled exception → 500 with safe body
# ---------------------------------------------------------------------------


def test_unhandled_exception_returns_500() -> None:
    response = _client.get("/boom")
    assert response.status_code == 500


def test_unhandled_exception_body_is_generic() -> None:
    response = _client.get("/boom")
    body = response.json()
    assert body["error"] == "Something went wrong"
    assert "request_id" in body


def test_unhandled_exception_body_has_no_stack_trace() -> None:
    response = _client.get("/boom")
    raw = response.text
    # Ensure no internal details are leaked.
    assert "ValueError" not in raw
    assert "internal details" not in raw
    assert "Traceback" not in raw
    assert "boom" not in raw  # function name must not appear


def test_unhandled_exception_request_id_in_body() -> None:
    """The request_id in the body should be a non-empty string."""
    response = _client.get("/boom")
    body = response.json()
    assert isinstance(body.get("request_id"), str)
    assert body["request_id"]  # not empty


# ---------------------------------------------------------------------------
# HTTPException → FastAPI's default handler (NOT caught by our handler)
# ---------------------------------------------------------------------------


def test_http_exception_not_caught_by_generic_handler() -> None:
    response = _client.get("/http-error")
    assert response.status_code == 400


def test_http_exception_body_matches_fastapi_default() -> None:
    response = _client.get("/http-error")
    body = response.json()
    assert body.get("detail") == "bad input"
    # Our handler's key is "error"; FastAPI's default uses "detail".
    assert "error" not in body


# ---------------------------------------------------------------------------
# X-Request-ID header is set on error responses
# ---------------------------------------------------------------------------


def test_request_id_header_present_on_error_response() -> None:
    response = _client.get("/boom")
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]  # non-empty


def test_request_id_header_present_on_success_response() -> None:
    response = _client.get("/ok")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_error_response_request_id_matches_inbound_header() -> None:
    """The X-Request-ID on a 500 response must echo the inbound header value.

    Regression guard: the error handler must reuse request.state.request_id
    (set by RequestIDMiddleware from the inbound header) — not generate a
    fresh UUID for each error response.
    """
    inbound_id = "abc123def456789"  # 15 chars — valid pattern for RequestIDMiddleware
    response = _client.get("/boom", headers={"X-Request-ID": inbound_id})
    assert response.status_code == 500
    # Header must be the inbound value, not a freshly generated UUID.
    assert response.headers.get("X-Request-ID") == inbound_id
    # Body request_id must also match.
    assert response.json()["request_id"] == inbound_id
