"""Tests for app.utils.ip_address."""

from __future__ import annotations

from app.utils.ip_address import is_public_ip


def test_is_public_ip_accepts_routable_ipv4() -> None:
    assert is_public_ip("8.8.8.8") is True


def test_is_public_ip_rejects_private_and_loopback() -> None:
    assert is_public_ip("127.0.0.1") is False
    assert is_public_ip("10.0.0.5") is False
    assert is_public_ip("192.168.1.10") is False
    assert is_public_ip(None) is False
    assert is_public_ip("not-an-ip") is False
