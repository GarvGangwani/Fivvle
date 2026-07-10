"""Unit tests for Spark version save short-circuit and staleness helpers."""

from __future__ import annotations

from uuid import uuid4

from app.services.spark_version_service import _attachment_ids_equal, _is_stale


def test_attachment_ids_equal_ignores_order() -> None:
    a = uuid4()
    b = uuid4()
    assert _attachment_ids_equal([a, b], [b, a])
    assert not _attachment_ids_equal([a], [a, b])


def test_is_stale_null_or_current_not_stale() -> None:
    assert _is_stale(None, 3) is False
    assert _is_stale(3, 3) is False
    assert _is_stale(2, 0) is False
    assert _is_stale(2, 3) is True
