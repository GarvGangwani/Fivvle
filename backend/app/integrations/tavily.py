"""Tavily web search integration wrapper.

EVERY Tavily call in Fivvle goes through this module.
Direct tavily-python SDK imports anywhere else are a violation of
`.cursorrules` "What NOT to do".

The wrapper:
- Runs the sync SDK in asyncio.to_thread so the event loop is never blocked.
- Logs one ExternalAPICall row per operation (success and failure).
- Never logs query text or scraped content — only metadata.

Pricing verified 2026-05-11 against https://docs.tavily.com/documentation/api-credits
and https://tavily.com/pricing:
  - Basic search:    1 credit  = $0.008 (pay-as-you-go rate)
  - Advanced search: 2 credits = $0.016
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel
from tavily import TavilyClient

from app.config import get_settings
from app.db.models.external_api_call import ExternalAPICall
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

# Cost per Tavily search call (PAYG rate, verified 2026-05-11).
# One credit = $0.008. Basic = 1 credit, Advanced = 2 credits.
_COST_PER_BASIC: Decimal = Decimal("0.008")
_COST_PER_ADVANCED: Decimal = Decimal("0.016")

_TIMEOUT_SECONDS = 30  # per .cursorrules reliability section

# Lazy module-level client. Built on first call.
_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client  # noqa: PLW0603
    if _client is None:
        settings = get_settings()
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


class TavilyResult(BaseModel):
    """A single result returned by Tavily search."""

    title: str
    url: str
    content: str  # snippet from Tavily, NOT raw HTML
    score: float | None = None


async def _log_api_call(
    db: AsyncSession,
    *,
    experiment_id: UUID | None,
    operation: str,
    latency_ms: int,
    cost_usd: Decimal,
    success: bool,
) -> None:
    """Persist one row to external_api_calls. Does NOT commit."""
    call = ExternalAPICall(
        experiment_id=experiment_id,
        provider="tavily",
        operation=operation,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        success=success,
    )
    db.add(call)
    await db.flush()


async def search(
    db: AsyncSession,
    *,
    query: str,
    experiment_id: UUID | None = None,
    max_results: int = 5,
    search_depth: Literal["basic", "advanced"] = "basic",
) -> list[TavilyResult]:
    """Run a Tavily web search.

    Args:
        db: caller's session. One ExternalAPICall row is written here.
        query: search query string.
        experiment_id: optional FK for cost rollup.
        max_results: number of results to return (default 5).
        search_depth: "basic" (1 credit) or "advanced" (2 credits).

    Returns a list of TavilyResult (title, url, content snippet, score).

    Raises whatever the Tavily SDK raises on network/auth failure — but only
    after logging a zero-cost ExternalAPICall row with success=False.
    """
    cost = _COST_PER_BASIC if search_depth == "basic" else _COST_PER_ADVANCED
    started_at = time.perf_counter()

    try:
        async def _do_tavily_call():
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _get_client().search,
                    query,
                    max_results=max_results,
                    search_depth=search_depth,
                ),
                timeout=_TIMEOUT_SECONDS,
            )

        @retry_async()
        async def _call_tavily_with_retry():
            return await get_breaker("tavily").call(_do_tavily_call)

        raw = await _call_tavily_with_retry()
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        results = [
            TavilyResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score"),
            )
            for r in raw.get("results", [])
        ]

        await _log_api_call(
            db,
            experiment_id=experiment_id,
            operation="search",
            latency_ms=latency_ms,
            cost_usd=cost,
            success=True,
        )

        # Log only metadata — NEVER query text or result content.
        _logger.info(
            "tavily search completed",
            num_results=len(results),
            search_depth=search_depth,
            latency_ms=latency_ms,
            cost_usd=str(cost),
        )

        return results

    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="search",
                latency_ms=latency_ms,
                cost_usd=Decimal("0"),
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed tavily call", error=str(log_exc))

        _logger.warning(
            "tavily search failed",
            search_depth=search_depth,
            error_type=type(exc).__name__,
        )
        raise
