"""Google Trends integration wrapper via pytrends.

EVERY Google Trends call in Fivvle goes through this module.
Direct pytrends imports anywhere else are a violation of `.cursorrules`.

The wrapper:
- Runs the sync pytrends SDK in asyncio.to_thread so the event loop is unblocked.
- Logs one ExternalAPICall row per operation (success and failure).
- NEVER logs keywords or trend data content — only metadata.

IMPORTANT: pytrends is notoriously flaky — Google aggressively rate-limits
unofficial Trends API requests. Per `.cursorrules`:
  "Trends flaky: retry 3x then continue without; note in report."
Retry logic is NOT implemented here — that lives at the research engine
orchestrator level (build step 5 / reliability infra). This wrapper catches
pytrends-specific exceptions and re-raises them so orchestrators can decide
whether to skip or retry.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel
from pytrends.exceptions import ResponseError, TooManyRequestsError
from pytrends.request import TrendReq

from app.db.models.external_api_call import ExternalAPICall
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

_TIMEOUT_SECONDS = 15  # per .cursorrules reliability section
_MAX_KEYWORDS = 5  # Google Trends API hard limit for comparison

# Lazy module-level client. Built on first call.
_pytrends: TrendReq | None = None


def _get_client() -> TrendReq:
    global _pytrends  # noqa: PLW0603
    if _pytrends is None:
        # timeout=(connect_timeout, read_timeout) — both set to spec limit.
        _pytrends = TrendReq(hl="en-US", tz=0, timeout=(_TIMEOUT_SECONDS, _TIMEOUT_SECONDS))
    return _pytrends


class TrendsDataPoint(BaseModel):
    """Interest score at a single point in time for each keyword."""

    date: str  # ISO date string (YYYY-MM-DD)
    values: dict[str, int]  # keyword -> interest score (0-100)


class TrendsResult(BaseModel):
    """Full interest-over-time result for a keyword comparison."""

    keywords: list[str]
    timeframe: str
    geo: str
    data_points: list[TrendsDataPoint]


async def _log_api_call(
    db: AsyncSession,
    *,
    experiment_id: UUID | None,
    operation: str,
    latency_ms: int,
    success: bool,
) -> None:
    """Persist one row to external_api_calls. Does NOT commit."""
    call = ExternalAPICall(
        experiment_id=experiment_id,
        provider="google_trends",
        operation=operation,
        latency_ms=latency_ms,
        cost_usd=Decimal("0"),  # Google Trends free — always $0
        success=success,
    )
    db.add(call)
    await db.flush()


def _fetch_interest_over_time(
    keywords: list[str],
    timeframe: str,
    geo: str,
) -> TrendsResult:
    """Synchronous pytrends call — run via asyncio.to_thread.

    Returns a TrendsResult. Raises TooManyRequestsError / ResponseError from
    pytrends if Google rejects the request.
    """
    pt = _get_client()
    pt.build_payload(kw_list=keywords, timeframe=timeframe, geo=geo)
    df = pt.interest_over_time()

    data_points: list[TrendsDataPoint] = []
    if df is not None and not df.empty:
        for ts, row in df.iterrows():
            values = {kw: int(row[kw]) for kw in keywords if kw in row}
            data_points.append(
                TrendsDataPoint(
                    date=ts.strftime("%Y-%m-%d"),
                    values=values,
                )
            )

    return TrendsResult(
        keywords=keywords,
        timeframe=timeframe,
        geo=geo,
        data_points=data_points,
    )


async def get_interest_over_time(
    db: AsyncSession,
    *,
    keywords: list[str],
    timeframe: str = "today 12-m",
    geo: str = "",
    experiment_id: UUID | None = None,
) -> TrendsResult:
    """Fetch Google Trends interest-over-time for up to 5 keywords.

    Args:
        db: caller's session. One ExternalAPICall row is written here.
        keywords: 1–5 strings. Google Trends API caps comparisons at 5.
        timeframe: pytrends timeframe string. "today 12-m" = last 12 months.
            Other examples: "today 5-y", "now 7-d".
        geo: country code like "US", "IN". Empty string = worldwide.
        experiment_id: optional FK for cost rollup.

    Returns TrendsResult with the time-series data per keyword.
    Cost: $0 (Google Trends is free but rate-limited and flaky).

    Raises:
        ValueError: if more than 5 keywords are provided.
        TooManyRequestsError: Google rate-limited this request.
        ResponseError: generic pytrends API failure.
        asyncio.TimeoutError: request exceeded _TIMEOUT_SECONDS.

    All failures are logged as zero-cost ExternalAPICall rows before re-raising.
    """
    if len(keywords) > _MAX_KEYWORDS:
        raise ValueError(
            f"Google Trends supports at most {_MAX_KEYWORDS} keywords; "
            f"got {len(keywords)}"
        )
    if not keywords:
        raise ValueError("keywords must be a non-empty list")

    started_at = time.perf_counter()

    try:
        async def _do_trends_call():
            return await asyncio.wait_for(
                asyncio.to_thread(_fetch_interest_over_time, keywords, timeframe, geo),
                timeout=_TIMEOUT_SECONDS,
            )

        @retry_async()
        async def _call_trends_with_retry():
            return await get_breaker("google_trends").call(_do_trends_call)

        result = await _call_trends_with_retry()
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        await _log_api_call(
            db,
            experiment_id=experiment_id,
            operation="get_interest_over_time",
            latency_ms=latency_ms,
            success=True,
        )

        # Log only metadata — NEVER log keywords or trend values.
        _logger.info(
            "google_trends get_interest_over_time completed",
            num_keywords=len(keywords),
            num_data_points=len(result.data_points),
            timeframe=timeframe,
            geo=geo or "worldwide",
            latency_ms=latency_ms,
        )

        return result

    except (TooManyRequestsError, ResponseError) as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="get_interest_over_time",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed trends call", error=str(log_exc))

        _logger.warning(
            "google_trends rate-limited or response error",
            error_type=type(exc).__name__,
        )
        raise

    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="get_interest_over_time",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed trends call", error=str(log_exc))

        _logger.warning(
            "google_trends get_interest_over_time failed",
            error_type=type(exc).__name__,
        )
        raise
