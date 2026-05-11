"""Sentry context middleware — enrich the Sentry scope with request metadata.

Runs AFTER RequestIDMiddleware, BEFORE route handlers. Sets Sentry tags that
apply to the entire request regardless of which route is matched.

This middleware is intentionally thin:
- No database calls.
- No I/O of any kind.
- Does not resolve authentication. If ``request.state.current_user`` is
  already populated (unlikely at this point — auth deps run per-route), the
  user context is set; otherwise it is left unset and individual route
  handlers or ``get_current_user`` populate it.

User context is set exclusively with the internal UUID (AGENTS.md
"Logging hygiene": "user email addresses tied to user_id without business
reason — use user_id alone where possible").
"""

from __future__ import annotations

from typing import Any

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SentryContextMiddleware(BaseHTTPMiddleware):
    """Populate Sentry scope with request-level context."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Re-set request_id in case this middleware runs in a new scope.
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            sentry_sdk.set_tag("request_id", request_id)

        # Use the route template (e.g. /experiments/{id}), not the resolved URL,
        # so high-cardinality resource IDs don't fragment Sentry's grouping.
        route = request.scope.get("route")
        path_tag = getattr(route, "path", None) or request.url.path
        sentry_sdk.set_tag("path", path_tag)
        sentry_sdk.set_tag("method", request.method)

        # Set Sentry user context if auth has already resolved (rare at this
        # point — the auth dependency runs inside the route handler, not here).
        current_user = getattr(request.state, "current_user", None)
        if current_user is not None:
            sentry_sdk.set_user({"id": str(current_user.id)})

        return await call_next(request)
