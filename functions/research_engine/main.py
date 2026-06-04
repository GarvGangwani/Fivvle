"""Cloud Function HTTP receiver for the research engine pipeline.

Per ADR 0020. Deploy with --no-cpu-throttling so the background thread
running the pipeline can complete after we return 202. See
docs/runbooks/research-engine-cloud-function.md.

The `app/` subpackage is populated at deploy time by the deploy script,
which rsyncs backend/app/ into this directory before `gcloud functions
deploy`. Imports below assume that subpackage exists in the deployment
archive.
"""

from __future__ import annotations

import asyncio
import threading
from uuid import UUID

import functions_framework
import structlog

from app.config import get_settings
from app.db.session import get_sessionmaker, init_engine
from app.services.research_engine_service import run_research_engine_pipeline

logger = structlog.get_logger()

_initialized = False
_init_lock = threading.Lock()


def _ensure_initialized() -> None:
    """Idempotent: init the DB engine once per container."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        init_engine(get_settings())
        _initialized = True


def _run_pipeline_blocking(experiment_id: UUID) -> None:
    """Run the async pipeline on this thread via a dedicated event loop."""
    try:
        asyncio.run(
            run_research_engine_pipeline(
                experiment_id=experiment_id,
                sessionmaker=get_sessionmaker(),
            )
        )
    except Exception as exc:
        logger.error(
            "pipeline thread crashed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )


@functions_framework.http
def research_engine_handler(request):
    """HTTP entry point. Parses experiment_id, fires background thread, returns 202."""
    try:
        body = request.get_json(silent=True) or {}
        raw = body.get("experiment_id")
        if not raw:
            logger.warning("dispatch rejected", reason="missing experiment_id")
            return ("missing experiment_id", 400)
        experiment_id = UUID(str(raw))
    except (ValueError, TypeError) as exc:
        logger.warning(
            "dispatch rejected",
            reason="invalid experiment_id",
            error_type=type(exc).__name__,
        )
        return ("invalid experiment_id", 400)

    try:
        _ensure_initialized()
    except Exception as exc:
        logger.error("init_engine failed", error_type=type(exc).__name__)
        return ("init failed", 500)

    thread = threading.Thread(
        target=_run_pipeline_blocking,
        args=(experiment_id,),
        name=f"pipeline-{experiment_id}",
        daemon=False,
    )
    thread.start()

    logger.info(
        "dispatch accepted",
        experiment_id=str(experiment_id),
        dispatcher="cloud_function",
    )
    return ("", 202)
