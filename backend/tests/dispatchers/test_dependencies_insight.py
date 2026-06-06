"""Unit tests for get_insight_dispatcher_dep."""

from __future__ import annotations

import types

import pytest

from app.dispatchers.dependencies import get_insight_dispatcher_dep


@pytest.mark.anyio
async def test_get_insight_dispatcher_dep_reads_from_app_state() -> None:
    """Dependency returns the insight dispatcher stored on app.state."""
    sentinel = object()
    app = types.SimpleNamespace(
        state=types.SimpleNamespace(insight_dispatcher=sentinel),
    )
    request = types.SimpleNamespace(app=app)

    result = await get_insight_dispatcher_dep(request)  # type: ignore[arg-type]

    assert result is sentinel
