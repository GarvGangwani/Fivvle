"""Spark version snapshots — save, list, and phase staleness helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.experiment_attachment import ExperimentAttachment
from app.db.models.experiment_spark_version import ExperimentSparkVersion
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.validation_report import ValidationReport
from app.logging_config import get_logger

_logger = get_logger(__name__)

_RAW_IDEA_MAX_LEN = 2000


@dataclass(frozen=True, slots=True)
class SparkPhaseVersionInfo:
    current_spark_version: int
    refine_spark_version: int | None
    evidence_spark_version: int | None
    launch_spark_version: int | None
    signal_spark_version: int | None
    refine_is_stale: bool
    evidence_is_stale: bool
    launch_is_stale: bool
    signal_is_stale: bool


def _attachment_ids_equal(a: list[UUID], b: list[UUID]) -> bool:
    return sorted(a) == sorted(b)


def _is_stale(phase_version: int | None, current: int) -> bool:
    if phase_version is None or current <= 0:
        return False
    return phase_version < current


async def get_latest_spark_version(
    db: AsyncSession,
    experiment_id: UUID,
) -> ExperimentSparkVersion | None:
    result = await db.execute(
        select(ExperimentSparkVersion)
        .where(ExperimentSparkVersion.experiment_id == experiment_id)
        .order_by(
            ExperimentSparkVersion.version_number.desc(),
            ExperimentSparkVersion.created_at.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_spark_version_id(
    db: AsyncSession,
    experiment_id: UUID,
) -> UUID | None:
    latest = await get_latest_spark_version(db, experiment_id)
    return latest.id if latest is not None else None


async def list_attachment_ids(
    db: AsyncSession,
    experiment_id: UUID,
) -> list[UUID]:
    result = await db.execute(
        select(ExperimentAttachment.id).where(
            ExperimentAttachment.experiment_id == experiment_id
        )
    )
    return list(result.scalars().all())


async def save_spark_version(
    db: AsyncSession,
    *,
    experiment: Experiment,
    user_id: UUID,
    raw_idea: str,
) -> ExperimentSparkVersion:
    """Create a new Spark version, or return the latest if content is identical."""
    if len(raw_idea) > _RAW_IDEA_MAX_LEN:
        raise ValueError(f"raw_idea must be at most {_RAW_IDEA_MAX_LEN} characters")

    attachment_ids = await list_attachment_ids(db, experiment.id)
    latest = await get_latest_spark_version(db, experiment.id)

    if (
        latest is not None
        and (latest.raw_idea or "") == raw_idea
        and _attachment_ids_equal(list(latest.attachment_ids_snapshot or []), attachment_ids)
    ):
        experiment.raw_idea = raw_idea
        experiment.spark_last_edited_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(experiment)
        await db.refresh(latest)
        return latest

    next_number = (latest.version_number + 1) if latest is not None else 1
    row = ExperimentSparkVersion(
        experiment_id=experiment.id,
        version_number=next_number,
        raw_idea=raw_idea,
        attachment_ids_snapshot=attachment_ids,
        created_by=user_id,
    )
    db.add(row)

    experiment.raw_idea = raw_idea
    experiment.spark_last_edited_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(row)
    await db.refresh(experiment)

    _logger.info(
        "spark version saved",
        experiment_id=str(experiment.id),
        version_number=row.version_number,
        attachment_count=len(attachment_ids),
    )
    return row


async def list_spark_versions(
    db: AsyncSession,
    experiment_id: UUID,
) -> list[ExperimentSparkVersion]:
    result = await db.execute(
        select(ExperimentSparkVersion)
        .where(ExperimentSparkVersion.experiment_id == experiment_id)
        .order_by(
            ExperimentSparkVersion.version_number.desc(),
            ExperimentSparkVersion.created_at.desc(),
        )
    )
    return list(result.scalars().all())


async def _version_number_for_id(
    db: AsyncSession,
    spark_version_id: UUID | None,
) -> int | None:
    if spark_version_id is None:
        return None
    result = await db.execute(
        select(ExperimentSparkVersion.version_number).where(
            ExperimentSparkVersion.id == spark_version_id
        )
    )
    return result.scalar_one_or_none()


async def fetch_spark_phase_version_info(
    db: AsyncSession,
    experiment: Experiment,
) -> SparkPhaseVersionInfo:
    latest = await get_latest_spark_version(db, experiment.id)
    current = latest.version_number if latest is not None else 0

    refine_version: int | None = None
    if experiment.thread_id is not None:
        thread_result = await db.execute(
            select(ChatThread.spark_version_id).where(
                ChatThread.id == experiment.thread_id
            )
        )
        refine_version = await _version_number_for_id(
            db, thread_result.scalar_one_or_none()
        )

    # Always query by experiment_id — do not touch lazy relationships
    # (MissingGreenlet under async SQLAlchemy).
    vr_result = await db.execute(
        select(ValidationReport.spark_version_id).where(
            ValidationReport.experiment_id == experiment.id
        )
    )
    evidence_version = await _version_number_for_id(
        db, vr_result.scalar_one_or_none()
    )

    lp_result = await db.execute(
        select(LandingPage.spark_version_id).where(
            LandingPage.experiment_id == experiment.id
        )
    )
    launch_version = await _version_number_for_id(
        db, lp_result.scalar_one_or_none()
    )

    ir_result = await db.execute(
        select(InsightReport.spark_version_id).where(
            InsightReport.experiment_id == experiment.id
        )
    )
    signal_version = await _version_number_for_id(
        db, ir_result.scalar_one_or_none()
    )

    return SparkPhaseVersionInfo(
        current_spark_version=current,
        refine_spark_version=refine_version,
        evidence_spark_version=evidence_version,
        launch_spark_version=launch_version,
        signal_spark_version=signal_version,
        refine_is_stale=_is_stale(refine_version, current),
        evidence_is_stale=_is_stale(evidence_version, current),
        launch_is_stale=_is_stale(launch_version, current),
        signal_is_stale=_is_stale(signal_version, current),
    )


async def stamp_chat_thread_spark_version(
    db: AsyncSession,
    thread: ChatThread,
    experiment_id: UUID,
) -> None:
    """Stamp Refine's chat thread with the current Spark version (once)."""
    if thread.spark_version_id is not None:
        return
    version_id = await get_latest_spark_version_id(db, experiment_id)
    if version_id is None:
        return
    thread.spark_version_id = version_id
    await db.flush()
