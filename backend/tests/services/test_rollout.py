"""Unit tests for app.services.rollout."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.services.rollout import AutoFireMode, _hash_bucket, should_auto_fire


def _find_uuid(*, bucket_lt: int | None = None, bucket_ge: int | None = None) -> UUID:
    for i in range(100_000):
        candidate = UUID(int=i)
        bucket = _hash_bucket(candidate)
        if bucket_lt is not None and bucket < bucket_lt:
            return candidate
        if bucket_ge is not None and bucket >= bucket_ge:
            return candidate
    raise AssertionError("could not find UUID for bucket constraint")


def test_off_always_false() -> None:
    uid = uuid4()
    assert should_auto_fire(uid, AutoFireMode.OFF) is False
    assert should_auto_fire(uid, "off") is False


def test_shadow_always_false() -> None:
    uid = uuid4()
    assert should_auto_fire(uid, AutoFireMode.SHADOW) is False
    assert should_auto_fire(uid, "shadow") is False


def test_on_always_true() -> None:
    uid = uuid4()
    assert should_auto_fire(uid, AutoFireMode.ON) is True
    assert should_auto_fire(uid, "on") is True


def test_cohort_10_respects_bucket() -> None:
    in_cohort = _find_uuid(bucket_lt=10)
    out_cohort = _find_uuid(bucket_ge=10)
    assert should_auto_fire(in_cohort, AutoFireMode.COHORT_10) is True
    assert should_auto_fire(out_cohort, AutoFireMode.COHORT_10) is False


def test_cohort_50_respects_bucket() -> None:
    in_cohort = _find_uuid(bucket_lt=50)
    out_cohort = _find_uuid(bucket_ge=50)
    assert should_auto_fire(in_cohort, AutoFireMode.COHORT_50) is True
    assert should_auto_fire(out_cohort, AutoFireMode.COHORT_50) is False


def test_should_auto_fire_accepts_string_and_enum() -> None:
    uid = uuid4()
    assert should_auto_fire(uid, "on") == should_auto_fire(uid, AutoFireMode.ON)


def test_hash_bucket_stable() -> None:
    uid = uuid4()
    assert _hash_bucket(uid) == _hash_bucket(uid)
