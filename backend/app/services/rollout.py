"""Progressive rollout helpers for chat-mode auto-fire."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from uuid import UUID


class AutoFireMode(StrEnum):
    OFF = "off"
    SHADOW = "shadow"
    COHORT_10 = "cohort_10"
    COHORT_50 = "cohort_50"
    ON = "on"


def should_auto_fire(experiment_id: UUID, mode: AutoFireMode | str) -> bool:
    """Deterministic cohort decision based on hash(experiment_id).

    OFF and SHADOW always return False.
    COHORT_10 returns True for ~10% of experiments (stable per UUID).
    COHORT_50 returns True for ~50%.
    ON returns True always.
    """
    m = AutoFireMode(mode) if isinstance(mode, str) else mode
    if m in (AutoFireMode.OFF, AutoFireMode.SHADOW):
        return False
    if m == AutoFireMode.ON:
        return True
    bucket = _hash_bucket(experiment_id)
    if m == AutoFireMode.COHORT_10:
        return bucket < 10
    if m == AutoFireMode.COHORT_50:
        return bucket < 50
    return False


def _hash_bucket(experiment_id: UUID) -> int:
    """Stable 0-99 bucket for an experiment UUID."""
    digest = hashlib.sha256(str(experiment_id).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100
