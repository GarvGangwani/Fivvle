"""Tests for RequestIDMiddleware.

Exercises:
- Missing X-Request-ID header → freshly generated UUID hex in response.
- Valid inbound X-Request-ID is echoed back unchanged.
- Malformed inbound X-Request-ID is ignored; a fresh ID is generated.
- ``request.state.request_id`` is accessible inside a handler.
- structlog records emitted during a request carry ``request_id``.
"""

from __future__ import annotations

import re

import pytest
import structlog
import structlog.contextvars
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.request_id import RequestIDMiddleware

# UUID4 hex: 32 lowercase hex chars (no hyphens).
_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with RequestIDMiddleware for testing."""
    mini = FastAPI()
    mini.add_middleware(RequestIDMiddleware)

    @mini.get("/ping")
    async def ping(request: Request) -> JSONResponse:
        return JSONResponse(
            {"request_id": request.state.request_id},
        )

    @mini.get("/contextvars")
    async def dump_contextvars(request: Request) -> JSONResponse:
        """Return the live structlog contextvars so tests can assert on them."""
        ctx = structlog.contextvars.get_contextvars()
        return JSONResponse({"contextvars": ctx})

    return mini


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    app = _make_app()
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Test: no inbound header → fresh UUID generated
# ---------------------------------------------------------------------------


def test_no_inbound_header_generates_uuid(test_client: TestClient) -> None:
    response = test_client.get("/ping")
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID", "")
    assert _UUID_HEX_RE.match(rid), f"Expected UUID hex, got: {rid!r}"


# ---------------------------------------------------------------------------
# Test: valid inbound ID is echoed back
# ---------------------------------------------------------------------------


def test_valid_inbound_id_echoed(test_client: TestClient) -> None:
    valid_id = "abc123def456"  # 12 chars, all alphanumeric — within 8–128
    response = test_client.get("/ping", headers={"X-Request-ID": valid_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == valid_id


# ---------------------------------------------------------------------------
# Test: malformed inbound IDs are rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "<script>alert(1)</script>",  # special characters
        "a" * 200,                    # too long (> 128)
        "short",                      # too short (< 8)
        "has spaces here",            # spaces not allowed
        "",                           # empty string (falsy — treated as missing)
    ],
)
def test_malformed_inbound_id_replaced(test_client: TestClient, bad_id: str) -> None:
    response = test_client.get("/ping", headers={"X-Request-ID": bad_id})
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID", "")
    # Must be a fresh UUID, never the malicious/malformed input.
    if bad_id:
        assert rid != bad_id
    assert _UUID_HEX_RE.match(rid), f"Expected UUID hex, got: {rid!r}"


# ---------------------------------------------------------------------------
# Test: request.state.request_id is accessible in the handler
# ---------------------------------------------------------------------------


def test_request_state_contains_request_id(test_client: TestClient) -> None:
    valid_id = "myrequest99"  # 11 chars, valid
    response = test_client.get("/ping", headers={"X-Request-ID": valid_id})
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == valid_id


# ---------------------------------------------------------------------------
# Test: structlog contextvar is bound during the request
#
# structlog.testing.capture_logs() bypasses merge_contextvars so we cannot
# use it to verify the binding. Instead we expose the live contextvars via a
# test route and verify the request_id key is present with the correct value.
# ---------------------------------------------------------------------------


def test_structlog_contextvar_bound_during_request(test_client: TestClient) -> None:
    valid_id = "ctxtest-abc1"  # 12 chars, valid
    response = test_client.get("/contextvars", headers={"X-Request-ID": valid_id})
    assert response.status_code == 200
    ctx = response.json()["contextvars"]
    assert ctx.get("request_id") == valid_id, (
        f"request_id not found in contextvars during request. Got: {ctx}"
    )
