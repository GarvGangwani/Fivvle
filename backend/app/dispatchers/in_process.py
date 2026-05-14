"""InProcessDispatcher — dev/test implementation of ResearchDispatcher (ADR 0009).

Triggers the research pipeline via asyncio.create_task() so /confirm returns
immediately (202 semantics) while the pipeline runs concurrently in the same
process.

Trade-offs vs HttpDispatcher (documented in ADR 0009 "Consequences"):
- No process isolation — pipeline shares FastAPI's event loop and DB pool.
- No durable retry — if the Cloud Run instance recycles mid-pipeline, the
  task is lost and the experiment is left in a mid-research state.
- Easier to iterate — one terminal, one log stream, tight prompt-tuning loop.

This dispatcher MUST NOT be used in staging or production.  The factory
(factory.py) enforces this via the DISPATCHER_MODE env var.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from app.dispatchers.protocol import DispatchError

logger = structlog.get_logger(__name__)


class InProcessDispatcher:
    """Run the research pipeline as an asyncio background task.

    get_sessionmaker is injected at construction time (via the factory) as a
    zero-arg callable that returns the async_sessionmaker.  This keeps the
    dispatcher decoupled from app.db.session's internals and makes unit tests
    clean: tests pass a lambda that returns a fake sessionmaker without
    monkey-patching module state.

    The sessionmaker is resolved at dispatch time (not construction time) by
    calling get_sessionmaker(), so there is no ordering dependency between
    get_dispatcher() and init_engine() in the lifespan handler.
    """

    def __init__(self, get_sessionmaker: object) -> None:
        # Zero-arg callable → async_sessionmaker[AsyncSession].
        # Named get_sessionmaker (not _get_sessionmaker) so static analysis
        # can follow the reference from factory.py.
        self._get_sessionmaker = get_sessionmaker

    async def dispatch(self, experiment_id: UUID) -> None:
        """Schedule the research pipeline and return immediately.

        The task runs concurrently.  Errors inside the pipeline are caught
        by run_research_engine_pipeline() and written to the experiment row
        (status=RESEARCH_FAILED, research_error_detail=...) — they do NOT
        propagate back to this coroutine.
        """
        log = logger.bind(
            dispatcher="in_process",
            experiment_id=str(experiment_id),
        )
        log.info("dispatcher dispatching", phase="dispatched")
        try:
            # Resolve the sessionmaker at dispatch time — get_sessionmaker() raises
            # RuntimeError if init_engine() hasn't run yet, which gives a clear
            # failure message rather than an AttributeError deep in SQLAlchemy.
            sessionmaker = self._get_sessionmaker()  # type: ignore[call-arg]

            # Import here (not at module top) to avoid circular imports:
            # dispatchers → research_engine_service → db.models → …
            from app.services.research_engine_service import (  # noqa: PLC0415
                run_research_engine_pipeline,
            )

            task = asyncio.create_task(
                run_research_engine_pipeline(
                    experiment_id=experiment_id,
                    sessionmaker=sessionmaker,
                ),
                name=f"research_pipeline_{experiment_id}",
            )
            # Attach a done-callback for fire-and-forget logging so unhandled
            # exceptions (bugs in run_research_engine_pipeline that escape its
            # internal try/except) surface in structlog rather than being
            # silently swallowed by asyncio.
            task.add_done_callback(
                lambda t: _log_task_outcome(t, experiment_id, log)
            )
        except Exception as exc:
            log.error(
                "dispatcher failed to create task",
                phase="failed",
                error_type=type(exc).__name__,
            )
            raise DispatchError("Failed to schedule research pipeline") from exc


def _log_task_outcome(
    task: asyncio.Task,  # type: ignore[type-arg]
    experiment_id: UUID,
    log: structlog.BoundLogger,
) -> None:
    """Done-callback: log any unexpected exception that escaped the pipeline."""
    if task.cancelled():
        log.warning(
            "dispatcher task cancelled",
            phase="failed",
            experiment_id=str(experiment_id),
        )
    elif exc := task.exception():
        # This path indicates a bug — run_research_engine_pipeline should
        # handle all expected failures internally.  Log the type only (no
        # message — may contain API keys or user data).
        log.error(
            "dispatcher task raised unexpected exception",
            phase="failed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
    else:
        log.info(
            "dispatcher task completed",
            phase="completed",
            experiment_id=str(experiment_id),
        )
