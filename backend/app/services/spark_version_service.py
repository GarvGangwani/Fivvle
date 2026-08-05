"""Spark version snapshots — fetch, stamp, and phase staleness helpers.

Version rows are write-frozen for new experiments after chat-driven capture
(PR3). Downstream artifacts still stamp/compare against existing versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.experiment_spark_version import ExperimentSparkVersion
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_v2 import LandingPageV2Spec
from app.db.models.validation_report import ValidationReport


@dataclass(frozen=True, slots=True)
class SparkPhaseVersionInfo:
    current_spark_version: int
    current_refined_idea_version: int
    current_edited_doc_version: int | None
    refine_spark_version: int | None
    evidence_spark_version: int | None
    launch_spark_version: int | None
    signal_spark_version: int | None
    refine_refined_idea_version: int | None
    evidence_refined_idea_version: int | None
    launch_refined_idea_version: int | None
    signal_refined_idea_version: int | None
    launch_edited_doc_version: int | None
    refine_is_stale: bool
    evidence_is_stale: bool
    launch_is_stale: bool
    signal_is_stale: bool
    refine_stale_reasons: list[str]
    evidence_stale_reasons: list[str]
    launch_stale_reasons: list[str]
    signal_stale_reasons: list[str]


@dataclass(frozen=True, slots=True)
class _LaunchStampSet:
    """One landing generator's cascade stamps (v1 or v2), as version numbers."""

    spark_version: int | None
    refined_idea_version: int | None
    edited_doc_version: int | None


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
    edited_doc_phase: int | None = None,
    edited_doc_current: int | None = None,
) -> list[str]:
    """Reasons a phase is stale relative to spark / refined_idea / edited_doc."""
    reasons: list[str] = []
    if _is_stale(spark_phase, spark_current):
        reasons.append("spark")
    if _is_stale(riv_phase, riv_current):
        reasons.append("refined_idea")
    if edited_doc_current is not None and _is_stale(
        edited_doc_phase, edited_doc_current
    ):
        reasons.append("edited_doc")
    return reasons


def _newest_optional_int(a: int | None, b: int | None) -> int | None:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def _merge_launch_stamp_sets(
    sets: list[_LaunchStampSet],
    *,
    spark_current: int,
    riv_current: int,
    edited_doc_current: int | None,
) -> tuple[int | None, int | None, int | None, list[str]]:
    """Merge v1/v2 launch stamps into response fields + deduped stale reasons.

    Response fields use the newest stamped value across generators that exist.
    Staleness reasons are the union of per-generator lag (max-lag semantics):
    if either generator is behind on a dimension, that reason surfaces.
    Empty ``sets`` → no launch output yet → not stale.
    """
    if not sets:
        return None, None, None, []

    newest_spark: int | None = None
    newest_riv: int | None = None
    newest_edv: int | None = None
    reasons: list[str] = []
    seen: set[str] = set()

    for stamps in sets:
        newest_spark = _newest_optional_int(newest_spark, stamps.spark_version)
        newest_riv = _newest_optional_int(newest_riv, stamps.refined_idea_version)
        newest_edv = _newest_optional_int(newest_edv, stamps.edited_doc_version)
        for reason in _stale_reasons(
            stamps.spark_version,
            spark_current,
            stamps.refined_idea_version,
            riv_current,
            stamps.edited_doc_version,
            edited_doc_current,
        ):
            if reason not in seen:
                seen.add(reason)
                reasons.append(reason)

    return newest_spark, newest_riv, newest_edv, reasons


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
            ValidationReport.edited_doc_version,
        ).where(ValidationReport.experiment_id == experiment.id)
    )
    vr_row = vr_result.one_or_none()
    evidence_version = await _version_number_for_id(
        db, vr_row[0] if vr_row is not None else None
    )
    evidence_riv = vr_row[1] if vr_row is not None else None
    current_edited_doc_version = vr_row[2] if vr_row is not None else None

    lp_result = await db.execute(
        select(
            LandingPage.spark_version_id,
            LandingPage.refined_idea_version,
            LandingPage.edited_doc_version,
        ).where(LandingPage.experiment_id == experiment.id)
    )
    lp_row = lp_result.one_or_none()

    lp_v2_result = await db.execute(
        select(
            LandingPageV2Spec.spark_version_id,
            LandingPageV2Spec.refined_idea_version,
            LandingPageV2Spec.edited_doc_version,
        ).where(LandingPageV2Spec.experiment_id == experiment.id)
    )
    lp_v2_row = lp_v2_result.one_or_none()

    launch_stamp_sets: list[_LaunchStampSet] = []
    if lp_row is not None:
        launch_stamp_sets.append(
            _LaunchStampSet(
                spark_version=await _version_number_for_id(db, lp_row[0]),
                refined_idea_version=lp_row[1],
                edited_doc_version=lp_row[2],
            )
        )
    if lp_v2_row is not None:
        launch_stamp_sets.append(
            _LaunchStampSet(
                spark_version=await _version_number_for_id(db, lp_v2_row[0]),
                refined_idea_version=lp_v2_row[1],
                edited_doc_version=lp_v2_row[2],
            )
        )

    (
        launch_version,
        launch_riv,
        launch_edited_doc_version,
        launch_reasons,
    ) = _merge_launch_stamp_sets(
        launch_stamp_sets,
        spark_current=current,
        riv_current=current_riv,
        edited_doc_current=current_edited_doc_version,
    )

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
    signal_reasons = _stale_reasons(signal_version, current, signal_riv, current_riv)

    return SparkPhaseVersionInfo(
        current_spark_version=current,
        current_refined_idea_version=current_riv,
        current_edited_doc_version=current_edited_doc_version,
        refine_spark_version=refine_version,
        evidence_spark_version=evidence_version,
        launch_spark_version=launch_version,
        signal_spark_version=signal_version,
        refine_refined_idea_version=refine_riv,
        evidence_refined_idea_version=evidence_riv,
        launch_refined_idea_version=launch_riv,
        signal_refined_idea_version=signal_riv,
        launch_edited_doc_version=launch_edited_doc_version,
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
