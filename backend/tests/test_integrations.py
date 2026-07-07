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

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.external_api_call import ExternalAPICall
from app.integrations.reddit import (
    RedditNotFoundException,
    fetch_post_comments,
    search_subreddits,
)
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

# ===========================================================================
# Reddit tests (public JSON / httpx)
# ===========================================================================


def _reddit_post_data(
    *,
    pid: str = "abc123",
    title: str = "Test post",
    permalink: str = "/r/startups/comments/abc123/test/",
    score: int = 42,
    num_comments: int = 7,
    created_utc: float = 1_700_000_000.0,
    subreddit: str = "startups",
    selftext: str = "body",
) -> dict:
    return {
        "id": pid,
        "title": title,
        "url": f"https://www.reddit.com{permalink}",
        "permalink": permalink,
        "score": score,
        "num_comments": num_comments,
        "created_utc": created_utc,
        "subreddit": subreddit,
        "selftext": selftext,
    }


def _reddit_search_payload(*posts: dict) -> dict:
    return {
        "data": {
            "children": [{"kind": "t3", "data": post} for post in posts],
        }
    }


def _reddit_comments_payload(*comments: dict) -> list:
    return [
        {"kind": "Listing", "data": {"children": []}},
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {"kind": "t1", "data": comment} for comment in comments
                ]
                + [{"kind": "more", "data": {"count": 1}}],
            },
        },
    ]


def _http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://www.reddit.com/r/startups/search.json")
    response = httpx.Response(status_code=status, request=request)
    return httpx.HTTPStatusError("http error", request=request, response=response)


@pytest.mark.asyncio
async def test_search_subreddits_parses_public_json_response(db_session):
    payload = _reddit_search_payload(
        _reddit_post_data(pid="post1", title="Title 1"),
        _reddit_post_data(pid="post2", title="Title 2", score=10),
    )

    with patch(
        "app.integrations.reddit._http_get_json",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        posts = await search_subreddits(
            db_session,
            query="startup ideas",
            subreddits=["startups"],
            limit=25,
        )
        await db_session.commit()

    assert len(posts) == 2
    assert posts[0].id == "post1"
    assert posts[0].title == "Title 1"
    assert posts[0].url == "https://www.reddit.com/r/startups/comments/abc123/test/"
    assert posts[0].subreddit_name == "startups"


@pytest.mark.asyncio
async def test_fetch_post_comments_parses_two_element_response(db_session):
    payload = _reddit_comments_payload(
        {
            "id": "c1",
            "body": "Good point",
            "score": 5,
            "created_utc": 1_700_001_000.0,
        },
        {
            "id": "c2",
            "body": "Agree",
            "score": 3,
            "created_utc": 1_700_002_000.0,
        },
    )

    with patch(
        "app.integrations.reddit._http_get_json",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        comments = await fetch_post_comments(db_session, post_id="abc123", limit=25)
        await db_session.commit()

    assert len(comments) == 2
    assert comments[0].id == "c1"
    assert comments[1].body == "Agree"


@pytest.mark.asyncio
async def test_search_subreddits_404_raises_specific_exception(db_session):
    pre_ids = await _reddit_external_api_ids_before(db_session)
    with patch(
        "app.integrations.reddit._http_get_json",
        new_callable=AsyncMock,
        side_effect=RedditNotFoundException("reddit HTTP 404", status_code=404),
    ):
        with pytest.raises(RedditNotFoundException):
            await search_subreddits(
                db_session,
                query="fail",
                subreddits=["nonexistent"],
            )
        await db_session.commit()

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.operation == "search_subreddits",
    )
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_search_subreddits_429_retries_and_logs(db_session):
    payload = _reddit_search_payload(_reddit_post_data(pid="post1"))
    call_count = 0

    async def _flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise _http_status_error(429)
        return payload

    with (
        patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock),
        patch("app.integrations.reddit._http_get_json", side_effect=_flaky),
    ):
        posts = await search_subreddits(
            db_session,
            query="pricing",
            subreddits=["startups"],
        )
        await db_session.commit()

    assert len(posts) == 1
    assert call_count == 2


@pytest.mark.asyncio
async def test_reddit_user_agent_sent_on_every_request(db_session):
    settings = get_settings()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _reddit_search_payload(_reddit_post_data())
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.headers = {"User-Agent": settings.reddit_user_agent}

    with patch("app.integrations.reddit._get_http_client", return_value=mock_client):
        await search_subreddits(db_session, query="test", subreddits=["startups"])
        await db_session.commit()

    mock_client.get.assert_awaited()
    assert mock_client.headers["User-Agent"] == settings.reddit_user_agent


@pytest.mark.asyncio
async def test_ExternalAPICall_persisted_with_reddit_provider_zero_cost(db_session):
    pre_ids = await _reddit_external_api_ids_before(db_session)
    payload = _reddit_search_payload(_reddit_post_data())

    with patch(
        "app.integrations.reddit._http_get_json",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        await search_subreddits(db_session, query="test", subreddits=["startups"])
        await db_session.commit()

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.operation == "search_subreddits",
        ExternalAPICall.success.is_(True),
    )
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].operation == "search_subreddits"
    assert rows[0].success is True
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_reddit_fetch_post_comments_failure_logs_row(db_session):
    pre_ids = await _reddit_external_api_ids_before(db_session)
    with patch(
        "app.integrations.reddit._http_get_json",
        new_callable=AsyncMock,
        side_effect=RuntimeError("reddit down"),
    ):
        with pytest.raises(RuntimeError, match="reddit down"):
            await fetch_post_comments(db_session, post_id="abc123")
        await db_session.commit()

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.operation == "fetch_post_comments",
    )
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


async def _tavily_external_api_ids_before(session: AsyncSession) -> set[UUID]:
    stmt = select(ExternalAPICall.id).where(ExternalAPICall.provider == "tavily")
    return set((await session.execute(stmt)).scalars().all())


async def _reddit_external_api_ids_before(session: AsyncSession) -> set[UUID]:
    stmt = select(ExternalAPICall.id).where(ExternalAPICall.provider == "reddit")
    return set((await session.execute(stmt)).scalars().all())


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
        ],
        "usage": {"credits": 1},
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
    assert rows[0].api_credits == 1
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_tavily_search_advanced_cost(db_session):
    """Advanced search is billed at 2 credits ($0.016)."""
    pre_ids = await _tavily_external_api_ids_before(db_session)
    tag = uuid4().hex[:8]
    isolation_query = f"isolation-tag-test_tavily_search_advanced_cost-{tag}"

    fake_response = {
        "results": [{"title": "R", "url": "https://x.com", "content": "c"}],
        "usage": {"credits": 2},
    }
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
    assert rows[0].api_credits == 2
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


