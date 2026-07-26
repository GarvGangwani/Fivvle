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
    current_refined_idea_version: int
    refine_spark_version: int | None
    evidence_spark_version: int | None
    launch_spark_version: int | None
    signal_spark_version: int | None
    refine_refined_idea_version: int | None
    evidence_refined_idea_version: int | None
    launch_refined_idea_version: int | None
    signal_refined_idea_version: int | None
    refine_is_stale: bool
    evidence_is_stale: bool
    launch_is_stale: bool
    signal_is_stale: bool
    refine_stale_reasons: list[str]
    evidence_stale_reasons: list[str]
    launch_stale_reasons: list[str]
    signal_stale_reasons: list[str]


def _attachment_ids_equal(a: list[UUID], b: list[UUID]) -> bool:
    return sorted(a) == sorted(b)


def _is_stale(phase_version: int | None, current: int) -> bool:
    if phase_version is None or current <= 0:
        return False
    return phase_version < current


def _stale_reasons(
    spark_phase: int | None,
    spark_current: int,
    riv_phase: int | None,
    riv_current: int,
) -> list[str]:
    """Reasons a phase is stale relative to current spark / refined_idea versions."""
    reasons: list[str] = []
    if _is_stale(spark_phase, spark_current):
        reasons.append("spark")
    if _is_stale(riv_phase, riv_current):
        reasons.append("refined_idea")
    return reasons


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
    current_riv = experiment.refined_idea_version

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
    # Refine has no refined_idea_version stamp (chat thread is spark-only).
    refine_riv: int | None = None

    vr_result = await db.execute(
        select(
            ValidationReport.spark_version_id,
            ValidationReport.refined_idea_version,
        ).where(ValidationReport.experiment_id == experiment.id)
    )
    vr_row = vr_result.one_or_none()
    evidence_version = await _version_number_for_id(
        db, vr_row[0] if vr_row is not None else None
    )
    evidence_riv = vr_row[1] if vr_row is not None else None

    lp_result = await db.execute(
        select(
            LandingPage.spark_version_id,
            LandingPage.refined_idea_version,
        ).where(LandingPage.experiment_id == experiment.id)
    )
    lp_row = lp_result.one_or_none()
    launch_version = await _version_number_for_id(
        db, lp_row[0] if lp_row is not None else None
    )
    launch_riv = lp_row[1] if lp_row is not None else None

    ir_result = await db.execute(
        select(
            InsightReport.spark_version_id,
            InsightReport.refined_idea_version,
        ).where(InsightReport.experiment_id == experiment.id)
    )
    ir_row = ir_result.one_or_none()
    signal_version = await _version_number_for_id(
        db, ir_row[0] if ir_row is not None else None
    )
    signal_riv = ir_row[1] if ir_row is not None else None

    refine_reasons = _stale_reasons(refine_version, current, refine_riv, current_riv)
    evidence_reasons = _stale_reasons(
        evidence_version, current, evidence_riv, current_riv
    )
    launch_reasons = _stale_reasons(launch_version, current, launch_riv, current_riv)
    signal_reasons = _stale_reasons(signal_version, current, signal_riv, current_riv)

    return SparkPhaseVersionInfo(
        current_spark_version=current,
        current_refined_idea_version=current_riv,
        refine_spark_version=refine_version,
        evidence_spark_version=evidence_version,
        launch_spark_version=launch_version,
        signal_spark_version=signal_version,
        refine_refined_idea_version=refine_riv,
        evidence_refined_idea_version=evidence_riv,
        launch_refined_idea_version=launch_riv,
        signal_refined_idea_version=signal_riv,
        refine_is_stale=bool(refine_reasons),
        evidence_is_stale=bool(evidence_reasons),
        launch_is_stale=bool(launch_reasons),
        signal_is_stale=bool(signal_reasons),
        refine_stale_reasons=refine_reasons,
        evidence_stale_reasons=evidence_reasons,
        launch_stale_reasons=launch_reasons,
        signal_stale_reasons=signal_reasons,
    )


async def stamp_chat_thread_spark_version(
    db: AsyncSession,
    thread: ChatThread,
    experiment_id: UUID,
) -> None:
    """Stamp Refine's chat thread with the current Spark version (overwrite)."""
    version_id = await get_latest_spark_version_id(db, experiment_id)
    if version_id is None:
        return
    thread.spark_version_id = version_id
    await db.flush()
