"""Tests for init_sentry().

All tests mock ``sentry_sdk.init`` to avoid real network calls.
Exercises:
- Empty/None DSN → no-op (sentry_sdk.init not called).
- ENVIRONMENT=test → no-op.
- Real-looking DSN with production environment → sentry_sdk.init called
  with the expected arguments.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import patch

from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.observability.sentry import init_sentry

_FAKE_DSN = "https://abc123@o999999.ingest.sentry.io/1234567"


def _settings(**overrides: object) -> SimpleNamespace:
    """Build a minimal settings-like object."""
    defaults = {
        "sentry_dsn": _FAKE_DSN,
        "environment": "production",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------


def test_empty_dsn_is_noop() -> None:
    settings = _settings(sentry_dsn=None)
    with patch("app.observability.sentry.sentry_sdk") as mock_sdk:
        init_sentry(settings)  # type: ignore[arg-type]
    mock_sdk.init.assert_not_called()


def test_empty_string_dsn_is_noop() -> None:
    settings = _settings(sentry_dsn="")
    with patch("app.observability.sentry.sentry_sdk") as mock_sdk:
        init_sentry(settings)  # type: ignore[arg-type]
    mock_sdk.init.assert_not_called()


def test_test_environment_is_noop() -> None:
    settings = _settings(sentry_dsn=_FAKE_DSN, environment="test")
    with patch("app.observability.sentry.sentry_sdk") as mock_sdk:
        init_sentry(settings)  # type: ignore[arg-type]
    mock_sdk.init.assert_not_called()


# ---------------------------------------------------------------------------
# Successful initialisation
# ---------------------------------------------------------------------------


def test_init_called_with_expected_kwargs() -> None:
    settings = _settings(sentry_dsn=_FAKE_DSN, environment="production")
    with patch("app.observability.sentry.sentry_sdk") as mock_sdk:
        init_sentry(settings)  # type: ignore[arg-type]

    mock_sdk.init.assert_called_once()
    _, kwargs = mock_sdk.init.call_args

    assert kwargs["dsn"] == _FAKE_DSN
    assert kwargs["environment"] == "production"
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["profiles_sample_rate"] == 0.0
    assert callable(kwargs["before_send"])


def test_init_includes_all_required_integrations() -> None:
    settings = _settings(sentry_dsn=_FAKE_DSN, environment="staging")
    with patch("app.observability.sentry.sentry_sdk") as mock_sdk:
        init_sentry(settings)  # type: ignore[arg-type]

    _, kwargs = mock_sdk.init.call_args
    integration_types = {type(i) for i in kwargs["integrations"]}

    assert FastApiIntegration in integration_types
    assert StarletteIntegration in integration_types
    assert SqlalchemyIntegration in integration_types
    assert LoggingIntegration in integration_types


def test_logging_integration_event_level_is_error() -> None:
    """LoggingIntegration must be created with event_level=ERROR.

    Sentry SDK 2.x does not expose the event_level as a readable instance
    attribute after construction, so we verify the constructor call args
    directly by patching LoggingIntegration in the observability module.
    """
    settings = _settings(sentry_dsn=_FAKE_DSN, environment="production")
    with (
        patch("app.observability.sentry.sentry_sdk"),
        patch("app.observability.sentry.LoggingIntegration") as mock_logging_cls,
    ):
        mock_logging_cls.return_value = object()  # sentinel instance
        init_sentry(settings)  # type: ignore[arg-type]

    mock_logging_cls.assert_called_once_with(
        level=logging.INFO,
        event_level=logging.ERROR,
    )


def test_development_environment_also_initialises_sentry() -> None:
    """init_sentry() with a DSN works in development too (not just production)."""
    settings = _settings(sentry_dsn=_FAKE_DSN, environment="development")
    with patch("app.observability.sentry.sentry_sdk") as mock_sdk:
        init_sentry(settings)  # type: ignore[arg-type]
    mock_sdk.init.assert_called_once()
