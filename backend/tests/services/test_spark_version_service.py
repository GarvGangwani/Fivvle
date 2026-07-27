"""Unit tests for Spark version save short-circuit and staleness helpers."""

from __future__ import annotations

from uuid import uuid4

from app.services.spark_version_service import (
    _LaunchStampSet,
    _attachment_ids_equal,
    _is_stale,
    _merge_launch_stamp_sets,
    _newest_optional_int,
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


def test_stale_reasons_edited_doc_only() -> None:
    assert _stale_reasons(2, 2, 3, 3, 1, 2) == ["edited_doc"]


def test_stale_reasons_edited_doc_null_phase_not_stale() -> None:
    # Pre-dimension landing stamp (NULL) is not treated as lagged.
    assert _stale_reasons(2, 2, 3, 3, None, 2) == []


def test_stale_reasons_edited_doc_current_zero_not_stale() -> None:
    assert _stale_reasons(2, 2, 3, 3, 0, 0) == []


def test_stale_reasons_launch_three_dimensions() -> None:
    assert _stale_reasons(1, 2, 1, 3, 1, 4) == [
        "spark",
        "refined_idea",
        "edited_doc",
    ]


def test_stale_reasons_spark_and_edited_doc() -> None:
    assert _stale_reasons(1, 2, 3, 3, 0, 1) == ["spark", "edited_doc"]


def test_stale_reasons_riv_and_edited_doc() -> None:
    assert _stale_reasons(2, 2, 1, 3, 1, 2) == ["refined_idea", "edited_doc"]


def test_newest_optional_int() -> None:
    assert _newest_optional_int(None, None) is None
    assert _newest_optional_int(None, 2) == 2
    assert _newest_optional_int(3, None) == 3
    assert _newest_optional_int(1, 4) == 4


def test_merge_launch_v2_only_drives_launch() -> None:
    """(a) v2 exists, v1 doesn't → v2 stamps drive launch."""
    spark, riv, edv, reasons = _merge_launch_stamp_sets(
        [
            _LaunchStampSet(
                spark_version=1,
                refined_idea_version=2,
                edited_doc_version=0,
            )
        ],
        spark_current=2,
        riv_current=2,
        edited_doc_current=1,
    )
    assert spark == 1
    assert riv == 2
    assert edv == 0
    assert reasons == ["spark", "edited_doc"]


def test_merge_launch_both_max_lag_wins() -> None:
    """(b) both exist → max-lag wins (union of reasons); response uses newest stamps."""
    spark, riv, edv, reasons = _merge_launch_stamp_sets(
        [
            _LaunchStampSet(
                spark_version=2,
                refined_idea_version=3,
                edited_doc_version=2,
            ),
            _LaunchStampSet(
                spark_version=1,
                refined_idea_version=3,
                edited_doc_version=1,
            ),
        ],
        spark_current=2,
        riv_current=3,
        edited_doc_current=2,
    )
    # Newest stamped across generators
    assert spark == 2
    assert riv == 3
    assert edv == 2
    # v2 lags on spark + edited_doc even though v1 is current
    assert reasons == ["spark", "edited_doc"]


def test_merge_launch_v1_only_unchanged_from_pr2() -> None:
    """(c) v1 exists, v2 doesn't → same as single-generator PR-2 behavior."""
    spark, riv, edv, reasons = _merge_launch_stamp_sets(
        [
            _LaunchStampSet(
                spark_version=2,
                refined_idea_version=3,
                edited_doc_version=1,
            )
        ],
        spark_current=2,
        riv_current=3,
        edited_doc_current=2,
    )
    assert spark == 2
    assert riv == 3
    assert edv == 1
    assert reasons == ["edited_doc"]


def test_merge_launch_neither_not_stale() -> None:
    spark, riv, edv, reasons = _merge_launch_stamp_sets(
        [],
        spark_current=2,
        riv_current=3,
        edited_doc_current=1,
    )
    assert spark is None
    assert riv is None
    assert edv is None
    assert reasons == []


def test_merge_launch_reasons_dedupe_across_generators() -> None:
    spark, riv, edv, reasons = _merge_launch_stamp_sets(
        [
            _LaunchStampSet(1, 1, 0),
            _LaunchStampSet(1, 2, 0),
        ],
        spark_current=2,
        riv_current=3,
        edited_doc_current=1,
    )
    assert spark == 1
    assert riv == 2
    assert edv == 0
    assert reasons == ["spark", "refined_idea", "edited_doc"]
