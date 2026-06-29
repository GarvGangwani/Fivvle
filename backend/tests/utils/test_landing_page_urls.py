"""Tests for public landing page URL helpers."""

from __future__ import annotations

import pytest

from app.utils.landing_page_urls import (
    build_public_landing_page_url,
    format_public_landing_host,
)


@pytest.mark.parametrize(
    ("slug", "expected_host"),
    [
        ("mewwly", "mewwly.localhost:3000"),
        ("origin-dry-co", "origin-dry-co.localhost:3000"),
    ],
)
def test_format_public_landing_host_dev(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    expected_host: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    from app.config import get_settings

    get_settings.cache_clear()
    assert format_public_landing_host(slug) == expected_host
    get_settings.cache_clear()


def test_build_public_landing_page_url_with_source_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    from app.config import get_settings

    get_settings.cache_clear()
    url = build_public_landing_page_url("mewwly", source_tag="twitter")
    assert url == "http://mewwly.localhost:3000/?utm_source=twitter"
    get_settings.cache_clear()
