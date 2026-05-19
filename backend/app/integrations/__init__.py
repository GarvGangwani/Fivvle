"""External API integration wrappers.

EVERY external paid/metered/rate-limited HTTP call goes through this package.
Direct httpx/requests calls outside this package are a violation of
`.cursorrules` "What NOT to do".

Each wrapper logs one ExternalAPICall row per operation, including failures.
"""

from app.integrations.reddit import (
    RedditComment,
    RedditPost,
    fetch_post_comments,
    search_subreddits,
)
from app.integrations.tavily import TavilyResult, search
from app.integrations.trends import fetch_trends

__all__ = [
    "RedditComment",
    "RedditPost",
    "TavilyResult",
    "fetch_post_comments",
    "fetch_trends",
    "search",
    "search_subreddits",
]
