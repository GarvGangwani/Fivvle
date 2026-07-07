"""Smoke test: live Reddit public JSON search (no DB writes)."""

from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.db.session import get_sessionmaker, init_engine
from app.integrations.reddit import search_subreddits


async def _main() -> None:
    init_engine(get_settings())
    sm = get_sessionmaker()
    async with sm() as db:
        posts = await search_subreddits(
            db,
            query="pricing",
            subreddits=["startups", "Entrepreneur"],
            limit=5,
        )
        await db.rollback()
    print(f"OK: {len(posts)} RedditPost objects returned")


if __name__ == "__main__":
    asyncio.run(_main())
    sys.exit(0)
