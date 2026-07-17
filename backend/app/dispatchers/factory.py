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
from app.dispatchers.in_process_insight import InProcessInsightDispatcher
from app.dispatchers.in_process_landing_page import InProcessLandingPageDispatcher
from app.dispatchers.launch_kit import InProcessLaunchKitDispatcher
from app.dispatchers.protocol import (
    InsightDispatcher,
    LandingPageDispatcher,
    LaunchKitDispatcher,
    ResearchDispatcher,
)


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


def get_insight_dispatcher(settings: Settings) -> InsightDispatcher:
    """Construct and return the configured InsightDispatcher.

    Args:
        settings: The application settings singleton (from get_settings()).

    Returns:
        An InsightDispatcher implementation selected by settings.dispatcher_mode.

    Raises:
        NotImplementedError: If dispatcher_mode="http" (HttpInsightDispatcher
            ships in Step 7 of the insight generator build).
    """
    if settings.dispatcher_mode == "in_process":
        from app.db.session import get_sessionmaker  # noqa: PLC0415

        return InProcessInsightDispatcher(get_sessionmaker=get_sessionmaker)

    if settings.dispatcher_mode == "http":
        raise NotImplementedError(
            "HttpInsightDispatcher is not yet implemented. "
            "Pending Step 7 of b4-insight-generator. "
            "Set DISPATCHER_MODE=in_process or wait for the Cloud Function ship."
        )

    raise ValueError(  # pragma: no cover
        f"Unknown DISPATCHER_MODE: {settings.dispatcher_mode!r}. "
        "Allowed values: 'in_process', 'http'."
    )


def get_landing_page_dispatcher(settings: Settings) -> LandingPageDispatcher:
    """Construct and return the configured LandingPageDispatcher.

    Args:
        settings: The application settings singleton (from get_settings()).

    Returns:
        A LandingPageDispatcher implementation selected by settings.dispatcher_mode.

    Raises:
        NotImplementedError: If dispatcher_mode="http" (HttpLandingPageDispatcher
            deferred per ADR 0022).
    """
    if settings.dispatcher_mode == "in_process":
        from app.db.session import get_sessionmaker  # noqa: PLC0415

        return InProcessLandingPageDispatcher(get_sessionmaker=get_sessionmaker)

    if settings.dispatcher_mode == "http":
        raise NotImplementedError(
            "HttpLandingPageDispatcher is not yet implemented. "
            "Deferred per ADR 0022. "
            "Set DISPATCHER_MODE=in_process until the Cloud Function ships."
        )

    raise ValueError(  # pragma: no cover
        f"Unknown DISPATCHER_MODE: {settings.dispatcher_mode!r}. "
        "Allowed values: 'in_process', 'http'."
    )


def get_launch_kit_dispatcher(settings: Settings) -> LaunchKitDispatcher:
    """Construct and return the configured LaunchKitDispatcher.

    Args:
        settings: The application settings singleton (from get_settings()).

    Returns:
        A LaunchKitDispatcher implementation selected by settings.dispatcher_mode.

    Raises:
        NotImplementedError: If dispatcher_mode="http" (HttpLaunchKitDispatcher
            deferred — no Cloud Function for LaunchKit yet).
    """
    if settings.dispatcher_mode == "in_process":
        from app.db.session import get_sessionmaker  # noqa: PLC0415

        return InProcessLaunchKitDispatcher(get_sessionmaker=get_sessionmaker)

    if settings.dispatcher_mode == "http":
        raise NotImplementedError(
            "HttpLaunchKitDispatcher is not yet implemented. "
            "Set DISPATCHER_MODE=in_process until the Cloud Function ships."
        )

    raise ValueError(  # pragma: no cover
        f"Unknown DISPATCHER_MODE: {settings.dispatcher_mode!r}. "
        "Allowed values: 'in_process', 'http'."
    )


