"""Tests for app.utils.safe_fetch.

All network calls (socket.getaddrinfo, httpx.AsyncClient) are mocked.
No real DNS lookups or HTTP requests are made.

Covers:
- Scheme allowlist (file://, gopher://, data: rejected)
- Empty hostname rejection
- Private IPv4 ranges (127.x, 10.x, 192.168.x, 172.16.x, 169.254.x)
- Private IPv6 ranges (::1, fe80::1)
- Mixed public/private resolved IPs → rejected
- Public IP → proceeds (httpx response mocked)
- Redirect to private IP rejected after re-validation
- Redirect depth > 5 raises UnsafeURLError("redirect_loop")
- Response body > max_response_bytes raises UnsafeURLError("response_too_large")
"""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.utils.safe_fetch import UnsafeURLError, safe_fetch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _addr_info(ip: str) -> list[tuple]:
    """Build a minimal getaddrinfo result list for a single IP."""
    # (family, type, proto, canonname, sockaddr)
    # sockaddr = (address, port)
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]


def _addr_info_ipv6(ip: str) -> list[tuple]:
    return [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", (ip, 0, 0, 0))]


def _mock_httpx_response(
    status_code: int = 200,
    content: bytes = b"hello",
    headers: dict | None = None,
    is_redirect: bool = False,
    location: str | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content
    resp.is_redirect = is_redirect
    resp.headers = MagicMock()
    def _headers_get(k: str, default: str = "") -> str:
        if k == "location":
            return location or default
        if k == "content-length":
            return str(len(content))
        return default

    resp.headers.get = MagicMock(side_effect=_headers_get)
    resp.aread = AsyncMock()
    return resp


def _patch_dns(ip: str, ipv6: bool = False):
    """Patch socket.getaddrinfo to return a single IP."""
    infos = _addr_info_ipv6(ip) if ipv6 else _addr_info(ip)
    return patch("app.utils.safe_fetch.socket.getaddrinfo", return_value=infos)


# ---------------------------------------------------------------------------
# Scheme checks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_file_scheme_raises():
    with pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("file:///etc/passwd")
    assert exc_info.value.reason == "scheme"


@pytest.mark.asyncio
async def test_gopher_scheme_raises():
    with pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("gopher://evil.com/1")
    assert exc_info.value.reason == "scheme"


@pytest.mark.asyncio
async def test_data_scheme_raises():
    with pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("data:text/plain,hello")
    assert exc_info.value.reason == "scheme"


# ---------------------------------------------------------------------------
# Hostname check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_hostname_raises():
    with pytest.raises(UnsafeURLError):
        # urlparse("http://") → hostname is None/empty
        await safe_fetch("http://")


# ---------------------------------------------------------------------------
# Private IP rejections
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("ip", [
    "127.0.0.1",
    "10.0.0.5",
    "192.168.1.1",
    "172.16.0.1",
    "0.0.0.1",
])
async def test_private_ipv4_raises(ip):
    with _patch_dns(ip), pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("http://internal.example.com/path")
    assert exc_info.value.reason == "private_ip"


@pytest.mark.asyncio
async def test_aws_metadata_endpoint_ip_raises():
    """169.254.169.254 is the canonical SSRF target (AWS/GCP metadata)."""
    with _patch_dns("169.254.169.254"), pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("http://metadata.internal/latest")
    assert exc_info.value.reason == "private_ip"


@pytest.mark.asyncio
async def test_ipv6_loopback_raises():
    with _patch_dns("::1", ipv6=True), pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("http://v6host.example.com/")
    assert exc_info.value.reason == "private_ip"


@pytest.mark.asyncio
async def test_ipv6_link_local_raises():
    with _patch_dns("fe80::1", ipv6=True), pytest.raises(UnsafeURLError) as exc_info:
        await safe_fetch("http://v6host.example.com/")
    assert exc_info.value.reason == "private_ip"


@pytest.mark.asyncio
async def test_mixed_public_and_private_ip_raises():
    """If ANY resolved IP is private we must reject, even if others are public."""
    mixed_infos = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0)),
    ]
    with (
        patch("app.utils.safe_fetch.socket.getaddrinfo", return_value=mixed_infos),
        pytest.raises(UnsafeURLError) as exc_info,
    ):
        await safe_fetch("http://cdn.example.com/")
    assert exc_info.value.reason == "private_ip"


# ---------------------------------------------------------------------------
# Public IP proceeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_public_ip_proceeds_and_returns_response():
    """Public IP (e.g. example.com → 93.184.216.34) should pass through."""
    fake_response = _mock_httpx_response(status_code=200, content=b"<html>hi</html>")

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=fake_response)

    with (
        _patch_dns("93.184.216.34"),
        patch("app.utils.safe_fetch.httpx.AsyncClient", return_value=mock_client),
    ):
        response = await safe_fetch("http://example.com/")

    assert response is fake_response


# ---------------------------------------------------------------------------
# Redirect handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redirect_to_private_ip_raises():
    """A 302 pointing to an internal host must be rejected after re-validation."""
    # First request returns a redirect to an internal host.
    redirect_response = _mock_httpx_response(
        status_code=302,
        content=b"",
        is_redirect=True,
        location="http://internal-host.local/secret",
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=redirect_response)

    # Public IP for the original request, private for the redirect target.
    def _selective_getaddrinfo(host, *args, **kwargs):
        if host == "example.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
        # internal-host.local resolves to a private IP.
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.5", 0))]

    with (
        patch("app.utils.safe_fetch.socket.getaddrinfo", side_effect=_selective_getaddrinfo),
        patch("app.utils.safe_fetch.httpx.AsyncClient", return_value=mock_client),
        pytest.raises(UnsafeURLError) as exc_info,
    ):
        await safe_fetch("http://example.com/")
    assert exc_info.value.reason == "private_ip"


@pytest.mark.asyncio
async def test_redirect_depth_exceeded_raises_redirect_loop():
    """More than 5 redirect hops raises UnsafeURLError('redirect_loop')."""
    # Each call returns a redirect to itself — creating an infinite loop.
    redirect_response = _mock_httpx_response(
        status_code=301,
        content=b"",
        is_redirect=True,
        location="http://example.com/loop",
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=redirect_response)

    with (
        _patch_dns("93.184.216.34"),
        patch("app.utils.safe_fetch.httpx.AsyncClient", return_value=mock_client),
        pytest.raises(UnsafeURLError) as exc_info,
    ):
        await safe_fetch("http://example.com/loop")
    assert exc_info.value.reason == "redirect_loop"


# ---------------------------------------------------------------------------
# Response size cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_too_large_raises():
    """Response content exceeding max_response_bytes raises the correct error."""
    large_content = b"x" * (5 * 1024 + 1)  # 5 KiB + 1 byte
    fake_response = _mock_httpx_response(
        status_code=200,
        content=large_content,
    )

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=fake_response)

    with (
        _patch_dns("93.184.216.34"),
        patch("app.utils.safe_fetch.httpx.AsyncClient", return_value=mock_client),
        pytest.raises(UnsafeURLError) as exc_info,
    ):
        await safe_fetch("http://example.com/big", max_response_bytes=5 * 1024)
    assert exc_info.value.reason == "response_too_large"
