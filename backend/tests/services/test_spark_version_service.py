"""Unit tests for Spark version save short-circuit and staleness helpers."""

from __future__ import annotations

from uuid import uuid4

from app.services.spark_version_service import (
    _attachment_ids_equal,
    _is_stale,
    _stale_reasons,
)


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


def test_stale_reasons_spark_only() -> None:
    assert _stale_reasons(1, 2, 3, 3) == ["spark"]


def test_stale_reasons_refined_idea_only() -> None:
    assert _stale_reasons(2, 2, 1, 3) == ["refined_idea"]


def test_stale_reasons_both_dimensions() -> None:
    assert _stale_reasons(1, 2, 1, 3) == ["spark", "refined_idea"]


def test_stale_reasons_neither() -> None:
    assert _stale_reasons(2, 2, 3, 3) == []
    assert _stale_reasons(None, 2, None, 3) == []
    assert _stale_reasons(1, 0, 1, 0) == []
