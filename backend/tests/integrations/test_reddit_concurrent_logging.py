"""Concurrent ExternalAPICall logging for Reddit."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.external_api_call import ExternalAPICall
from app.integrations.reddit import search_subreddits


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


@pytest.mark.asyncio
async def test_concurrent_failing_reddit_calls_all_log_failure_rows(
    db_session: AsyncSession,
    capsys: pytest.CaptureFixture[str],
) -> None:
    await db_session.execute(delete(ExternalAPICall).where(ExternalAPICall.provider == "reddit"))
    await db_session.commit()

    with patch(
        "app.integrations.reddit._fetch_subreddit_posts",
        side_effect=RuntimeError("simulated reddit failure"),
    ):
        await asyncio.gather(
            *[
                search_subreddits(db_session, query=f"q{i}", subreddits=["test"])
                for i in range(15)
            ],
            return_exceptions=True,
        )
    await db_session.commit()

    captured = capsys.readouterr()
    assert "session is already flushing" not in captured.out.lower(), (
        f"Bug A detected in stdout. Excerpt: "
        f"{[line for line in captured.out.splitlines() if 'flushing' in line.lower()][:3]}"
    )

    stmt = select(ExternalAPICall).where(
        ExternalAPICall.provider == "reddit",
        ExternalAPICall.success == False,  # noqa: E712
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 15, f"Expected 15 failure rows, got {len(rows)}"
    assert all(r.success is False for r in rows)
    assert all(r.cost_usd == Decimal("0") for r in rows)
    assert all(r.operation == "search_subreddits" for r in rows)

    for row in rows:
        await db_session.delete(row)
    await db_session.commit()
