"""Unit tests for app.dispatchers.http.HttpDispatcher (ADR 0020).

All OIDC minting and HTTP calls are mocked — no real GCP or network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
import pytest
import structlog.testing
from google.auth.exceptions import DefaultCredentialsError

from app.dispatchers.http import HttpDispatcher
from app.dispatchers.protocol import DispatchError

CF_URL = "https://us-central1-proj.cloudfunctions.net/research_engine"
TEST_UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_TOKEN = "mock-oidc-token"


def _patch_async_client(*, status_code: int = 202, post_side_effect: Exception | None = None):
    """Return a context manager patching httpx.AsyncClient with a canned response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = "internal server detail must not leak"

    mock_client = AsyncMock()
    if post_side_effect is not None:
        mock_client.post = AsyncMock(side_effect=post_side_effect)
    else:
        mock_client.post = AsyncMock(return_value=mock_response)

    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
    mock_instance.__aexit__ = AsyncMock(return_value=None)

    return patch("app.dispatchers.http.httpx.AsyncClient", return_value=mock_instance)


@pytest.fixture
def mock_fetch_id_token():
    with patch("app.dispatchers.http.fetch_id_token", return_value=TEST_TOKEN) as m:
        yield m


async def test_dispatch_202_returns_none_and_logs_succeeded(
    mock_fetch_id_token: MagicMock,
) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    with _patch_async_client(status_code=202), structlog.testing.capture_logs() as cap:
        result = await dispatcher.dispatch(TEST_UUID)

    assert result is None
    succeeded = [
        e
        for e in cap
        if e.get("event") == "http dispatch succeeded" and e.get("phase") == "dispatch_succeeded"
    ]
    assert len(succeeded) == 1
    assert succeeded[0]["status_code"] == 202


async def test_dispatch_200_returns_none(mock_fetch_id_token: MagicMock) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    with _patch_async_client(status_code=200):
        result = await dispatcher.dispatch(TEST_UUID)
    assert result is None


async def test_dispatch_500_raises_dispatch_error_without_body(
    mock_fetch_id_token: MagicMock,
) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    with _patch_async_client(status_code=500):
        with pytest.raises(DispatchError, match=r"HTTP 500") as exc_info:
            await dispatcher.dispatch(TEST_UUID)
    assert "internal server detail" not in str(exc_info.value)


async def test_dispatch_401_raises_dispatch_error(mock_fetch_id_token: MagicMock) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    with _patch_async_client(status_code=401):
        with pytest.raises(DispatchError, match=r"HTTP 401"):
            await dispatcher.dispatch(TEST_UUID)


async def test_dispatch_timeout_raises_dispatch_error(mock_fetch_id_token: MagicMock) -> None:
    dispatcher = HttpDispatcher(CF_URL, timeout_seconds=10.0)
    with _patch_async_client(post_side_effect=httpx.TimeoutException("timed out")):
        with pytest.raises(DispatchError, match="timed out"):
            await dispatcher.dispatch(TEST_UUID)


async def test_dispatch_network_error_raises_transport_dispatch_error(
    mock_fetch_id_token: MagicMock,
) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    with _patch_async_client(post_side_effect=httpx.NetworkError("connection refused")):
        with pytest.raises(DispatchError, match="transport error"):
            await dispatcher.dispatch(TEST_UUID)


async def test_fetch_id_token_default_credentials_error_no_http_call(
    mock_fetch_id_token: MagicMock,
) -> None:
    mock_fetch_id_token.side_effect = DefaultCredentialsError("no credentials")
    dispatcher = HttpDispatcher(CF_URL)
    with _patch_async_client() as mock_client_cls:
        with pytest.raises(DispatchError, match="Failed to mint OIDC token"):
            await dispatcher.dispatch(TEST_UUID)
    mock_client_cls.assert_not_called()
    mock_fetch_id_token.assert_called_once()


async def test_audience_override_passed_to_fetch_id_token(
    mock_fetch_id_token: MagicMock,
) -> None:
    dispatcher = HttpDispatcher(CF_URL, audience="custom-audience")
    with _patch_async_client():
        await dispatcher.dispatch(TEST_UUID)
    assert mock_fetch_id_token.call_args[0][1] == "custom-audience"


async def test_audience_defaults_to_url(mock_fetch_id_token: MagicMock) -> None:
    dispatcher = HttpDispatcher("https://x", audience=None)
    with _patch_async_client():
        await dispatcher.dispatch(TEST_UUID)
    assert mock_fetch_id_token.call_args[0][1] == "https://x"


def _mock_client_with_post() -> tuple[MagicMock, AsyncMock]:
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    return mock_instance, mock_client


async def test_authorization_header_bearer_token(mock_fetch_id_token: MagicMock) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    mock_instance, mock_client = _mock_client_with_post()
    with patch("app.dispatchers.http.httpx.AsyncClient", return_value=mock_instance):
        await dispatcher.dispatch(TEST_UUID)
    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers == {"Authorization": f"Bearer {TEST_TOKEN}"}


async def test_request_body_experiment_id_json(mock_fetch_id_token: MagicMock) -> None:
    dispatcher = HttpDispatcher(CF_URL)
    mock_instance, mock_client = _mock_client_with_post()
    with patch("app.dispatchers.http.httpx.AsyncClient", return_value=mock_instance):
        await dispatcher.dispatch(TEST_UUID)
    assert mock_client.post.call_args.kwargs["json"] == {
        "experiment_id": str(TEST_UUID),
    }
