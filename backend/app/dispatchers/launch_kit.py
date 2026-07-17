"""InProcessLaunchKitDispatcher — dev/test implementation of LaunchKitDispatcher.

Triggers LaunchKit generation via asyncio.create_task() so
POST /experiments/{id}/generate-launch-kit returns immediately (202 semantics)
while generation runs concurrently in the same process.

Unlike the research / insight / landing dispatchers, LaunchKit generation does
NOT drive Experiment.status — the kit is a side artifact of an already-live
experiment. There is therefore no terminal status transition here. On failure we
log and stop; the founder can retry via the endpoint (which regenerates).

Same trade-offs as the other in-process dispatchers (no process isolation, no
durable retry on Cloud Run instance recycle). MUST NOT be used in staging or
prod — factory.py enforces this via DISPATCHER_MODE.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from app.services.launch_kit_service import (
    LaunchKitLLMError,
    LaunchKitPreconditionError,
    generate_launch_kit,
)

logger = structlog.get_logger(__name__)


class InProcessLaunchKitDispatcher:
    def __init__(self, get_sessionmaker: object) -> None:
        self._get_sessionmaker = get_sessionmaker

    async def dispatch(self, experiment_id: UUID) -> None:
        log = logger.bind(
            dispatcher="in_process",
            pipeline="launch_kit",
            experiment_id=str(experiment_id),
        )
        log.info("launch kit pipeline dispatched", phase="dispatched")

        sessionmaker = self._get_sessionmaker()

        async def _run() -> None:
            async with sessionmaker() as session:
                try:
                    await generate_launch_kit(session, experiment_id)
                    await session.commit()
                    log.info("launch kit pipeline completed", phase="completed")
                except (LaunchKitPreconditionError, LaunchKitLLMError) as exc:
                    await session.rollback()
                    log.warning(
                        "launch kit pipeline failed (known error)",
                        phase="failed",
                        error_type=type(exc).__name__,
                    )
                except Exception as exc:  # noqa: BLE001
                    await session.rollback()
                    log.exception(
                        "launch kit pipeline crashed",
                        phase="failed",
                        error_type=type(exc).__name__,
                    )

        asyncio.create_task(_run())
