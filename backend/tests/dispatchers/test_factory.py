"""Unit tests for get_dispatcher factory (ADR 0009).

4 tests, one per branch:
  1. DISPATCHER_MODE=in_process (default) → InProcessDispatcher
  2. DISPATCHER_MODE=http + URL → HttpDispatcher
  3. DISPATCHER_MODE=http, no URL → ValueError with "RESEARCH_ENGINE_URL"
  4. Unknown mode bypassed past Pydantic → ValueError with "Unknown DISPATCHER_MODE"

Test 4 uses types.SimpleNamespace to bypass Pydantic's Literal constraint because
Settings itself rejects unknown modes at construction time — the guard at the
bottom of factory.py is defensive code for callers that don't use Settings.
"""

from __future__ import annotations

import types

import pytest

from app.dispatchers.factory import get_dispatcher
from app.dispatchers.http import HttpDispatcher
from app.dispatchers.in_process import InProcessDispatcher


def _ns(
    mode: str,
    url: str | None = None,
    *,
    oidc_audience: str | None = None,
) -> types.SimpleNamespace:
    """Minimal Settings-duck for factory tests (no I/O, no Pydantic)."""
    return types.SimpleNamespace(
        dispatcher_mode=mode,
        research_engine_url=url,
        oidc_audience=oidc_audience,
    )


# ---------------------------------------------------------------------------
# 1. in_process mode
# ---------------------------------------------------------------------------


def test_factory_in_process_mode_returns_in_process_dispatcher() -> None:
    """DISPATCHER_MODE=in_process → InProcessDispatcher holding get_sessionmaker ref."""
    settings = _ns("in_process")
    dispatcher = get_dispatcher(settings)  # type: ignore[arg-type]
    assert isinstance(dispatcher, InProcessDispatcher)


# ---------------------------------------------------------------------------
# 2. http mode with URL
# ---------------------------------------------------------------------------


def test_factory_http_mode_with_url_returns_http_dispatcher() -> None:
    """DISPATCHER_MODE=http + research_engine_url set → HttpDispatcher."""
    settings = _ns("http", url="https://region-project.cloudfunctions.net/research_engine")
    dispatcher = get_dispatcher(settings)  # type: ignore[arg-type]
    assert isinstance(dispatcher, HttpDispatcher)


# ---------------------------------------------------------------------------
# 3. http mode without URL
# ---------------------------------------------------------------------------


def test_factory_http_mode_without_url_raises_value_error() -> None:
    """DISPATCHER_MODE=http but research_engine_url=None → ValueError mentioning RESEARCH_ENGINE_URL."""
    settings = _ns("http", url=None)
    with pytest.raises(ValueError, match="RESEARCH_ENGINE_URL"):
        get_dispatcher(settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. Defensive guard — unknown mode bypassed past Pydantic's Literal check
# ---------------------------------------------------------------------------


def test_factory_invalid_mode_raises_value_error() -> None:
    """Unknown dispatcher_mode that slipped past Pydantic → ValueError defensive guard."""
    settings = _ns("cloud_run_direct")  # not a valid Literal value
    with pytest.raises(ValueError, match="Unknown DISPATCHER_MODE"):
        get_dispatcher(settings)  # type: ignore[arg-type]
