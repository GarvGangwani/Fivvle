"""Unit tests for get_insight_dispatcher factory."""

from __future__ import annotations

import types

import pytest

from app.dispatchers.factory import get_insight_dispatcher
from app.dispatchers.in_process_insight import InProcessInsightDispatcher


def _ns(mode: str) -> types.SimpleNamespace:
    """Minimal Settings-duck for factory tests (no I/O, no Pydantic)."""
    return types.SimpleNamespace(dispatcher_mode=mode)


def test_factory_in_process_mode_returns_in_process_insight_dispatcher() -> None:
    """DISPATCHER_MODE=in_process → InProcessInsightDispatcher."""
    settings = _ns("in_process")
    dispatcher = get_insight_dispatcher(settings)  # type: ignore[arg-type]
    assert isinstance(dispatcher, InProcessInsightDispatcher)


def test_factory_http_mode_raises_not_implemented_error() -> None:
    """DISPATCHER_MODE=http → NotImplementedError referencing Step 7."""
    settings = _ns("http")
    with pytest.raises(NotImplementedError, match="Step 7"):
        get_insight_dispatcher(settings)  # type: ignore[arg-type]
