"""Sentry initialisation and redaction for the Fivvle backend.

Two public symbols:
- ``init_sentry(settings)`` — call once from the FastAPI lifespan startup.
- ``_before_send`` — passed to ``sentry_sdk.init`` as the redaction hook.

Security rules (AGENTS.md "Error handling", "Logging hygiene"):
- ``send_default_pii=False`` — PII is never attached automatically.
- ``_before_send`` scrubs auth tokens, cookies, and any header/field whose
  name looks like a secret, before the event leaves the process.
- Stack traces and exception messages are NOT touched — we need them to debug;
  the rule is "don't put secrets in exception messages in the first place".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.logging_config import get_logger

if TYPE_CHECKING:
    from app.config import Settings

_logger = get_logger(__name__)

# Header names (lowercased) that must always be redacted.
_REDACT_HEADER_NAMES = frozenset({"authorization", "cookie"})

# Substrings (lowercased) that trigger redaction when found in a header name.
_SENSITIVE_HEADER_SUBSTRINGS = ("token", "api-key", "apikey", "secret", "password")

# Top-level event field names that must be redacted if present.
_SENSITIVE_TOP_LEVEL_FIELDS = frozenset(
    {
        "firebase_token",
        "id_token",
        "anthropic_api_key",
        "groq_api_key",
        "tavily_api_key",
        "reddit_client_secret",
        "database_url",
    }
)


def _is_sensitive_header(name: str) -> bool:
    """Return True if a header name (any case) should be redacted.

    Underscores are normalised to hyphens before matching so that both
    HTTP header conventions (``api-key``) and Python dict-key conventions
    (``api_key``) are caught by the same set of patterns.
    """
    lower = name.lower().replace("_", "-")
    if lower in _REDACT_HEADER_NAMES:
        return True
    return any(sub in lower for sub in _SENSITIVE_HEADER_SUBSTRINGS)


def _redact_dict(d: dict[str, Any]) -> None:
    """Redact sensitive keys in-place, preserving structure."""
    for key in list(d.keys()):
        if _is_sensitive_header(key):
            d[key] = "[redacted]"


def _before_send(
    event: dict[str, Any],
    hint: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any] | None:
    """Scrub sensitive data from Sentry events before transmission.

    Rules (AGENTS.md "Error handling", "Logging hygiene"):
    - Redact ``Authorization`` and ``Cookie`` headers.
    - Redact any header whose lowercased name contains a sensitive substring.
    - Redact known sensitive top-level event fields.
    - Walk breadcrumb ``data`` dicts and apply the same header-name rules.
    - Never drop the event (always return it); never touch exception messages.
    - Defensive: missing or wrongly-typed fields log a warning and leave the
      event unchanged so a redaction bug never silently swallows errors.
    """
    try:
        # --- Request headers ---------------------------------------------------
        request = event.get("request")
        if isinstance(request, dict):
            headers = request.get("headers")
            if isinstance(headers, dict):
                _redact_dict(headers)
            elif headers is not None:
                _logger.warning(
                    "sentry before_send: unexpected headers type, skipping redaction",
                    headers_type=type(headers).__name__,
                )

        # --- Sensitive top-level fields ----------------------------------------
        for field in _SENSITIVE_TOP_LEVEL_FIELDS:
            if field in event:
                event[field] = "[redacted]"

        # --- Breadcrumb data ---------------------------------------------------
        breadcrumbs = event.get("breadcrumbs")
        if isinstance(breadcrumbs, dict):
            values = breadcrumbs.get("values")
            if isinstance(values, list):
                for crumb in values:
                    if isinstance(crumb, dict):
                        data = crumb.get("data")
                        if isinstance(data, dict):
                            _redact_dict(data)

    except Exception:
        # A bug in redaction must never silently swallow the event.
        _logger.warning(
            "sentry before_send: redaction raised an unexpected error; "
            "returning event unmodified"
        )

    return event


def init_sentry(settings: Settings) -> None:
    """Initialise the Sentry SDK.

    No-op when:
    - ``SENTRY_DSN`` is empty or ``None`` (fine in local dev).
    - ``ENVIRONMENT`` is ``"test"`` (prevents noise in test runs).

    Must be called from the FastAPI lifespan *before* any other
    initialisation that could raise, so startup errors are captured.
    """
    if not settings.sentry_dsn:
        _logger.info("sentry not initialised (no DSN configured)")
        return

    if settings.environment == "test":
        _logger.info("sentry not initialised (environment=test)")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        # Error capture only — no transaction sampling in MVP.
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        # PII is attached explicitly via set_user(); never implicitly.
        send_default_pii=False,
        integrations=[
            # FastAPI + Starlette: per-request scope isolation, route tagging.
            StarletteIntegration(),
            FastApiIntegration(),
            # SQLAlchemy: query breadcrumbs on errors.
            SqlalchemyIntegration(),
            # stdlib logging: ERROR-level log records become Sentry events.
            LoggingIntegration(
                level=logging.INFO,       # capture breadcrumbs at INFO+
                event_level=logging.ERROR,  # send as Sentry events at ERROR+
            ),
        ],
        before_send=_before_send,
        # release is unset — wired to build-tag injection in a later step.
    )

    _logger.info(
        "sentry initialised",
        environment=settings.environment,
    )
