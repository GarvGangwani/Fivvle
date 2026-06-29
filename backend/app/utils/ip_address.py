"""Client IP helpers for telemetry and geolocation."""

from __future__ import annotations

import ipaddress


def is_public_ip(ip: str | None) -> bool:
    """Return True when *ip* is a routable public address suitable for geo lookup."""
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_unspecified
    )
