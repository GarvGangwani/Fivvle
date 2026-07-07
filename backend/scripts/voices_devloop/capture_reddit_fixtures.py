"""One-time capture of live Reddit JSON fixtures (sanitized, no usernames).

Usage:
  uv run python -m scripts.voices_devloop.capture_reddit_fixtures \\
      --output-dir scripts/voices_devloop/fixtures/reddit_full
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from app.config import get_settings
from app.db.session import get_sessionmaker, init_engine
from app.integrations.reddit import fetch_post_comments, search_subreddits

_USERNAME_RE = re.compile(r"u/[A-Za-z0-9_-]+")


def _scrub(text: str) -> str:
    return _USERNAME_RE.sub("[user]", text)


async def _capture(output_dir: Path) -> None:
    init_engine(get_settings())
    sm = get_sessionmaker()
    async with sm() as db:
        posts = await search_subreddits(
            db,
            query="founder validation",
            subreddits=["startups", "Entrepreneur", "saas"],
            limit=15,
        )
        post_payload = []
        comments_payload: dict[str, list[dict]] = {}
        for post in posts:
            post_payload.append(
                {
                    **post.model_dump(),
                    "title": _scrub(post.title),
                    "selftext": _scrub(post.selftext),
                }
            )
            comments = await fetch_post_comments(db, post_id=post.id, limit=10)
            comments_payload[post.id] = [
                {**c.model_dump(), "body": _scrub(c.body)} for c in comments
            ]
        await db.rollback()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "subreddit_posts.json").write_text(
        json.dumps(post_payload, indent=2),
        encoding="utf-8",
    )
    (output_dir / "post_comments.json").write_text(
        json.dumps(comments_payload, indent=2),
        encoding="utf-8",
    )
    print(f"Captured {len(post_payload)} posts to {output_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture Reddit fixtures")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    asyncio.run(_capture(Path(args.output_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
