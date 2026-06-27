"""Public landing page URL helpers (subdomain routing)."""

from __future__ import annotations

from urllib.parse import urlencode

from app.config import get_settings
from app.utils.experiment_naming import validate_landing_slug

LANDING_PAGE_SOURCE_PARAM = "utm_source"


def format_public_landing_host(slug: str) -> str:
    """Hostname for display, e.g. mewwly.fivvle.io or mewwly.localhost:3000."""
    settings = get_settings()
    normalized = validate_landing_slug(slug)
    if settings.environment in {"development", "test"}:
        port = settings.landing_public_dev_port
        return f"{normalized}.localhost:{port}"
    root = settings.landing_public_root_domain
    return f"{normalized}.{root}"


def build_public_landing_page_url(
    slug: str,
    *,
    source_tag: str | None = None,
) -> str:
    """Full public URL for a published landing page."""
    settings = get_settings()
    normalized = validate_landing_slug(slug)
    if settings.environment in {"development", "test"}:
        port = settings.landing_public_dev_port
        base = f"http://{normalized}.localhost:{port}/"
    else:
        root = settings.landing_public_root_domain
        base = f"https://{normalized}.{root}/"

    if not source_tag:
        return base

    query = urlencode({LANDING_PAGE_SOURCE_PARAM: source_tag})
    return f"{base}?{query}"
