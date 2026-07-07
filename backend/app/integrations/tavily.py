"""Tavily web search integration wrapper.

EVERY Tavily call in Fivvle goes through this module.
Direct tavily-python SDK imports anywhere else are a violation of
`.cursorrules` "What NOT to do".

The wrapper:
- Runs the sync SDK in asyncio.to_thread so the event loop is never blocked.
- Logs one ExternalAPICall row per HTTP attempt (success and failure).
- Uses Tavily ``include_usage=True`` when available for credit-accurate costs.
- Never logs query text or scraped content — only metadata.

Pricing: configure ``TAVILY_USD_PER_CREDIT`` to match your Tavily plan.
Credit counts per search depth: https://docs.tavily.com/documentation/api-credits
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
from app.cost.category import resolve_cost_category_from_external_provider
from app.cost.tavily import (
    resolve_tavily_credits_from_response,
    tavily_cost_usd,
)
from app.db.models.external_api_call import ExternalAPICall
from app.db.session_lock import lock_for
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

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
    api_credits: int | None,
    success: bool,
) -> None:
    """Persist one row to external_api_calls. Does NOT commit."""
    call = ExternalAPICall(
        experiment_id=experiment_id,
        provider="tavily",
        cost_category=resolve_cost_category_from_external_provider("tavily").value,
        operation=operation,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        api_credits=api_credits,
        success=success,
    )
    async with lock_for(db):
        db.add(call)
        await db.flush()


async def search(
    db: AsyncSession,
    *,
    query: str,
    experiment_id: UUID | None = None,
    max_results: int = 5,
    search_depth: Literal["basic", "advanced"] = "basic",
    include_domains: list[str] | None = None,
) -> list[TavilyResult]:
    """Run a Tavily web search.

    Args:
        db: caller's session. One ExternalAPICall row is written per HTTP attempt.
        query: search query string.
        experiment_id: optional FK for cost rollup.
        max_results: number of results to return (default 5).
        search_depth: "basic" (1 credit) or "advanced" (2 credits).
        include_domains: optional Tavily domain bias list (soft signal).

    Returns a list of TavilyResult (title, url, content snippet, score).

    Raises whatever the Tavily SDK raises on network/auth failure — but only
    after logging a zero-cost ExternalAPICall row with success=False.
    """
    settings = get_settings()
    started_at = time.perf_counter()

    async def _perform_search_attempt() -> dict:
        """One Tavily HTTP round-trip; logs audit row before returning."""
        attempt_started = time.perf_counter()
        try:
            search_kwargs: dict[str, object] = {
                "max_results": max_results,
                "search_depth": search_depth,
                "include_usage": True,
            }
            if include_domains:
                search_kwargs["include_domains"] = include_domains
            raw = await asyncio.wait_for(
                asyncio.to_thread(
                    _get_client().search,
                    query,
                    **search_kwargs,
                ),
                timeout=_TIMEOUT_SECONDS,
            )
            latency_ms = int((time.perf_counter() - attempt_started) * 1000)
            credits = resolve_tavily_credits_from_response(
                raw,
                search_depth=search_depth,
            )
            cost = tavily_cost_usd(credits, settings.tavily_usd_per_credit)

            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="search",
                latency_ms=latency_ms,
                cost_usd=cost,
                api_credits=credits,
                success=True,
            )

            _logger.info(
                "tavily search completed",
                num_results=len(raw.get("results", [])),
                search_depth=search_depth,
                latency_ms=latency_ms,
                api_credits=credits,
                cost_usd=str(cost),
            )
            return raw
        except Exception:
            latency_ms = int((time.perf_counter() - attempt_started) * 1000)
            try:
                await _log_api_call(
                    db,
                    experiment_id=experiment_id,
                    operation="search",
                    latency_ms=latency_ms,
                    cost_usd=Decimal("0"),
                    api_credits=None,
                    success=False,
                )
            except Exception as log_exc:
                _logger.warning(
                    "failed to log failed tavily call",
                    error=str(log_exc),
                )
            raise

    try:

        @retry_async()
        async def _call_tavily_with_retry() -> dict:
            return await get_breaker("tavily").call(_perform_search_attempt)

        raw = await _call_tavily_with_retry()

        results = [
            TavilyResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score"),
            )
            for r in raw.get("results", [])
        ]

        return results

    except Exception as exc:
        _logger.warning(
            "tavily search failed",
            search_depth=search_depth,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            error_type=type(exc).__name__,
        )
        raise
