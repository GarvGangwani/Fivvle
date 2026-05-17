"""Tests for app.integrations.* wrappers.

All SDK/network calls are mocked. We test WRAPPER behavior:
- One ExternalAPICall row is written per operation (success and failure).
- Success row: correct provider/operation/cost, success=True.
- Failure row: success=False, cost=0, exception re-raised.
- Pydantic result models parse correctly from mocked SDK responses.

Uses the same standalone-engine fixture as test_llm_client.py to avoid the
disposed-engine issue caused by TestClient lifespan teardown.
"""

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.external_api_call import ExternalAPICall
from app.integrations.google_trends import TrendsResult, get_interest_over_time
from app.integrations.reddit import RedditComment, RedditPost, fetch_post_comments, search_subreddits
from app.integrations.tavily import TavilyResult, search


# ---------------------------------------------------------------------------
# Standalone DB session fixture — avoids disposed-engine ordering problem
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh async session per test; independent of FastAPI lifespan."""
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_praw_submission(
    *,
    sid: str = "abc123",
    title: str = "Test post",
    url: str = "https://reddit.com/r/test/abc123",
    score: int = 42,
    num_comments: int = 7,
    created_utc: float = 1_700_000_000.0,
    display_name: str = "startups",
    selftext: str = "",
) -> MagicMock:
    sub = MagicMock()
    sub.id = sid
    sub.title = title
    sub.url = url
    sub.score = score
    sub.num_comments = num_comments
    sub.created_utc = created_utc
    sub.subreddit.display_name = display_name
    sub.selftext = selftext
    return sub


def _make_praw_comment(
    *,
    cid: str = "c1",
    body: str = "Great idea!",
    score: int = 15,
    created_utc: float = 1_700_001_000.0,
) -> MagicMock:
    comment = MagicMock()
    comment.id = cid
    comment.body = body
    comment.score = score
    comment.created_utc = created_utc
    return comment


async def _tavily_external_api_ids_before(session: AsyncSession) -> set[UUID]:
    stmt = select(ExternalAPICall.id).where(ExternalAPICall.provider == "tavily")
    return set((await session.execute(stmt)).scalars().all())


def _make_trends_df(keywords: list[str]) -> pd.DataFrame:
    """Create a minimal pytrends-style DataFrame for two dates."""
    import datetime

    dates = pd.to_datetime(["2025-01-01", "2025-01-08"])
    data = {kw: [50, 75] for kw in keywords}
    data["isPartial"] = [False, False]
    return pd.DataFrame(data, index=dates)


# ===========================================================================
# Tavily tests
# ===========================================================================


@pytest.mark.asyncio
async def test_tavily_search_success_logs_row(db_session):
    """Successful Tavily search writes one ExternalAPICall row with correct cost."""
    pre_ids = await _tavily_external_api_ids_before(db_session)
    tag = uuid4().hex[:8]
    isolation_query = f"isolation-tag-test_tavily_search_success_logs_row-{tag}"

    fake_response = {
        "results": [
            {"title": "Result 1", "url": "https://example.com/1", "content": "snippet 1", "score": 0.9},
            {"title": "Result 2", "url": "https://example.com/2", "content": "snippet 2", "score": 0.8},
        ]
    }

    fake_client = MagicMock()
    fake_client.search = MagicMock(return_value=fake_response)

    with patch("app.integrations.tavily._client", fake_client):
        results = await search(
            db_session,
            query=isolation_query,
            max_results=2,
            search_depth="basic",
        )
        await db_session.commit()

    assert len(results) == 2
    assert all(isinstance(r, TavilyResult) for r in results)
    assert results[0].title == "Result 1"
    assert results[0].url == "https://example.com/1"
    assert results[0].score == 0.9

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "tavily")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].operation == "search"
    assert rows[0].success is True
    assert rows[0].cost_usd == Decimal("0.008")  # basic = 1 credit
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tavily_search_advanced_cost(db_session):
    """Advanced search is billed at 2 credits ($0.016)."""
    pre_ids = await _tavily_external_api_ids_before(db_session)
    tag = uuid4().hex[:8]
    isolation_query = f"isolation-tag-test_tavily_search_advanced_cost-{tag}"

    fake_response = {"results": [{"title": "R", "url": "https://x.com", "content": "c"}]}
    fake_client = MagicMock()
    fake_client.search = MagicMock(return_value=fake_response)

    with patch("app.integrations.tavily._client", fake_client):
        await search(db_session, query=isolation_query, search_depth="advanced")
        await db_session.commit()

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "tavily")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd == Decimal("0.016")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tavily_search_failure_logs_zero_cost_row(db_session):
    """When Tavily SDK raises, logs a zero-cost failure row and re-raises."""
    pre_ids = await _tavily_external_api_ids_before(db_session)
    tag = uuid4().hex[:8]
    isolation_query = f"isolation-tag-test_tavily_search_failure_logs_zero_cost_row-{tag}"

    fake_client = MagicMock()
    fake_client.search = MagicMock(side_effect=Exception("network error"))

    with patch("app.integrations.tavily._client", fake_client):
        with pytest.raises(Exception, match="network error"):
            await search(db_session, query=isolation_query)
        await db_session.commit()

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "tavily")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ===========================================================================
# Reddit tests
# ===========================================================================


@pytest.mark.asyncio
async def test_reddit_search_subreddits_success(db_session):
    """Successful Reddit search writes one ExternalAPICall row with $0 cost."""
    fake_submissions = [
        _make_praw_submission(sid="post1", title="Title 1"),
        _make_praw_submission(sid="post2", title="Title 2"),
    ]

    fake_subreddit = MagicMock()
    fake_subreddit.search = MagicMock(return_value=iter(fake_submissions))

    fake_reddit = MagicMock()
    fake_reddit.subreddit = MagicMock(return_value=fake_subreddit)

    with patch("app.integrations.reddit._reddit", fake_reddit):
        posts = await search_subreddits(
            db_session,
            query="startup ideas",
            subreddits=["startups", "Entrepreneur"],
        )
        await db_session.commit()

    assert len(posts) == 2
    assert all(isinstance(p, RedditPost) for p in posts)
    assert posts[0].id == "post1"
    assert posts[0].title == "Title 1"

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "reddit")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].operation == "search_subreddits"
    assert rows[0].success is True
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_reddit_search_subreddits_failure_logs_row(db_session):
    """When PRAW raises, logs a failure row and re-raises."""
    fake_reddit = MagicMock()
    fake_reddit.subreddit = MagicMock(side_effect=Exception("praw error"))

    with patch("app.integrations.reddit._reddit", fake_reddit):
        with pytest.raises(Exception, match="praw error"):
            await search_subreddits(
                db_session,
                query="fail",
                subreddits=["startups"],
            )
        await db_session.commit()

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "reddit")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_reddit_fetch_post_comments_success(db_session):
    """Successful comment fetch writes one ExternalAPICall row."""
    fake_comments = [
        _make_praw_comment(cid="c1", body="Good point"),
        _make_praw_comment(cid="c2", body="Agree"),
    ]

    fake_submission = MagicMock()
    fake_submission.comments.replace_more = MagicMock()
    fake_submission.comments.list = MagicMock(return_value=fake_comments)

    fake_reddit = MagicMock()
    fake_reddit.submission = MagicMock(return_value=fake_submission)

    with patch("app.integrations.reddit._reddit", fake_reddit):
        comments = await fetch_post_comments(db_session, post_id="abc123", limit=25)
        await db_session.commit()

    assert len(comments) == 2
    assert all(isinstance(c, RedditComment) for c in comments)
    assert comments[0].id == "c1"

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.operation == "fetch_post_comments",
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is True
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_reddit_fetch_post_comments_failure_logs_row(db_session):
    """When PRAW raises during comment fetch, logs failure and re-raises."""
    fake_reddit = MagicMock()
    fake_reddit.submission = MagicMock(side_effect=Exception("reddit down"))

    with patch("app.integrations.reddit._reddit", fake_reddit):
        with pytest.raises(Exception, match="reddit down"):
            await fetch_post_comments(db_session, post_id="abc123")
        await db_session.commit()

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.operation == "fetch_post_comments",
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ===========================================================================
# Google Trends tests
# ===========================================================================


@pytest.mark.asyncio
async def test_trends_success_logs_row(db_session):
    """Successful Trends call writes one ExternalAPICall row with $0 cost."""
    keywords = ["startup", "MVP"]
    fake_df = _make_trends_df(keywords)

    fake_pytrends = MagicMock()
    fake_pytrends.build_payload = MagicMock()
    fake_pytrends.interest_over_time = MagicMock(return_value=fake_df)

    with patch("app.integrations.google_trends._pytrends", fake_pytrends):
        result = await get_interest_over_time(
            db_session,
            keywords=keywords,
            timeframe="today 12-m",
        )
        await db_session.commit()

    assert isinstance(result, TrendsResult)
    assert result.keywords == keywords
    assert len(result.data_points) == 2
    assert result.data_points[0].values["startup"] == 50
    assert result.data_points[1].values["MVP"] == 75

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "google_trends")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].operation == "get_interest_over_time"
    assert rows[0].success is True
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_trends_failure_logs_row(db_session):
    """When pytrends raises TooManyRequestsError, logs failure and re-raises."""
    from pytrends.exceptions import TooManyRequestsError

    fake_pytrends = MagicMock()
    fake_pytrends.build_payload = MagicMock()
    # TooManyRequestsError(message, response) — response can be any mock
    fake_pytrends.interest_over_time = MagicMock(
        side_effect=TooManyRequestsError("rate limited", MagicMock())
    )

    with patch("app.integrations.google_trends._pytrends", fake_pytrends):
        with pytest.raises(TooManyRequestsError):
            await get_interest_over_time(db_session, keywords=["startup"])
        await db_session.commit()

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "google_trends")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_trends_too_many_keywords_raises_before_logging(db_session):
    """Providing >5 keywords raises ValueError immediately, no ExternalAPICall row."""
    with pytest.raises(ValueError, match="at most 5"):
        await get_interest_over_time(
            db_session,
            keywords=["a", "b", "c", "d", "e", "f"],
        )

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "google_trends")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 0
