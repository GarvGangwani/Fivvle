"""External API integration wrappers.

EVERY external paid/metered/rate-limited HTTP call goes through this package.
Direct httpx/requests calls outside this package are a violation of
`.cursorrules` "What NOT to do".

Each wrapper logs one ExternalAPICall row per operation, including failures.
"""

from app.integrations.google_trends import (
    TrendsDataPoint,
    TrendsResult,
    get_interest_over_time,
)
from app.integrations.reddit import (
    RedditComment,
    RedditPost,
    fetch_post_comments,
    search_subreddits,
)
from app.integrations.tavily import TavilyResult, search

__all__ = [
    "RedditComment",
    "RedditPost",
    "TavilyResult",
    "TrendsDataPoint",
    "TrendsResult",
    "fetch_post_comments",
    "get_interest_over_time",
    "search",
    "search_subreddits",
]
