"""Topic+geography → subreddit list cache with lazy LLM-backed generation.

Public API:
    get_subreddits_for_topic(db, topic, geography) -> list[str]

Cache miss triggers one LLM call, persists the result, returns subreddits.
Generation failures return [] and never raise — soft-fail for Voices phase.

Per AGENTS.md hygiene: log only normalized_key and counts in warning paths.
Never log raw topic or picked subreddit names in warnings.
"""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.subreddit_selection_hint import SubredditSelectionHint
from app.llm.prompts.subreddit_selection import (
    PROMPT_NAME,
    SUBREDDIT_SELECTION_SYSTEM_PROMPT,
    build_subreddit_selection_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.subreddit_selection import SubredditSelectionDraft

_logger = get_logger(__name__)

_MAX_TOKENS = 800
_TEMPERATURE = 0.3

_SUBREDDIT_RE = re.compile(r"^[a-z0-9_]{2,50}$")


def _normalize_part(raw: str) -> str:
    """Normalize for cache lookup: lowercase, collapse whitespace, trim."""
    return " ".join(raw.lower().split()).strip()


def _normalize_key(topic: str, geography: str | None) -> str:
    return f"{_normalize_part(topic)}||{_normalize_part(geography or '')}"


def _sanitize_subreddit(name: str) -> str | None:
    s = name.strip().lower()
    for prefix in ("r/", "/r/", "www.reddit.com/r/", "https://www.reddit.com/r/", "http://www.reddit.com/r/"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    if "/" in s:
        s = s.split("/", 1)[0]
    if not _SUBREDDIT_RE.match(s):
        return None
    return s


async def _get_cached(db: AsyncSession, normalized_key: str) -> SubredditSelectionHint | None:
    result = await db.execute(
        select(SubredditSelectionHint).where(
            SubredditSelectionHint.normalized_key == normalized_key
        )
    )
    return result.scalar_one_or_none()


async def _generate_and_cache(
    db: AsyncSession,
    *,
    normalized_key: str,
    original_topic: str,
    original_geography: str | None,
    experiment_id: UUID | None,
) -> list[str]:
    """Call LLM to generate subreddits, persist result, return list.

    On any failure, logs a warning and returns []. Never raises.
    """
    settings = get_settings()

    try:
        draft, meta = await llm_client.complete_structured(
            db,
            provider=settings.voices_subreddit_provider,
            model=settings.voices_subreddit_model,
            prompt_name=PROMPT_NAME,
            system=SUBREDDIT_SELECTION_SYSTEM_PROMPT,
            user=build_subreddit_selection_user_prompt(
                original_topic[:300],
                original_geography,
            ),
            response_model=SubredditSelectionDraft,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            max_retries=2,
            experiment_id=experiment_id,
            phase="voices_subreddit_selection",
        )
    except Exception as exc:
        _logger.warning(
            "subreddit selection generation failed",
            normalized_key_length=len(normalized_key),
            error_type=type(exc).__name__,
        )
        return []

    seen: set[str] = set()
    sanitized: list[str] = []
    for raw_name in draft.subreddits:
        clean = _sanitize_subreddit(raw_name)
        if clean and clean not in seen:
            seen.add(clean)
            sanitized.append(clean)

    row = SubredditSelectionHint(
        normalized_key=normalized_key,
        original_topic=original_topic[:300],
        original_geography=(original_geography[:200] if original_geography else None),
        subreddits=sanitized,
        rationale=draft.rationale or None,
        model_used=f"{settings.voices_subreddit_provider}:{settings.voices_subreddit_model}",
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        existing = await _get_cached(db, normalized_key)
        if existing is not None:
            _logger.info(
                "subreddit selection race — using winner",
                normalized_key=normalized_key,
                subreddit_count=len(existing.subreddits),
            )
            return list(existing.subreddits)
        _logger.warning(
            "subreddit selection race — winner not found on re-read",
            normalized_key=normalized_key,
        )
        return []

    _logger.info(
        "subreddit selection generated and cached",
        normalized_key=normalized_key,
        subreddit_count=len(sanitized),
        rejected_count=len(draft.subreddits) - len(sanitized),
        cost_usd=str(meta.cost_usd),
        latency_ms=meta.latency_ms,
    )
    return sanitized


async def get_subreddits_for_topic(
    db: AsyncSession,
    *,
    topic: str,
    geography: str | None,
    experiment_id: UUID | None = None,
) -> list[str]:
    """Get up to 8 subreddits for a topic+geography, generating on cache miss.

    Never raises. Returns [] for empty/unusable inputs, cache misses that
    fail to generate, and generation errors.
    """
    if not topic or not topic.strip():
        return []

    normalized_topic = _normalize_part(topic)
    if len(normalized_topic) < 2 or len(normalized_topic) > 300:
        return []

    geo_norm = _normalize_part(geography) if geography and geography.strip() else ""
    if geo_norm and len(geo_norm) > 200:
        return []

    normalized_key = _normalize_key(topic, geography)

    cached = await _get_cached(db, normalized_key)
    if cached is not None:
        _logger.info(
            "subreddit selection cache hit",
            normalized_key=normalized_key,
            subreddit_count=len(cached.subreddits),
        )
        return list(cached.subreddits)

    return await _generate_and_cache(
        db,
        normalized_key=normalized_key,
        original_topic=topic,
        original_geography=geography,
        experiment_id=experiment_id,
    )
