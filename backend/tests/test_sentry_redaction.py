"""Unit tests for _before_send redaction logic.

All tests call ``_before_send`` directly with synthetic event dicts.
No real Sentry network calls are made.

Redaction rules (AGENTS.md "Logging hygiene", "Error handling"):
- ``Authorization`` and ``Cookie`` headers → ``"[redacted]"``, key preserved.
- Any header whose lowercased name contains token/api-key/apikey/secret/password.
- Known top-level fields: firebase_token, id_token, anthropic_api_key,
  groq_api_key, tavily_api_key, reddit_client_secret, database_url.
- Breadcrumb data dicts — same header-name rules.
- Exception messages are NOT touched.
- Missing/unexpected fields → warning logged, event returned unchanged.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.observability.sentry import _before_send


def _event(**kwargs: object) -> dict:
    """Minimal Sentry event skeleton."""
    return {"event_id": "test-event-id", **kwargs}


def _with_headers(**headers: str) -> dict:
    return _event(request={"headers": dict(headers)})


# ---------------------------------------------------------------------------
# Authorization header
# ---------------------------------------------------------------------------


def test_authorization_header_redacted() -> None:
    event = _with_headers(authorization="Bearer super-secret-token")
    result = _before_send(event, {})
    assert result is not None
    assert result["request"]["headers"]["authorization"] == "[redacted]"


def test_authorization_key_preserved_after_redaction() -> None:
    event = _with_headers(Authorization="Bearer abc")
    result = _before_send(event, {})
    assert "Authorization" in result["request"]["headers"]  # type: ignore[index]
    assert result["request"]["headers"]["Authorization"] == "[redacted]"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Cookie header
# ---------------------------------------------------------------------------


def test_cookie_header_redacted() -> None:
    event = _with_headers(cookie="session=abc123; tracking=xyz")
    result = _before_send(event, {})
    assert result["request"]["headers"]["cookie"] == "[redacted]"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Sensitive substring in header name (case-insensitive)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "header_name",
    [
        "X-API-Key",
        "x-api-key",
        "X-Auth-Token",
        "Api-Secret",
        "X-Password",
        "X-Apikey",
    ],
)
def test_sensitive_header_name_redacted(header_name: str) -> None:
    event = _with_headers(**{header_name: "should-be-gone"})
    result = _before_send(event, {})
    assert result["request"]["headers"][header_name] == "[redacted]"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Non-sensitive headers are left untouched
# ---------------------------------------------------------------------------


def test_non_sensitive_header_unchanged() -> None:
    event = _with_headers(**{"Content-Type": "application/json", "X-Request-ID": "abc"})
    result = _before_send(event, {})
    assert result["request"]["headers"]["Content-Type"] == "application/json"  # type: ignore[index]
    assert result["request"]["headers"]["X-Request-ID"] == "abc"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Top-level sensitive fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "firebase_token",
        "id_token",
        "anthropic_api_key",
        "groq_api_key",
        "tavily_api_key",
        "reddit_client_secret",
        "database_url",
    ],
)
def test_top_level_sensitive_field_redacted(field: str) -> None:
    event = _event(**{field: "super-secret-value"})
    result = _before_send(event, {})
    assert result[field] == "[redacted]"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Breadcrumb data
# ---------------------------------------------------------------------------


def test_breadcrumb_data_with_sensitive_key_redacted() -> None:
    event = _event(
        breadcrumbs={
            "values": [
                {"type": "http", "data": {"api_key": "sk-abc", "url": "https://example.com"}},
                {"type": "log", "data": {"message": "ok"}},
            ]
        }
    )
    result = _before_send(event, {})
    assert result["breadcrumbs"]["values"][0]["data"]["api_key"] == "[redacted]"  # type: ignore[index]
    # Non-sensitive key in same breadcrumb is untouched.
    assert result["breadcrumbs"]["values"][0]["data"]["url"] == "https://example.com"  # type: ignore[index]
    # Clean breadcrumb is untouched.
    assert result["breadcrumbs"]["values"][1]["data"]["message"] == "ok"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Exception messages are NOT redacted
# ---------------------------------------------------------------------------


def test_exception_messages_not_touched() -> None:
    event = _event(
        exception={
            "values": [
                {
                    "type": "ValueError",
                    "value": "Something went wrong with firebase_token handling",
                    "stacktrace": {"frames": []},
                }
            ]
        }
    )
    original_value = event["exception"]["values"][0]["value"]
    result = _before_send(event, {})
    assert result["exception"]["values"][0]["value"] == original_value  # type: ignore[index]


# ---------------------------------------------------------------------------
# Defensive: missing / unexpected-typed fields don't crash
# ---------------------------------------------------------------------------


def test_empty_event_returns_unchanged() -> None:
    event: dict = {}
    result = _before_send(event, {})
    assert result == {}


def test_event_without_request_key() -> None:
    event = _event(some_other_key="value")
    result = _before_send(event, {})
    assert result is not None
    assert result["some_other_key"] == "value"


def test_non_dict_headers_logs_warning_and_returns_event() -> None:
    """If headers is not a dict (unexpected), log a warning and return event unchanged."""
    event = _event(request={"headers": "not-a-dict"})
    with patch("app.observability.sentry._logger") as mock_logger:
        result = _before_send(event, {})
    mock_logger.warning.assert_called_once()
    assert result["request"]["headers"] == "not-a-dict"  # type: ignore[index]
