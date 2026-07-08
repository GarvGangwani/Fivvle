"""Perplexity sonar search integration wrapper.

EVERY Perplexity call in Fivvle goes through this module.
Direct httpx calls to Perplexity elsewhere are a violation of `.cursorrules`.

The wrapper:
- Uses httpx.AsyncClient with API key from settings.
- Logs one ExternalAPICall row per HTTP attempt (success and failure).
- Never logs query text or response content — only metadata.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import httpx

from app.config import get_settings
from app.cost.category import resolve_cost_category_from_external_provider
from app.cost.perplexity import perplexity_cost_usd
from app.db.models.external_api_call import ExternalAPICall
from app.db.session_lock import lock_for
from app.logging_config import get_logger
from app.reliability.circuit_breakers import CircuitOpenError, get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
_DEFAULT_TIMEOUT_S = 30

_http_client: httpx.AsyncClient | None = None


@dataclass
class PerplexityResult:
    title: str
    url: str
    snippet: str
    date: str | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client  # noqa: PLW0603
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(_DEFAULT_TIMEOUT_S))
    return _http_client


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
        provider="perplexity",
        cost_category=resolve_cost_category_from_external_provider("perplexity").value,
        operation=operation,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        success=success,
    )
    async with lock_for(db):
        db.add(call)
        await db.flush()


def _parse_search_results(raw: dict[str, Any], *, max_results: int) -> list[PerplexityResult]:
    search_results = raw.get("search_results")
    if isinstance(search_results, list) and search_results:
        parsed: list[PerplexityResult] = []
        for item in search_results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            parsed.append(
                PerplexityResult(
                    title=str(item.get("title") or url),
                    url=url,
                    snippet=str(item.get("snippet") or ""),
                    date=item.get("date") if item.get("date") else None,
                )
            )
            if len(parsed) >= max_results:
                break
        return parsed

    citations = raw.get("citations")
    if isinstance(citations, list):
        parsed = []
        for url in citations:
            if not isinstance(url, str) or not url.strip():
                continue
            parsed.append(
                PerplexityResult(
                    title=url,
                    url=url.strip(),
                    snippet="",
                )
            )
            if len(parsed) >= max_results:
                break
        return parsed

    return []


async def search(
    db: AsyncSession,
    *,
    query: str,
    experiment_id: UUID | None = None,
    domain_filter: list[str] | None = None,
    max_results: int = 10,
    timeout_s: int = 30,
) -> list[PerplexityResult]:
    """Run a Perplexity sonar search scoped to optional domain filters.

    Args:
        db: caller's session. One ExternalAPICall row per HTTP attempt.
        query: search query string (never logged).
        experiment_id: optional FK for cost rollup.
        domain_filter: Perplexity search_domain_filter allowlist entries.
        max_results: cap on parsed search_results returned.
        timeout_s: HTTP timeout in seconds.

    Returns parsed search results. Raises on final failure after logging.
    """
    settings = get_settings()
    started_at = time.perf_counter()

    async def _perform_search_attempt() -> dict[str, Any]:
        """One Perplexity HTTP round-trip; logs audit row before returning."""
        attempt_started = time.perf_counter()
        try:
            payload: dict[str, Any] = {
                "model": "sonar",
                "messages": [{"role": "user", "content": query}],
                "web_search_options": {"search_context_size": "low"},
            }
            if domain_filter:
                payload["search_domain_filter"] = domain_filter

            client = _get_http_client()
            response = await asyncio.wait_for(
                client.post(
                    _PERPLEXITY_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {settings.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                ),
                timeout=timeout_s,
            )
            response.raise_for_status()
            raw: dict[str, Any] = response.json()

            latency_ms = int((time.perf_counter() - attempt_started) * 1000)
            usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
            usage_cost = usage.get("cost") if isinstance(usage.get("cost"), dict) else None
            cost = perplexity_cost_usd(usage_cost, settings.perplexity_usd_per_search)
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")
            results = _parse_search_results(raw, max_results=max_results)

            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="search",
                latency_ms=latency_ms,
                cost_usd=cost,
                success=True,
            )

            _logger.info(
                "perplexity search completed",
                integration="perplexity",
                provider="perplexity",
                num_results=len(results),
                latency_ms=latency_ms,
                cost_usd=str(cost),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
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
                    success=False,
                )
            except Exception as log_exc:
                _logger.warning(
                    "failed to log failed perplexity call",
                    integration="perplexity",
                    error=str(log_exc),
                )
            raise

    try:

        @retry_async()
        async def _call_perplexity_with_retry() -> dict[str, Any]:
            return await get_breaker("perplexity").call(_perform_search_attempt)

        raw = await _call_perplexity_with_retry()
        return _parse_search_results(raw, max_results=max_results)

    except CircuitOpenError:
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
            _logger.warning(
                "failed to log failed perplexity call",
                integration="perplexity",
                error=str(log_exc),
            )
        _logger.warning(
            "perplexity search failed",
            integration="perplexity",
            provider="perplexity",
            latency_ms=latency_ms,
            error_type="CircuitOpenError",
        )
        raise
    except Exception as exc:
        _logger.warning(
            "perplexity search failed",
            integration="perplexity",
            provider="perplexity",
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            error_type=type(exc).__name__,
        )
        raise
