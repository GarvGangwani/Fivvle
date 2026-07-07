"""Geography → include_domains cache with lazy LLM-backed generation.

Public API:
    get_include_domains_for_geography(db, raw_geography) -> list[str]

Cache miss triggers one LLM call, persists the result, returns the domains.
Generation failures return [] and never raise — this is a soft-quality signal.

Per AGENTS.md hygiene: log only presence/length in warning paths, and only the
normalized key (not the raw string) in info paths for cache-hit debugging.
"""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.geography_source_hint import GeographySourceHint
from app.llm.prompts.geography_hint import (
    GEOGRAPHY_HINT_SYSTEM_PROMPT,
    PROMPT_NAME,
    build_geography_hint_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.geography_hint import GeographyHintDraft

_logger = get_logger(__name__)

_MAX_TOKENS = 800
_TEMPERATURE = 0.3

_DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$"
)


def _normalize_geography(raw: str) -> str:
    """Normalize for cache lookup: lowercase, collapse whitespace, trim."""
    return " ".join(raw.lower().split()).strip()


def _sanitize_domain(d: str) -> str | None:
    """Return sanitized domain or None if invalid."""
    d = d.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if d.startswith(prefix):
            d = d[len(prefix) :]
    for sep in ("/", "?", "#"):
        if sep in d:
            d = d.split(sep, 1)[0]
    if not _DOMAIN_RE.match(d):
        return None
    if len(d) > 100:
        return None
    return d


async def _get_cached(db: AsyncSession, normalized_key: str) -> GeographySourceHint | None:
    result = await db.execute(
        select(GeographySourceHint).where(
            GeographySourceHint.normalized_key == normalized_key
        )
    )
    return result.scalar_one_or_none()


async def _generate_and_cache(
    db: AsyncSession,
    *,
    normalized_key: str,
    original_geography: str,
    experiment_id: UUID | None,
) -> list[str]:
    """Call LLM to generate hints, persist result, return domain list.

    On any failure, logs a warning and returns []. Never raises.
    """
    settings = get_settings()

    try:
        draft, meta = await llm_client.complete_structured(
            db,
            provider=settings.searcher_hints_provider,
            model=settings.searcher_hints_model,
            prompt_name=PROMPT_NAME,
            system=GEOGRAPHY_HINT_SYSTEM_PROMPT,
            user=build_geography_hint_user_prompt(normalized_key),
            response_model=GeographyHintDraft,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            max_retries=2,
            experiment_id=experiment_id,
            phase="geography_hint",
        )
    except Exception as exc:
        _logger.warning(
            "geography hint generation failed",
            normalized_key_length=len(normalized_key),
            error_type=type(exc).__name__,
        )
        return []

    seen: set[str] = set()
    sanitized: list[str] = []
    for raw_domain in draft.include_domains:
        clean = _sanitize_domain(raw_domain)
        if clean and clean not in seen:
            seen.add(clean)
            sanitized.append(clean)

    row = GeographySourceHint(
        normalized_key=normalized_key,
        original_geography=original_geography[:200],
        include_domains=sanitized,
        rationale=draft.rationale or None,
        model_used=f"{settings.searcher_hints_provider}:{settings.searcher_hints_model}",
    )
    # Wrap the insert in a SAVEPOINT so IntegrityError rolls back ONLY the
    # insert attempt, not the caller's outer transaction.
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        existing = await _get_cached(db, normalized_key)
        if existing is not None:
            _logger.info(
                "geography hint race — using winner",
                normalized_key=normalized_key,
                domain_count=len(existing.include_domains),
            )
            return list(existing.include_domains)
        _logger.warning(
            "geography hint race — winner not found on re-read",
            normalized_key=normalized_key,
        )
        return []

    _logger.info(
        "geography hint generated and cached",
        normalized_key=normalized_key,
        domain_count=len(sanitized),
        rejected_count=len(draft.include_domains) - len(sanitized),
        cost_usd=str(meta.cost_usd),
        latency_ms=meta.latency_ms,
    )
    return sanitized


async def get_include_domains_for_geography(
    db: AsyncSession,
    raw_geography: str,
    experiment_id: UUID | None = None,
) -> list[str]:
    """Get Tavily include_domains for a geography, generating on cache miss.

    Never raises. Returns [] for empty/unusable inputs, cache misses that fail
    to generate, and generation errors.
    """
    if not raw_geography or not raw_geography.strip():
        return []

    normalized = _normalize_geography(raw_geography)
    if len(normalized) < 2 or len(normalized) > 200:
        return []

    cached = await _get_cached(db, normalized)
    if cached is not None:
        _logger.info(
            "geography hint cache hit",
            normalized_key=normalized,
            domain_count=len(cached.include_domains),
        )
        return list(cached.include_domains)

    return await _generate_and_cache(
        db,
        normalized_key=normalized,
        original_geography=raw_geography,
        experiment_id=experiment_id,
    )
