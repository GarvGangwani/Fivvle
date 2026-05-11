"""Generic production-safe exception handler.

Registered via ``app.add_exception_handler(Exception, generic_exception_handler)``.

Behaviour (AGENTS.md "Error handling"):
- Catches only truly *unhandled* exceptions — FastAPI/Starlette dispatch
  ``HTTPException`` to its own registered handler first (more specific type
  wins), so ``HTTPException`` subclasses never reach this handler.
- Logs the full stack trace server-side via structlog at ERROR level so
  developers can diagnose problems. The structlog ``merge_contextvars``
  processor automatically attaches ``request_id`` from the RequestID
  middleware's contextvar binding.
- The ``LoggingIntegration`` in the Sentry SDK will capture this ERROR-level
  stdlib log record as a Sentry event. We do NOT call
  ``sentry_sdk.capture_exception()`` here — doing so would double-capture.
- Returns a generic JSON body to the client: NO stack trace, NO exception
  type, NO file paths, NO internal details.
- Includes ``request_id`` in the response body so the client can reference
  it in a support request and ops can correlate with server logs.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.logging_config import get_logger

_logger = get_logger(__name__)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a 500 JSON response without leaking internal details.

    HTTPExceptions are handled by Starlette's built-in handler (registered
    before this one by FastAPI) and will never reach this function. The
    isinstance guard is a belt-and-suspenders safety net in case the handler
    is invoked via an unconventional path.
    """
    if isinstance(exc, HTTPException):
        # Should not happen — FastAPI routes HTTPException to its own handler.
        # If it somehow reaches here, re-raise so the default handler handles it.
        raise exc

    request_id: str = getattr(request.state, "request_id", "unknown")

    _logger.error(
        "unhandled exception",
        exc_info=exc,
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        request_id=request_id,
    )

    response = JSONResponse(
        status_code=500,
        content={
            "error": "Something went wrong",
            "request_id": request_id,
        },
    )
    # Set the header directly on the error response. BaseHTTPMiddleware may
    # not get a chance to patch headers when an exception escapes call_next
    # via an anyio ExceptionGroup. Setting it here ensures the header is
    # always present on 500 responses regardless of the middleware pathway.
    response.headers["X-Request-ID"] = request_id
    return response
