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
from app.dispatchers.protocol import LaunchKitDispatcher
from app.services.landing_page_service import (
    LandingPageGenerationError,
    MissingValidationReportError,
    generate_landing_page,
)

logger = structlog.get_logger(__name__)

_MAX_GENERATION_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 3.0

_active_tasks: dict[UUID, asyncio.Task[None]] = {}


def landing_generation_in_progress(experiment_id: UUID) -> bool:
    """True when an in-process landing page task is still running."""
    task = _active_tasks.get(experiment_id)
    return task is not None and not task.done()


class InProcessLandingPageDispatcher:
    def __init__(
        self,
        get_sessionmaker: object,
        launch_kit_dispatcher: LaunchKitDispatcher | None = None,
    ) -> None:
        self._get_sessionmaker = get_sessionmaker
        self._launch_kit_dispatcher = launch_kit_dispatcher

    async def dispatch(
        self,
        experiment_id: UUID,
        page_goal: str,
        template_id: str,
        regeneration_hint: str | None = None,
        was_live: bool = False,
    ) -> None:
        log = logger.bind(
            dispatcher="in_process",
            pipeline="landing_page",
            experiment_id=str(experiment_id),
        )
        log.info("landing page pipeline dispatched", phase="dispatched")

        sessionmaker = self._get_sessionmaker()

        async def _run() -> None:
            success_status = (
                ExperimentStatus.LANDING_LIVE
                if was_live
                else ExperimentStatus.LANDING_DRAFT
            )
            failure_status = (
                ExperimentStatus.LANDING_LIVE
                if was_live
                else ExperimentStatus.RESEARCH_READY
            )
            last_error: Exception | None = None

            for attempt in range(1, _MAX_GENERATION_ATTEMPTS + 1):
                async with sessionmaker() as session:
                    try:
                        await generate_landing_page(
                            session,
                            experiment_id,
                            page_goal=page_goal,
                            template_id=template_id,
                            regeneration_hint=regeneration_hint,
                        )
                        await session.commit()
                        await _transition_status(
                            session, experiment_id, success_status
                        )
                        log.info(
                            "landing page pipeline completed",
                            phase="completed",
                            attempt=attempt,
                        )
                        if self._launch_kit_dispatcher is not None:
                            try:
                                await self._launch_kit_dispatcher.dispatch(
                                    experiment_id
                                )
                            except Exception:  # noqa: BLE001
                                log.warning(
                                    "launch kit auto-dispatch failed",
                                    phase="launch_kit_dispatch_failed",
                                    experiment_id=str(experiment_id),
                                    exc_info=True,
                                )
                        return
                    except MissingValidationReportError as exc:
                        last_error = exc
                        await session.rollback()
                        log.warning(
                            "landing page pipeline failed (missing report)",
                            phase="failed",
                            error_type=type(exc).__name__,
                        )
                        break
                    except LandingPageGenerationError as exc:
                        last_error = exc
                        await session.rollback()
                        log.warning(
                            "landing page pipeline failed (known error)",
                            phase="failed",
                            error_type=type(exc).__name__,
                            attempt=attempt,
                        )
                        if attempt < _MAX_GENERATION_ATTEMPTS:
                            await asyncio.sleep(_RETRY_DELAY_SECONDS)
                            continue
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        await session.rollback()
                        log.exception(
                            "landing page pipeline crashed",
                            phase="failed",
                            error_type=type(exc).__name__,
                            attempt=attempt,
                        )
                        if attempt < _MAX_GENERATION_ATTEMPTS:
                            await asyncio.sleep(_RETRY_DELAY_SECONDS)
                            continue

            async with sessionmaker() as session:
                await _transition_status(
                    session, experiment_id, failure_status
                )
                log.warning(
                    "landing page pipeline exhausted retries",
                    phase="failed",
                    error_type=type(last_error).__name__ if last_error else None,
                )

        task = asyncio.create_task(_run())
        _active_tasks[experiment_id] = task

        def _cleanup(done_task: asyncio.Task[None]) -> None:
            current = _active_tasks.get(experiment_id)
            if current is done_task:
                _active_tasks.pop(experiment_id, None)
            if not done_task.cancelled() and done_task.exception() is not None:
                log.error(
                    "landing page background task exited with error",
                    error_type=type(done_task.exception()).__name__,
                )

        task.add_done_callback(_cleanup)


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
