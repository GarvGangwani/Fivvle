"""Dispatcher factory (ADR 0009).

Called once during app startup (app/main.py lifespan) and stored on
app.state.dispatcher.  All subsequent requests read from app.state rather
than calling this function again.

Selection logic:
    DISPATCHER_MODE=in_process  →  InProcessDispatcher (default, dev/test)
    DISPATCHER_MODE=http        →  HttpDispatcher (staging/prod — B3)

Fails loudly on misconfiguration (missing RESEARCH_ENGINE_URL when mode=http)
rather than falling back silently.  Explicit over implicit — per ADR 0009.
"""

from __future__ import annotations

from app.config import Settings
from app.dispatchers.http import HttpDispatcher
from app.dispatchers.in_process import InProcessDispatcher
from app.dispatchers.protocol import ResearchDispatcher


def get_dispatcher(settings: Settings) -> ResearchDispatcher:
    """Construct and return the configured ResearchDispatcher.

    Args:
        settings: The application settings singleton (from get_settings()).

    Returns:
        A ResearchDispatcher implementation selected by settings.dispatcher_mode.

    Raises:
        ValueError: If dispatcher_mode="http" but research_engine_url is unset.
        ValueError: If dispatcher_mode is an unknown value (should not happen —
            Pydantic's Literal constraint rejects it at Settings construction).
    """
    if settings.dispatcher_mode == "in_process":
        # Import get_sessionmaker lazily so this factory can be called
        # before init_engine() runs — the callable itself is resolved at
        # dispatch time, not here.
        from app.db.session import get_sessionmaker  # noqa: PLC0415

        return InProcessDispatcher(get_sessionmaker=get_sessionmaker)

    if settings.dispatcher_mode == "http":
        if not settings.research_engine_url:
            raise ValueError(
                "DISPATCHER_MODE=http requires RESEARCH_ENGINE_URL to be set. "
                "Add the Cloud Function HTTPS URL to your environment or .env file."
            )
        return HttpDispatcher(
            url=settings.research_engine_url,
            audience=settings.oidc_audience,
        )

    # Unreachable if Pydantic's Literal constraint is enforced — defensive guard.
    raise ValueError(  # pragma: no cover
        f"Unknown DISPATCHER_MODE: {settings.dispatcher_mode!r}. "
        "Allowed values: 'in_process', 'http'."
    )
