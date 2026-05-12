"""Rate limiting policies for Fivvle.

Authenticated endpoints — key by Firebase UID (resolved to DB user.id):
    @limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
    @router.post("/example")
    async def example(request: Request, ...): ...

Public endpoints (analytics, waitlist) — key by IP:
    @limiter.limit(PUBLIC_RATE_LIMIT, key_func=ip_key)
    @router.post("/experiments/{slug}/waitlist")
    async def example_public(request: Request, ...): ...

Behind Cloud Run, X-Forwarded-For is set correctly by Google's edge. If
deployment moves off Cloud Run, ip_key needs revisiting — see AGENTS.md
"Rate limiting" for the trust caveat.

Policy constants:
    AUTH_RATE_LIMIT   = "60/minute"   — per .cursorrules "Authenticated: 60 req/min/user"
    PUBLIC_RATE_LIMIT = "30/minute"   — per .cursorrules "Public (analytics, waitlist): 30 req/min/IP"
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.logging_config import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Policy constants — tune here, one change propagates everywhere.
# ---------------------------------------------------------------------------

AUTH_RATE_LIMIT = "60/minute"
PUBLIC_RATE_LIMIT = "30/minute"

# TODO(step 7-9): Per-user research-run cap (default 5/hour) lives in the
# experiment service, not here. AGENTS.md "Rate limiting".

# ---------------------------------------------------------------------------
# Limiter instance
#
# key_func default is get_remote_address (IP). Per-endpoint key_func
# overrides are passed via @limiter.limit(..., key_func=...).
# headers_enabled=True injects X-RateLimit-Limit, X-RateLimit-Remaining,
# and X-RateLimit-Reset into every response touching a decorated endpoint.
# default_limits=[] means no global limit; limits are set per endpoint.
# ---------------------------------------------------------------------------

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=True,
)

# ---------------------------------------------------------------------------
# Key functions
# ---------------------------------------------------------------------------


def user_key(request: Request) -> str:
    """Rate-limit key for authenticated endpoints: keyed by DB user UUID.

    Reads request.state.current_user which is set by get_current_user
    (app/auth/dependencies.py) before the route handler executes.

    Falls back to IP when current_user is absent.  In practice this only
    happens on POST /users/sync, which is the bootstrap endpoint that cannot
    use get_current_user (the User row doesn't exist yet).  The IP fallback
    gives sync a 60/min-per-IP budget — acceptable for a bootstrap call.
    """
    user = getattr(request.state, "current_user", None)
    if user is not None:
        return f"user:{user.id}"
    return f"ip:{get_remote_address(request)}"


def ip_key(request: Request) -> str:
    """Rate-limit key for public endpoints: keyed by originating IP.

    get_remote_address reads from X-Forwarded-For when present.  This is
    safe because Cloud Run's edge always sets X-Forwarded-For to the real
    client IP before traffic reaches the backend.  If Fivvle is ever deployed
    off Cloud Run without a trusted reverse proxy, this assumption must be
    revisited — an attacker could spoof X-Forwarded-For and bypass IP limits.
    See AGENTS.md "Rate limiting" for the trust caveat.
    """
    return f"ip:{get_remote_address(request)}"


# ---------------------------------------------------------------------------
# Custom 429 handler
# ---------------------------------------------------------------------------


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Return a structured JSON 429 with Retry-After and X-Request-ID headers.

    Replaces slowapi's default plain-text 429 so the response body is
    consistent with all other Fivvle error responses.

    Logs at INFO (not WARN) — rate-limited clients are routine noise and
    should not inflate production alerting thresholds.
    """
    request_id: str = getattr(request.state, "request_id", "unknown")

    # exc.retry_after is seconds-until-reset from the limits library.
    # Default to 60 if the attribute is absent or non-numeric (defensive).
    retry_after: int = 60
    raw_retry = getattr(exc, "retry_after", None)
    if raw_retry is not None:
        try:
            retry_after = int(raw_retry)
        except (ValueError, TypeError):
            pass

    _logger.info(
        "rate limit exceeded",
        limit=str(exc.detail),
        path=request.url.path,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "request_id": request_id,
            "retry_after_seconds": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-Request-ID": request_id,
        },
    )
