"""Reddit read-only research integration wrapper.

EVERY Reddit call in Fivvle goes through this module.
Direct httpx or praw imports anywhere else are a violation of `.cursorrules`.

Transport: Reddit public JSON endpoints (no OAuth). Same data as the legacy
API; ~60 requests/minute per IP without auth.

The wrapper:
- Uses httpx.AsyncClient with User-Agent from settings.
- Logs one ExternalAPICall row per operation (success and failure).
- NEVER logs query text, post bodies, or comment text — only metadata.

# Reddit public JSON — ~60 requests/minute per IP. We do NOT enforce rate
# limiting in this module; rate limit handling lives at the research engine
# orchestrator level. On 429, httpx raises and retry_async backs off.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.cost.category import resolve_cost_category_from_external_provider
from app.db.models.external_api_call import ExternalAPICall
from app.db.session_lock import lock_for
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

_TIMEOUT_SECONDS = 15  # per .cursorrules reliability section
_REDDIT_BASE = "https://www.reddit.com"

# Lazy module-level HTTP client.
_http_client: httpx.AsyncClient | None = None


class RedditClientError(Exception):
    """Base for non-retryable Reddit HTTP client errors."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class RedditNotFoundException(RedditClientError):
    """Subreddit or resource not found (HTTP 404)."""


class RedditForbiddenException(RedditClientError):
    """Auth/forbidden response (HTTP 401/403)."""


class RedditServerException(RedditClientError):
    """Reddit server error (HTTP 5xx) — retryable via status_code on exc."""


def _get_http_client() -> httpx.AsyncClient:
    global _http_client  # noqa: PLW0603
    if _http_client is None:
        settings = get_settings()
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(_TIMEOUT_SECONDS),
            headers={"User-Agent": settings.reddit_user_agent},
            follow_redirects=True,
        )
    return _http_client


class RedditPost(BaseModel):
    """A Reddit submission (post)."""

    id: str
    title: str
    url: str
    score: int
    num_comments: int
    created_utc: float
    subreddit_name: str
    selftext: str = ""


class RedditComment(BaseModel):
    """A top-level comment on a Reddit post."""

    id: str
    body: str
    score: int
    created_utc: float


async def _log_api_call(
    db: AsyncSession,
    *,
    experiment_id: UUID | None,
    operation: str,
    latency_ms: int,
    success: bool,
) -> None:
    """Persist one row to external_api_calls. Does NOT commit."""
    call = ExternalAPICall(
        experiment_id=experiment_id,
        provider="reddit",
        cost_category=resolve_cost_category_from_external_provider("reddit").value,
        operation=operation,
        latency_ms=latency_ms,
        cost_usd=Decimal("0"),  # Reddit public JSON — always $0
        success=success,
    )
    async with lock_for(db):
        db.add(call)
        await db.flush()


def _raise_for_http_status(response: httpx.Response) -> None:
    status = response.status_code
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        _logger.warning(
            "reddit rate limited",
            status_code=status,
            retry_after=retry_after,
        )
        response.raise_for_status()
    if status in (401, 403):
        raise RedditForbiddenException(
            f"reddit HTTP {status}",
            status_code=status,
        )
    if status == 404:
        raise RedditNotFoundException(
            "reddit HTTP 404",
            status_code=status,
        )
    if 500 <= status <= 599:
        raise RedditServerException(
            f"reddit HTTP {status}",
            status_code=status,
        )
    if status >= 400:
        raise RedditClientError(
            f"reddit HTTP {status}",
            status_code=status,
        )


async def _http_get_json(url: str, *, params: dict[str, Any]) -> Any:
    client = _get_http_client()
    response = await client.get(url, params=params)
    _raise_for_http_status(response)
    return response.json()


def _parse_search_listing(payload: dict[str, Any]) -> list[RedditPost]:
    children = payload.get("data", {}).get("children", [])
    posts: list[RedditPost] = []
    for child in children:
        if child.get("kind") != "t3":
            continue
        post_data = child.get("data") or {}
        permalink = post_data.get("permalink") or ""
        full_url = (
            f"{_REDDIT_BASE}{permalink}"
            if permalink.startswith("/")
            else str(post_data.get("url") or "")
        )
        posts.append(
            RedditPost(
                id=str(post_data.get("id") or ""),
                title=str(post_data.get("title") or ""),
                url=full_url,
                score=int(post_data.get("score") or 0),
                num_comments=int(post_data.get("num_comments") or 0),
                created_utc=float(post_data.get("created_utc") or 0.0),
                subreddit_name=str(post_data.get("subreddit") or ""),
                selftext=str(post_data.get("selftext") or ""),
            )
        )
    return posts


def _parse_comments_listing(payload: list[Any], *, limit: int) -> list[RedditComment]:
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    comment_listing = payload[1]
    if not isinstance(comment_listing, dict):
        return []
    children = comment_listing.get("data", {}).get("children", [])
    comments: list[RedditComment] = []
    for child in children:
        if child.get("kind") == "more":
            continue
        if child.get("kind") != "t1":
            continue
        comment_data = child.get("data") or {}
        comments.append(
            RedditComment(
                id=str(comment_data.get("id") or ""),
                body=str(comment_data.get("body") or ""),
                score=int(comment_data.get("score") or 0),
                created_utc=float(comment_data.get("created_utc") or 0.0),
            )
        )
        if len(comments) >= limit:
            break
    return comments


async def _search_subreddits_http(
    query: str,
    subreddits: list[str],
    limit: int,
) -> list[RedditPost]:
    per_request = min(limit, 25)
    by_id: dict[str, RedditPost] = {}
    for subreddit in subreddits:
        url = f"{_REDDIT_BASE}/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "true",
            "sort": "relevance",
            "limit": str(per_request),
            "raw_json": "1",
        }
        payload = await _http_get_json(url, params=params)
        if not isinstance(payload, dict):
            continue
        for post in _parse_search_listing(payload):
            if post.id:
                by_id[post.id] = post
    ordered = sorted(by_id.values(), key=lambda p: p.score, reverse=True)
    return ordered[:limit]


async def _fetch_post_comments_http(post_id: str, limit: int) -> list[RedditComment]:
    url = f"{_REDDIT_BASE}/comments/{post_id}.json"
    params = {
        "limit": str(min(limit, 25)),
        "sort": "top",
        "raw_json": "1",
    }
    payload = await _http_get_json(url, params=params)
    return _parse_comments_listing(payload, limit=limit)


async def search_subreddits(
    db: AsyncSession,
    *,
    query: str,
    subreddits: list[str],
    limit: int = 25,
    experiment_id: UUID | None = None,
) -> list[RedditPost]:
    """Search within one or more subreddits for posts matching the query.

    Read-only — does NOT post, comment, vote, or modify anything.
    Cost: $0.

    Args:
        db: caller's session. One ExternalAPICall row is written here.
        query: search query string.
        subreddits: list like ["startups", "Entrepreneur"].
        limit: max posts returned across all subreddits.
        experiment_id: optional FK for cost rollup.

    Returns RedditPost list sorted by score descending.

    Raises RedditClientError subclasses or httpx errors on failure — after
    logging a failure row.
    """
    started_at = time.perf_counter()

    try:

        @retry_async()
        async def _call_reddit_search_with_retry() -> list[RedditPost]:
            async def _do_reddit_search() -> list[RedditPost]:
                return await _search_subreddits_http(query, subreddits, limit)

            return await get_breaker("reddit").call(_do_reddit_search)

        posts = await _call_reddit_search_with_retry()
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        await _log_api_call(
            db,
            experiment_id=experiment_id,
            operation="search_subreddits",
            latency_ms=latency_ms,
            success=True,
        )

        _logger.info(
            "reddit search_subreddits completed",
            num_posts=len(posts),
            num_subreddits=len(subreddits),
            latency_ms=latency_ms,
        )

        return posts

    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="search_subreddits",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed reddit call", error=str(log_exc))

        _logger.warning(
            "reddit search_subreddits failed",
            error_type=type(exc).__name__,
            status_code=getattr(exc, "status_code", None),
        )
        raise


async def fetch_post_comments(
    db: AsyncSession,
    *,
    post_id: str,
    limit: int = 25,
    experiment_id: UUID | None = None,
) -> list[RedditComment]:
    """Fetch top N comments for a Reddit post.

    Read-only — does NOT post, comment, vote, or modify anything.
    Cost: $0.

    Args:
        db: caller's session. One ExternalAPICall row is written here.
        post_id: Reddit post ID (e.g. "abc123").
        limit: max number of top-level comments to return.
        experiment_id: optional FK for cost rollup.

    Returns list of RedditComment sorted by top score.

    Raises RedditClientError subclasses or httpx errors on failure — after
    logging a failure row.
    """
    started_at = time.perf_counter()

    try:

        @retry_async()
        async def _call_reddit_comments_with_retry() -> list[RedditComment]:
            async def _do_reddit_comments() -> list[RedditComment]:
                return await _fetch_post_comments_http(post_id, limit)

            return await get_breaker("reddit").call(_do_reddit_comments)

        comments = await _call_reddit_comments_with_retry()
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        await _log_api_call(
            db,
            experiment_id=experiment_id,
            operation="fetch_post_comments",
            latency_ms=latency_ms,
            success=True,
        )

        _logger.info(
            "reddit fetch_post_comments completed",
            num_comments=len(comments),
            latency_ms=latency_ms,
        )

        return comments

    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="fetch_post_comments",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed reddit call", error=str(log_exc))

        _logger.warning(
            "reddit fetch_post_comments failed",
            error_type=type(exc).__name__,
            status_code=getattr(exc, "status_code", None),
        )
        raise
