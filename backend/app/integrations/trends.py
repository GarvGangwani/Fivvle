"""Google Trends integration wrapper via pytrends (ADR 0015).

EVERY Google Trends call in Fivvle goes through this module.
Direct pytrends imports anywhere else are a violation of `.cursorrules`.

The wrapper:
- Runs the sync pytrends SDK in asyncio.to_thread so the event loop is never blocked.
- Logs one ExternalAPICall row per operation (success and failure).
- Never logs keyword strings or trend values — only metadata.

pytrends requires no credentials; `.env` is unchanged.

Per `.cursorrules` Reliability: retry 3× then continue without; note in report.
Terminal failure returns None (graceful-skip) — does not raise into the orchestrator.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import ValidationError
import pytrends.request as pytrends_request
from pytrends.exceptions import ResponseError, TooManyRequestsError

from app.db.models.external_api_call import ExternalAPICall
from app.db.session_lock import lock_for
from app.logging_config import get_logger
from app.reliability.circuit_breakers import CircuitOpenError, get_breaker
from app.reliability.retry import retry_async
from app.schemas.search import TrendsPoint, TrendsSeries

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

TRENDS_TIMEFRAME = "today 12-m"
TRENDS_GEO = ""
_MAX_KEYWORDS = 5
_TIMEOUT_SECONDS = 15  # per .cursorrules reliability section


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
        provider="pytrends",
        operation=operation,
        latency_ms=latency_ms,
        cost_usd=Decimal("0"),
        success=success,
    )
    async with lock_for(db):
        db.add(call)
        await db.flush()


def _dataframe_to_series(
    keywords: list[str],
    df,
) -> dict[str, TrendsSeries]:
    """Map a pytrends interest_over_time DataFrame to Fivvle-owned DTOs."""
    result: dict[str, TrendsSeries] = {}
    has_rows = df is not None and not df.empty

    for kw in keywords:
        points: list[TrendsPoint] = []
        if has_rows and kw in df.columns:
            for ts, row in df.iterrows():
                points.append(
                    TrendsPoint(
                        date=ts.strftime("%Y-%m-%d"),
                        value=int(row[kw]),
                    )
                )
        result[kw] = TrendsSeries(keyword=kw, points=points)

    return result


def _sync_fetch_interest_over_time(
    keywords: list[str],
    *,
    timeframe: str,
    geo: str,
) -> dict[str, TrendsSeries]:
    """Synchronous pytrends call — run via asyncio.to_thread.

    Constructs a fresh TrendReq per invocation (no shared module-level client).
    """
    pt = pytrends_request.TrendReq(
        hl="en-US", tz=0, timeout=(_TIMEOUT_SECONDS, _TIMEOUT_SECONDS)
    )
    pt.build_payload(kw_list=keywords, timeframe=timeframe, geo=geo)
    df = pt.interest_over_time()
    return _dataframe_to_series(keywords, df)


async def fetch_trends(
    db: AsyncSession,
    keywords: list[str],
    experiment_id: UUID | None = None,
) -> dict[str, TrendsSeries] | None:
    """Fetch Google Trends interest-over-time for up to five keywords.

    Args:
        db: caller's session. One ExternalAPICall row is written on success or
            terminal failure (not on early-return skips).
        keywords: 1–5 keyword phrases (caller adapts from RefinedIdea / plan).
        experiment_id: optional FK for cost rollup.

    Returns:
        dict mapping each keyword to its TrendsSeries, or None on graceful-skip
        (empty input, circuit open, retries exhausted, or schema validation failure).
    """
    if not keywords:
        return None

    kw_batch = keywords[:_MAX_KEYWORDS]
    started_at = time.perf_counter()

    try:

        async def _do_trends_call() -> dict[str, TrendsSeries]:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _sync_fetch_interest_over_time,
                    kw_batch,
                    timeframe=TRENDS_TIMEFRAME,
                    geo=TRENDS_GEO,
                ),
                timeout=_TIMEOUT_SECONDS,
            )

        @retry_async()
        async def _call_trends_with_retry() -> dict[str, TrendsSeries]:
            return await get_breaker("pytrends").call(_do_trends_call)

        raw = await _call_trends_with_retry()
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        # Validate every series (guards against provider drift / bad values).
        validated: dict[str, TrendsSeries] = {}
        for key, series in raw.items():
            validated[key] = TrendsSeries.model_validate(series.model_dump())

        await _log_api_call(
            db,
            experiment_id=experiment_id,
            operation="fetch_trends",
            latency_ms=latency_ms,
            success=True,
        )

        _logger.info(
            "pytrends fetch_trends completed",
            integration="pytrends",
            keywords_count=len(kw_batch),
            series_count=len(validated),
            latency_ms=latency_ms,
            cost_usd=Decimal("0"),
        )

        return validated

    except ValidationError as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        _logger.warning(
            "pytrends fetch_trends schema validation failed",
            integration="pytrends",
            experiment_id=str(experiment_id) if experiment_id else None,
            keywords_count=len(kw_batch),
            error_type=type(exc).__name__,
        )
        return None

    except CircuitOpenError as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="fetch_trends",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed pytrends call", error=str(log_exc))

        _logger.warning(
            "pytrends fetch_trends skipped — circuit open",
            integration="pytrends",
            experiment_id=str(experiment_id) if experiment_id else None,
            keywords_count=len(kw_batch),
            error_type=type(exc).__name__,
        )
        return None

    except (TooManyRequestsError, ResponseError, Exception) as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_api_call(
                db,
                experiment_id=experiment_id,
                operation="fetch_trends",
                latency_ms=latency_ms,
                success=False,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed pytrends call", error=str(log_exc))

        _logger.warning(
            "pytrends fetch_trends failed",
            integration="pytrends",
            experiment_id=str(experiment_id) if experiment_id else None,
            keywords_count=len(kw_batch),
            error_type=type(exc).__name__,
        )
        return None
