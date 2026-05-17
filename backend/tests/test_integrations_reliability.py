"""Reliability tests for app.integrations.* (circuit breakers + retry).

Verifies the NEW circuit-breaker/retry wiring added in step 5B:
- CircuitOpenError from an open breaker still writes an ExternalAPICall failure row.
- Retried-then-successful calls write exactly ONE ExternalAPICall row.

Existing test_integrations.py tests are NOT modified and must continue to pass.
DB fixture pattern is identical to test_integrations.py.
"""

from __future__ import annotations

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
from app.integrations.reddit import search_subreddits
from app.integrations.tavily import search
from app.reliability.circuit_breakers import CircuitBreaker, CircuitOpenError, _breakers

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_breakers():
    _breakers.clear()
    yield
    _breakers.clear()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _raise_connect_error():
    raise httpx.ConnectError("test error")


async def _tavily_external_api_ids_before(session: AsyncSession) -> set[UUID]:
    stmt = select(ExternalAPICall.id).where(ExternalAPICall.provider == "tavily")
    return set((await session.execute(stmt)).scalars().all())


def _open_breaker(name: str) -> CircuitBreaker:
    """Create a breaker with threshold=1, cooldown=9999, then fail it once → OPEN."""
    import asyncio

    breaker = CircuitBreaker(name=name, failure_threshold=1, cooldown_seconds=9999)
    _breakers[name] = breaker

    async def _open():
        with pytest.raises(httpx.ConnectError):
            await breaker.call(_raise_connect_error)

    asyncio.get_event_loop().run_until_complete(_open())
    return breaker


# ---------------------------------------------------------------------------
# Tavily — open breaker logs failure row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_open_breaker_logs_failure_row(db_session):
    """When Tavily breaker is OPEN, search() raises CircuitOpenError AND writes
    a zero-cost ExternalAPICall failure row."""
    pre_ids = await _tavily_external_api_ids_before(db_session)
    tag = uuid4().hex[:8]
    isolation_query = f"isolation-tag-test_tavily_open_breaker_logs_failure_row-{tag}"

    breaker = CircuitBreaker(name="tavily", failure_threshold=1, cooldown_seconds=9999)
    _breakers["tavily"] = breaker
    with pytest.raises(httpx.ConnectError):
        await breaker.call(_raise_connect_error)

    assert breaker._state.value == "open"

    fake_client = MagicMock()
    fake_client.search = MagicMock(return_value={"results": []})

    with patch("app.integrations.tavily._client", fake_client):
        with pytest.raises(CircuitOpenError):
            await search(db_session, query=isolation_query)
        await db_session.commit()

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "tavily",
        ExternalAPICall.success.is_(False),
    )
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()

    fake_client.search.assert_not_called()


# ---------------------------------------------------------------------------
# Tavily — retry + eventual success writes exactly one row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_retry_then_success_writes_one_row(db_session):
    """2 transient failures then success → ONE ExternalAPICall row."""
    pre_ids = await _tavily_external_api_ids_before(db_session)
    tag = uuid4().hex[:8]
    isolation_query = f"isolation-tag-test_tavily_retry_then_success_writes_one_row-{tag}"

    call_count = 0
    fake_response = {"results": [{"title": "T", "url": "https://ex.com", "content": "c"}]}

    def _flaky_search(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Updated for Bug B: allow-list classifier requires an explicit transient exception type.
            raise httpx.ConnectError("connection refused by remote host")
        return fake_response

    fake_client = MagicMock()
    fake_client.search = MagicMock(side_effect=_flaky_search)

    with (
        patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock),
        patch("app.integrations.tavily._client", fake_client),
    ):
        results = await search(db_session, query=isolation_query)
        await db_session.commit()

    assert len(results) == 1
    assert call_count == 3

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "tavily",
        ExternalAPICall.success.is_(True),
    )
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1  # only one row — the successful call
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ---------------------------------------------------------------------------
# Reddit — open breaker logs failure row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reddit_open_breaker_logs_failure_row(db_session):
    breaker = CircuitBreaker(name="reddit", failure_threshold=1, cooldown_seconds=9999)
    _breakers["reddit"] = breaker
    with pytest.raises(httpx.ConnectError):
        await breaker.call(_raise_connect_error)

    assert breaker._state.value == "open"

    fake_reddit = MagicMock()
    fake_reddit.subreddit = MagicMock(return_value=MagicMock())

    with patch("app.integrations.reddit._reddit", fake_reddit):
        with pytest.raises(CircuitOpenError):
            await search_subreddits(db_session, query="test", subreddits=["startups"])
        await db_session.commit()

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.success.is_(False),
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ---------------------------------------------------------------------------
# Reddit — retry + eventual success writes exactly one row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reddit_retry_then_success_writes_one_row(db_session):
    call_count = 0

    fake_sub = MagicMock()
    fake_post = MagicMock()
    fake_post.id = "p1"
    fake_post.title = "Title"
    fake_post.url = "https://reddit.com/r/startups/p1"
    fake_post.score = 10
    fake_post.num_comments = 2
    fake_post.created_utc = 1_700_000_000.0
    fake_post.subreddit.display_name = "startups"
    fake_post.selftext = ""

    def _flaky_search(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Updated for Bug B: allow-list classifier requires an explicit transient exception type.
            raise httpx.ConnectError("connection refused by remote host")
        return iter([fake_post])

    fake_sub.search = MagicMock(side_effect=_flaky_search)
    fake_reddit = MagicMock()
    fake_reddit.subreddit = MagicMock(return_value=fake_sub)

    with (
        patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock),
        patch("app.integrations.reddit._reddit", fake_reddit),
    ):
        posts = await search_subreddits(db_session, query="test", subreddits=["startups"])
        await db_session.commit()

    assert len(posts) == 1
    assert call_count == 3

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.success.is_(True),
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()
