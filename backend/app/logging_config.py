"""
Structured logging configuration using structlog.

Call configure_logging(settings) exactly once at application startup (in the
lifespan handler in main.py).  After that, obtain loggers anywhere via
get_logger().

Logging hygiene rules (from AGENTS.md — enforced by convention, not code):
- NEVER log Firebase ID tokens or any auth tokens
- NEVER log API keys (Anthropic, Groq, Tavily, etc.)
- NEVER log user-submitted idea text verbatim; log experiment_id + hash instead
- NEVER log full LLM prompts containing user content; log prompt name + token counts
- NEVER log database connection strings or service account paths
- Use user_id alone where possible; avoid tying emails to user_id without reason
"""

import logging
import logging.config

import structlog

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure stdlib logging and structlog for the application.

    JSON output in production (for Cloud Logging ingestion), human-readable
    console output in development.  A `service` and `environment` key are
    automatically bound to every log entry.

    Per-request context (request_id, user_id, experiment_id) is added by
    middleware via structlog.contextvars — the contextvars processor is
    wired here; the middleware that calls
    structlog.contextvars.bind_contextvars() is added in a later build step.
    """
    log_level = settings.log_level

    # --- stdlib logging ---------------------------------------------------
    # Route stdlib loggers (uvicorn, sqlalchemy, etc.) through structlog so
    # all logs share the same format and context.
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level),
    )
    # Silence overly verbose third-party loggers at WARNING by default.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # --- structlog processors ---------------------------------------------
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.is_production:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bind default context present on every log entry.
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        service="fivvle-backend",
        environment=settings.environment,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger.

    Args:
        name: Optional logger name, typically ``__name__`` of the calling module.

    Returns:
        A structlog BoundLogger that merges request-scoped context automatically.
    """
    return structlog.get_logger(name)
