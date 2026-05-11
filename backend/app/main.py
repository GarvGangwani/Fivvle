"""
FastAPI application entry point.

Wires together:
- Lifespan handler (startup / shutdown)
- CORS middleware (explicit allowlist — no wildcards, per AGENTS.md)
- Security headers middleware (6 headers from AGENTS.md)
- Generic production error handler (no stack traces to clients)
- Registered routers (health only for build step 1)

Local dev:  uv run uvicorn app.main:app --reload
Production: gunicorn -k uvicorn.workers.UvicornWorker app.main:app
"""

from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import configure_logging, get_logger
from app.routers.health import router as health_router

settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifespan handler.

    Startup:
    1. Configure structlog (must happen before any logging).
    2. Initialize Firebase Admin SDK.
    3. Initialize Sentry if DSN is configured (optional in dev).

    Shutdown:
    - Placeholder — DB pool teardown will be added in build step 2.
    """
    # 1. Logging — must be first so all subsequent startup messages are captured.
    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info("starting fivvle api", environment=settings.environment)

    # 2. Firebase Admin SDK
    # Import here (after logging is configured) so any init errors are logged.
    from app.auth.firebase import init_firebase

    init_firebase(settings)

    # 3. Sentry — only when a DSN is explicitly configured.
    if settings.sentry_dsn is not None:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            send_default_pii=False,
            traces_sample_rate=0.1 if settings.is_production else 1.0,
        )
        logger.info("sentry initialized")

    yield

    # --- Shutdown ----------------------------------------------------------
    # DB connection pool teardown will be added in build step 2.
    logger.info("shutting down fivvle api")


# ---------------------------------------------------------------------------
# App construction
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Fivvle API",
    lifespan=lifespan,
    # Disable interactive docs in production (AGENTS.md "Error handling").
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# ---------------------------------------------------------------------------
# Middleware — order matters in Starlette: last added is outermost.
# ---------------------------------------------------------------------------

# CORS — explicit allowlist, no wildcards (AGENTS.md "CORS").
# Never combine allow_origins=["*"] with allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Security headers — applied to every response (AGENTS.md "Security headers").
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Any:
    response = await call_next(request)

    # Content-Security-Policy: backend serves JSON only, so 'self' is sufficient.
    # The Next.js frontend has its own, more permissive CSP in next.config.js.
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    # HSTS: only in production — setting this on localhost breaks browser dev flows.
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Production-safe generic error handler.

    In production: returns a generic message with a placeholder request_id.
    The request_id placeholder will be replaced with the real value when
    request-ID middleware is added in a later build step.

    In development: re-raises so FastAPI's default debug handler shows the
    full traceback in the response (useful during local development).
    """
    if settings.is_production:
        # Sentry captures the real exception server-side.
        logger = get_logger(__name__)
        logger.exception("unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Something went wrong",
                # Placeholder — wired to real request-ID in build step 5.
                "request_id": "n/a",
            },
        )
    # Dev: propagate so FastAPI shows the full traceback.
    raise exc


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
