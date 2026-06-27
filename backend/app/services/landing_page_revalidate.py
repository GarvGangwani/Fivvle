"""Best-effort ISR cache invalidation for published landing pages."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.landing_page import LandingPage
from app.logging_config import get_logger
from app.utils.experiment_naming import validate_landing_slug

_logger = get_logger(__name__)


def _normalize_slugs(slugs: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in slugs:
        if not raw:
            continue
        try:
            slug = validate_landing_slug(raw)
        except ValueError:
            _logger.warning(
                "landing_page_revalidate_invalid_slug",
                extra={"slug": raw},
            )
            continue
        if slug in seen:
            continue
        seen.add(slug)
        unique.append(slug)
    return unique


async def revalidate_published_landing_pages(slugs: Sequence[str]) -> datetime | None:
    """POST to the Next.js revalidate endpoint for each slug.

    Returns a UTC timestamp when at least one slug was invalidated successfully.
    Skips quietly when revalidate env vars are not configured (local dev fallback).
    """
    settings = get_settings()
    if not settings.frontend_revalidate_url or not settings.revalidate_secret:
        _logger.debug(
            "landing_page_revalidate_skipped",
            extra={"reason": "not_configured"},
        )
        return None

    targets = _normalize_slugs(slugs)
    if not targets:
        return None

    any_ok = False
    async with httpx.AsyncClient(timeout=10.0) as client:
        for slug in targets:
            try:
                response = await client.post(
                    settings.frontend_revalidate_url,
                    json={"slug": slug},
                    headers={"X-Revalidate-Secret": settings.revalidate_secret},
                )
                response.raise_for_status()
                any_ok = True
                _logger.info("landing_page_revalidate_ok", extra={"slug": slug})
            except httpx.HTTPError as exc:
                _logger.warning(
                    "landing_page_revalidate_failed",
                    extra={"slug": slug, "error": str(exc)},
                )

    return datetime.now(UTC) if any_ok else None


async def notify_live_landing_page_changed(
    db: AsyncSession,
    landing_page: LandingPage,
    *,
    previous_slug: str | None = None,
) -> None:
    """Invalidate ISR cache for the live page (and previous slug if renamed)."""
    slugs: list[str] = [landing_page.slug]
    if previous_slug and previous_slug != landing_page.slug:
        slugs.append(previous_slug)

    revalidated_at = await revalidate_published_landing_pages(slugs)
    if revalidated_at is None:
        return

    landing_page.last_revalidated_at = revalidated_at
    await db.commit()
    await db.refresh(landing_page)
