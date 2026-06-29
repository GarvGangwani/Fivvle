"""Reddit read-only research integration wrapper.

EVERY Reddit call in Fivvle goes through this module.
Direct praw imports anywhere else are a violation of `.cursorrules`.

The wrapper:
- Uses PRAW in script/read-only mode (no OAuth flow, no posting).
- Runs the sync PRAW SDK in asyncio.to_thread so the event loop is unblocked.
- Logs one ExternalAPICall row per operation (success and failure).
- NEVER logs query text, post bodies, or comment text — only metadata.

# Reddit free tier — 60 requests/minute. We do NOT enforce rate limiting in
# this module; rate limit handling lives at the research engine orchestrator
# level (build step 8-9). If we hit 429, PRAW will raise and we log a failure.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import praw
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

# Lazy module-level client. Built on first call.
_reddit: praw.Reddit | None = None


def _get_client() -> praw.Reddit:
    global _reddit  # noqa: PLW0603
    if _reddit is None:
        settings = get_settings()
        _reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
            ratelimit_seconds=_TIMEOUT_SECONDS,
            requestor_kwargs={"timeout": _TIMEOUT_SECONDS},
        )
        _reddit.read_only = True
    return _reddit


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
        cost_usd=Decimal("0"),  # Reddit free tier — always $0
        success=success,
    )
    async with lock_for(db):
        db.add(call)
        await db.flush()


def _fetch_subreddit_posts(
    query: str,
    subreddits: list[str],
    limit: int,
) -> list[RedditPost]:
    """Synchronous PRAW call — run via asyncio.to_thread."""
    reddit = _get_client()
    subreddit_str = "+".join(subreddits)
    sub = reddit.subreddit(subreddit_str)
    posts = []
    for submission in sub.search(query, limit=limit, sort="relevance"):
        posts.append(
            RedditPost(
                id=submission.id,
                title=submission.title,
                url=submission.url,
                score=submission.score,
                num_comments=submission.num_comments,
                created_utc=submission.created_utc,
                subreddit_name=submission.subreddit.display_name,
                selftext=submission.selftext or "",
            )
        )
    return posts


def _fetch_comments(post_id: str, limit: int) -> list[RedditComment]:
    """Synchronous PRAW call — run via asyncio.to_thread."""
    reddit = _get_client()
    submission = reddit.submission(id=post_id)
    submission.comment_sort = "top"
    submission.comments.replace_more(limit=0)  # skip MoreComments objects
    comments = []
    for comment in submission.comments.list()[:limit]:
        if not hasattr(comment, "body"):
            continue
        comments.append(
            RedditComment(
                id=comment.id,
                body=comment.body,
                score=comment.score,
                created_utc=comment.created_utc,
            )
        )
    return comments


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
    Cost: $0 (free tier).

    Args:
        db: caller's session. One ExternalAPICall row is written here.
        query: search query string.
        subreddits: list like ["startups", "Entrepreneur"]. Joined with "+".
        limit: per-subreddit result cap.
        experiment_id: optional FK for cost rollup.

    Returns RedditPost list sorted by relevance.

    Raises praw exceptions on network/auth failure — after logging a failure row.
    """
    started_at = time.perf_counter()

    try:
        async def _do_reddit_search():
            return await asyncio.wait_for(
                asyncio.to_thread(_fetch_subreddit_posts, query, subreddits, limit),
                timeout=_TIMEOUT_SECONDS,
            )

        @retry_async()
        async def _call_reddit_search_with_retry():
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

        # Log only metadata — NEVER query text, post bodies, or subreddit names.
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
    Cost: $0 (free tier).

    Args:
        db: caller's session. One ExternalAPICall row is written here.
        post_id: Reddit post ID (e.g. "abc123").
        limit: max number of top-level comments to return.
        experiment_id: optional FK for cost rollup.

    Returns list of RedditComment sorted by top score.

    Raises praw exceptions on network/auth failure — after logging a failure row.
    """
    started_at = time.perf_counter()

    try:
        async def _do_reddit_comments():
            return await asyncio.wait_for(
                asyncio.to_thread(_fetch_comments, post_id, limit),
                timeout=_TIMEOUT_SECONDS,
            )

        @retry_async()
        async def _call_reddit_comments_with_retry():
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

        # Log only metadata — NEVER log post_id or comment bodies.
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
        )
        raise
