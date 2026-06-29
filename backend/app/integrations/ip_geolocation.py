"""IP geolocation integration via ipwho.is.

Every geolocation lookup in Fivvle goes through this module.
Used for waitlist signup location enrichment — never called from the frontend.

Provider: https://ipwho.is/ (free HTTPS tier, no API key for MVP).
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID

import httpx
from pydantic import BaseModel

from app.cost.category import resolve_cost_category_from_external_provider
from app.db.models.external_api_call import ExternalAPICall
from app.db.session_lock import lock_for
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async
from app.utils.ip_address import is_public_ip

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_logger = get_logger(__name__)

_PROVIDER = "ipwho"
_TIMEOUT_SECONDS = 15
_BASE_URL = "https://ipwho.is"


class IpGeolocation(BaseModel):
    """Resolved city / region / country for a public IP."""

    city: str | None = None
    region: str | None = None
    country: str | None = None


class _IpWhoResponse(BaseModel):
    success: bool = False
    city: str | None = None
    region: str | None = None
    country: str | None = None
    message: str | None = None


async def _log_api_call(
    db: AsyncSession,
    *,
    experiment_id: UUID | None,
    latency_ms: int,
    success: bool,
) -> None:
    call = ExternalAPICall(
        experiment_id=experiment_id,
        provider=_PROVIDER,
        cost_category=resolve_cost_category_from_external_provider(_PROVIDER).value,
        operation="lookup",
        latency_ms=latency_ms,
        cost_usd=Decimal("0"),
        success=success,
    )
    async with lock_for(db):
        db.add(call)
        await db.flush()


def _normalize_field(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


async def lookup_ip_geolocation(
    db: AsyncSession,
    *,
    ip: str,
    experiment_id: UUID | None = None,
) -> IpGeolocation | None:
    """Resolve city, region (state), and country for a public IP.

    Returns None when the IP is non-public, the provider fails, or no location
    data is available. Never raises to callers — signup must stay resilient.
    """
    if not is_public_ip(ip):
        return None

    started_at = time.perf_counter()

    try:

        async def _do_lookup() -> IpGeolocation | None:
            url = f"{_BASE_URL}/{quote(ip, safe='')}"
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = _IpWhoResponse.model_validate(response.json())

            if not payload.success:
                return None

            location = IpGeolocation(
                city=_normalize_field(payload.city),
                region=_normalize_field(payload.region),
                country=_normalize_field(payload.country),
            )
            if not any((location.city, location.region, location.country)):
                return None
            return location

        @retry_async(max_retries=2)
        async def _lookup_with_retry() -> IpGeolocation | None:
            return await get_breaker(_PROVIDER).call(_do_lookup)

        result = await _lookup_with_retry()
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        await _log_api_call(
            db,
            experiment_id=experiment_id,
            latency_ms=latency_ms,
            success=result is not None,
        )
        if result is not None:
            _logger.info(
                "ip geolocation resolved",
                experiment_id=str(experiment_id) if experiment_id else None,
                has_city=result.city is not None,
                has_region=result.region is not None,
                has_country=result.country is not None,
            )
        return result
    except Exception:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        await _log_api_call(
            db,
            experiment_id=experiment_id,
            latency_ms=latency_ms,
            success=False,
        )
        _logger.warning(
            "ip geolocation lookup failed",
            experiment_id=str(experiment_id) if experiment_id else None,
        )
        return None


def location_label(
    *,
    city: str | None,
    region: str | None,
    country: str | None,
) -> str:
    """Human-readable location label for metrics rollups."""
    parts = [part for part in (city, region, country) if part]
    return ", ".join(parts) if parts else "Unknown"
