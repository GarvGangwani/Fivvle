"""SSRF-safe URL fetcher.

Per AGENTS.md "SSRF prevention (URL fetching)", every fetch of a URL derived
from external/LLM/scraped input MUST go through ``safe_fetch``.

What is guarded:
  1. Scheme allowlist — only http and https.
  2. Hostname presence check.
  3. DNS resolution via socket.getaddrinfo (run in a thread — never block the
     event loop).  ALL resolved A/AAAA records are checked; if ANY maps to a
     private/internal range the request is rejected.  We can't predict which
     IP the OS or httpx will ultimately dial, so the only safe policy is all-or-
     nothing.
  4. Redirect following — manual, so each redirect target is validated before
     the next request is made.  Auto-redirect is disabled on the httpx client.
  5. Redirect depth cap — raises UnsafeURLError("redirect_loop") after 5 hops.
  6. Response size cap — raises UnsafeURLError("response_too_large") if the
     body exceeds *max_response_bytes* (default 10 MiB).

What is NOT guarded here:
  - Calls to known, hardcoded provider endpoints (Anthropic, Groq, Tavily,
    Reddit, Google Trends).  Those SDK calls do not route through safe_fetch
    because their destination is code-controlled, not data-controlled.

IP range coverage via ipaddress module properties:
  - ip.is_loopback   → 127.0.0.0/8 (IPv4)  and ::1/128 (IPv6)
  - ip.is_private    → 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (IPv4)
                       and fc00::/7 ULA (IPv6)
  - ip.is_link_local → 169.254.0.0/16 (IPv4, e.g. AWS/GCP metadata endpoint
                       169.254.169.254)  and fe80::/10 (IPv6)
  - ip.is_reserved   → 0.0.0.0/8 and IANA special-purpose ranges
  - ip.is_unspecified → 0.0.0.0 (IPv4) and :: (IPv6)
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from app.logging_config import get_logger

_logger = get_logger(__name__)

_MAX_REDIRECT_DEPTH = 5


class UnsafeURLError(Exception):
    """Raised when a URL fails a safety check.

    Attributes:
        reason: Short machine-readable tag for the failure kind.
            One of: ``"scheme"``, ``"empty_hostname"``, ``"dns_failure"``,
            ``"dns_no_results"``, ``"private_ip"``, ``"redirect_loop"``,
            ``"response_too_large"``.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"Unsafe URL ({reason})")
        self.reason = reason


def _is_private_ip(addr: str) -> bool:
    """Return True if *addr* is a private, loopback, link-local, reserved, or
    unspecified IP address.

    ipaddress property coverage (see module docstring for ranges):
      - is_loopback   → 127.x.x.x / ::1
      - is_private    → RFC-1918 + ULA
      - is_link_local → 169.254.x.x / fe80::/10
      - is_reserved   → 0.0.0.0/8 and other IANA specials
      - is_unspecified → 0.0.0.0 / ::
    """
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        # Unparseable — treat as unsafe.
        return True

    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
    )


async def safe_fetch(
    url: str,
    *,
    timeout: float = 30.0,
    max_response_bytes: int = 10 * 1024 * 1024,
    _redirect_depth: int = _MAX_REDIRECT_DEPTH,
) -> httpx.Response:
    """Fetch *url* with full SSRF protection.

    Args:
        url: The URL to fetch.  Must use http or https scheme.
        timeout: Per-request timeout in seconds (connect + read).
        max_response_bytes: Maximum response body size accepted.  If the server
            sends more, ``UnsafeURLError("response_too_large")`` is raised.
        _redirect_depth: Internal counter tracking how many redirect hops
            remain.  Do NOT pass this from call sites outside this module.

    Returns:
        An ``httpx.Response`` with ``.content`` fully populated.

    Raises:
        UnsafeURLError: URL fails any safety check (see ``reason`` attribute).
        httpx.HTTPError: Network-level errors propagate unchanged so callers
            can distinguish transport failures from safety rejections.
    """
    if _redirect_depth <= 0:
        raise UnsafeURLError("redirect_loop")

    # --- 1. Scheme check ---------------------------------------------------
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("scheme")

    # --- 2. Hostname presence ----------------------------------------------
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("empty_hostname")

    # --- 3. DNS resolution + private-IP check ------------------------------
    # getaddrinfo is a blocking stdlib call; run it in a thread so we never
    # stall the event loop.  We request SOCK_STREAM to match typical HTTP
    # connection behaviour and avoid duplicate address-family entries.
    def _resolve() -> list[tuple]:  # type: ignore[type-arg]
        return socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)

    try:
        addr_infos = await asyncio.to_thread(_resolve)
    except socket.gaierror as exc:
        raise UnsafeURLError("dns_failure") from exc

    if not addr_infos:
        raise UnsafeURLError("dns_no_results")

    for addr_info in addr_infos:
        # addr_info is (family, type, proto, canonname, sockaddr)
        # sockaddr is (address, port) for IPv4 or (address, port, flow, scope) for IPv6
        ip_str = addr_info[4][0]
        if _is_private_ip(ip_str):
            _logger.warning(
                "safe_fetch: private IP rejected",
                hostname=hostname,
                ip=ip_str,
            )
            raise UnsafeURLError("private_ip")

    # --- 4. HTTP request (no auto-redirect) --------------------------------
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=False,
    ) as client:
        response = await client.get(url)

    # --- 5. Manual redirect validation -------------------------------------
    if response.is_redirect:
        location = response.headers.get("location", "").strip()
        if location:
            return await safe_fetch(
                location,
                timeout=timeout,
                max_response_bytes=max_response_bytes,
                _redirect_depth=_redirect_depth - 1,
            )

    # --- 6. Response size cap ----------------------------------------------
    # Fast-path: trust Content-Length if provided to avoid reading a huge body.
    cl_header = response.headers.get("content-length", "")
    if cl_header:
        try:
            if int(cl_header) > max_response_bytes:
                raise UnsafeURLError("response_too_large")
        except ValueError:
            pass  # Malformed Content-Length — fall through to actual size check.

    # Ensure .content is populated (httpx.get already reads the full body, but
    # calling aread() is a safe no-op if content is already loaded).
    await response.aread()

    if len(response.content) > max_response_bytes:
        raise UnsafeURLError("response_too_large")

    return response
