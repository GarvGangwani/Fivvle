"""InProcessLandingPageDispatcher — dev/test implementation of LandingPageDispatcher.

Triggers the landing page pipeline via asyncio.create_task() so the route
returns immediately (202 semantics) while the pipeline runs concurrently in
the same process.

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
from app.services.landing_page_service import (
    LandingPageGenerationError,
    MissingValidationReportError,
    generate_landing_page,
)

logger = structlog.get_logger(__name__)


class InProcessLandingPageDispatcher:
    def __init__(self, get_sessionmaker: object) -> None:
        self._get_sessionmaker = get_sessionmaker

    async def dispatch(
        self,
        experiment_id: UUID,
        page_goal: str,
        template_id: str,
    ) -> None:
        log = logger.bind(
            dispatcher="in_process",
            pipeline="landing_page",
            experiment_id=str(experiment_id),
        )
        log.info("landing page pipeline dispatched", phase="dispatched")

        sessionmaker = self._get_sessionmaker()

        async def _run() -> None:
            async with sessionmaker() as session:
                try:
                    await generate_landing_page(
                        session,
                        experiment_id,
                        page_goal=page_goal,
                        template_id=template_id,
                    )
                    await session.commit()
                    await _transition_status(
                        session, experiment_id, ExperimentStatus.LANDING_DRAFT
                    )
                    log.info("landing page pipeline completed", phase="completed")
                except (
                    MissingValidationReportError,
                    LandingPageGenerationError,
                ) as exc:
                    log.warning(
                        "landing page pipeline failed (known error)",
                        phase="failed",
                        error_type=type(exc).__name__,
                    )
                    await _transition_status(
                        session, experiment_id, ExperimentStatus.RESEARCH_READY
                    )
                except Exception as exc:  # noqa: BLE001
                    log.exception(
                        "landing page pipeline crashed",
                        phase="failed",
                        error_type=type(exc).__name__,
                    )
                    await _transition_status(
                        session, experiment_id, ExperimentStatus.RESEARCH_READY
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
