"""ResearchDispatcher protocol (ADR 0009).

All dispatcher implementations MUST conform to this Protocol.
Using typing.Protocol keeps implementations decoupled — no shared base class,
no import coupling between InProcessDispatcher and HttpDispatcher.

Structlog field contract (enforced by convention + code review — see README.md):
    dispatcher: str   — "in_process" | "http"
    experiment_id: str
    phase: str        — "dispatched" | "completed" | "failed"
    pipeline: str     — "research" | "insight" | "landing_page"
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ResearchDispatcher(Protocol):
    """Trigger the research pipeline for a given experiment.

    Implementations MUST return immediately (202 semantics).  The actual work
    runs asynchronously — either in a background asyncio task (InProcess) or in
    a Cloud Function invoked over HTTP (Http).

    Both implementations call the same run_research_engine_pipeline() entry
    point with the same experiment_id — the dispatcher controls *how* the work
    is triggered, not *what* it does.
    """

    async def dispatch(self, experiment_id: UUID) -> None:
        """Schedule the research pipeline for experiment_id.

        Must not block.  Failures to schedule (e.g. HTTP 5xx from the Cloud
        Function) should raise DispatchError so the /confirm endpoint can
        return an appropriate error rather than silently dropping the job.
        """
        ...


class InsightDispatcher(Protocol):
    """Trigger the insight generation pipeline for a given experiment.

    Implementations MUST return immediately (202 semantics). The actual work
    runs asynchronously — either in a background asyncio task (InProcess) or
    in a Cloud Function invoked over HTTP (Http — Step 7).

    Both implementations call the same insight_service.generate_insight_report()
    entry point with the same experiment_id, then transition Experiment.status
    to INSIGHT_READY (success) or INSIGHT_FAILED (any exception).

    Status transitions to INSIGHT_GENERATING are the responsibility of the
    /experiments/{id}/generate-insight route handler (Step 6b) BEFORE
    dispatch() is awaited. The dispatcher transitions to the terminal state.
    """

    async def dispatch(self, experiment_id: UUID) -> None:
        """Schedule the insight pipeline for experiment_id.

        Must not block. Failures to schedule (e.g. HTTP 5xx from the Cloud
        Function) should raise DispatchError so the route handler can return
        an appropriate error rather than silently dropping the job.
        """
        ...


class LandingPageDispatcher(Protocol):
    """Trigger the landing page generation pipeline for a given experiment.

    Implementations MUST return immediately (202 semantics). The actual work
    runs asynchronously — either in a background asyncio task (InProcess) or
    in a Cloud Function invoked over HTTP (deferred per ADR 0022).

    Both implementations call the same landing_page_service.generate_landing_page()
    entry point with the same experiment_id, page_goal, and template_id, then
    transition Experiment.status to LANDING_DRAFT (success) or RESEARCH_READY
    (any failure — rollback per ADR 0022).

    Status transitions to LANDING_GENERATING are the responsibility of the
    route handler or research-completion trigger BEFORE dispatch() is awaited.
    The dispatcher transitions to the terminal state.
    """

    async def dispatch(
        self,
        experiment_id: UUID,
        page_goal: str,
        template_id: str,
    ) -> None:
        """Schedule the landing page pipeline for experiment_id.

        Must not block. Failures to schedule (e.g. HTTP 5xx from the Cloud
        Function) should raise DispatchError so the route handler can return
        an appropriate error rather than silently dropping the job.
        """
        ...


class DispatchError(RuntimeError):
    """Raised when a dispatcher cannot schedule the research pipeline.

    Callers (the /confirm route handler) catch this and return HTTP 502.
    The full cause chain is logged server-side; only a sanitized message
    is returned to the client (AGENTS.md "Error handling").
    """
