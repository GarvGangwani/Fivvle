"""Request-ID middleware — generate or propagate a per-request identifier.

Execution order in the middleware stack (outermost → innermost):
  CORS → security-headers → **RequestIDMiddleware** → SentryContextMiddleware → handler

What this middleware does, in order, for every request:
1. Read ``X-Request-ID`` inbound header. Accept it if it matches the safe
   pattern (alphanumeric/hyphen/underscore, 8–128 chars); otherwise generate a
   fresh UUID4 hex string. Malformed inbound values are discarded silently at
   DEBUG (not WARN — it's noise from misconfigured clients).
2. Bind ``request_id`` to structlog contextvars. Because
   ``structlog.contextvars.merge_contextvars`` is already in the processor
   chain (logging_config.py), every log record emitted during the request
   automatically carries ``request_id``.
3. Set ``request_id`` as a Sentry tag via ``sentry_sdk.set_tag()``.
4. Attach the value to ``request.state.request_id`` for handler code.
5. Call the downstream handler.
6. Set ``X-Request-ID`` on the response so clients can correlate.

The ``structlog.contextvars.bound_contextvars`` context manager ensures the
binding is cleared after the request completes, even on errors.

This middleware has zero dependencies on authentication, the database, or any
external service (AGENTS.md "Authentication and authorization").
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import sentry_sdk
import structlog
import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_logger = structlog.get_logger(__name__)

# Accept alphanumeric characters, hyphens, and underscores; length 8–128.
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{8,128}$")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique, safe request ID to every request/response cycle."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        inbound = request.headers.get("X-Request-ID", "")

        if inbound and _SAFE_ID_RE.match(inbound):
            request_id = inbound
        else:
            if inbound:
                # Present but invalid — discard silently. DEBUG only; this is
                # routine noise from clients sending arbitrary header values.
                _logger.debug("invalid inbound X-Request-ID discarded")
            request_id = uuid.uuid4().hex

        # Bind to structlog contextvars for the duration of the request.
        # bound_contextvars restores the previous state on exit (even on error).
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            sentry_sdk.set_tag("request_id", request_id)
            request.state.request_id = request_id
            response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        return response
