"""InProcessInsightDispatcher — dev/test implementation of InsightDispatcher.

Triggers the insight pipeline via asyncio.create_task() so the
/experiments/{id}/generate-insight route returns immediately (202 semantics)
while the pipeline runs concurrently in the same process.

Same trade-offs as InProcessDispatcher (no process isolation, no durable
retry on Cloud Run instance recycle). MUST NOT be used in staging or prod
— factory.py enforces this via DISPATCHER_MODE.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import select

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.services.analytics_aggregator import LandingPageNotLiveError
from app.services.insight_service import (
    InsightCitationHallucinatedError,
    MissingValidationReportError,
    generate_insight_report,
)

logger = structlog.get_logger(__name__)


class InProcessInsightDispatcher:
    def __init__(self, get_sessionmaker: object) -> None:
        self._get_sessionmaker = get_sessionmaker

    async def dispatch(self, experiment_id: UUID) -> None:
        log = logger.bind(
            dispatcher="in_process",
            pipeline="insight",
            experiment_id=str(experiment_id),
        )
        log.info("insight pipeline dispatched", phase="dispatched")

        sessionmaker = self._get_sessionmaker()

        async def _run() -> None:
            async with sessionmaker() as session:
                try:
                    await generate_insight_report(session, experiment_id)
                    await session.commit()
                    await _transition_status(
                        session, experiment_id, ExperimentStatus.INSIGHT_READY
                    )
                    log.info("insight pipeline completed", phase="completed")
                except (
                    MissingValidationReportError,
                    LandingPageNotLiveError,
                    InsightCitationHallucinatedError,
                ) as exc:
                    log.warning(
                        "insight pipeline failed (known error)",
                        phase="failed",
                        error_type=type(exc).__name__,
                    )
                    await _transition_status(
                        session, experiment_id, ExperimentStatus.INSIGHT_FAILED
                    )
                except Exception as exc:  # noqa: BLE001
                    log.exception(
                        "insight pipeline crashed",
                        phase="failed",
                        error_type=type(exc).__name__,
                    )
                    await _transition_status(
                        session, experiment_id, ExperimentStatus.INSIGHT_FAILED
                    )

        asyncio.create_task(_run())


async def _transition_status(
    session, experiment_id: UUID, status: ExperimentStatus
) -> None:
    """Best-effort status transition. Uses a fresh select to avoid stale state
    after the service's own flush."""
    result = await session.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()
    if experiment is None:
        return
    experiment.status = status
    await session.commit()
