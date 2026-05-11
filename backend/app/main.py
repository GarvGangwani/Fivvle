"""
FastAPI application entry point.

Wires together:
- Lifespan handler (startup / shutdown)
- CORS middleware (explicit allowlist — no wildcards, per AGENTS.md)
- Security headers middleware (6 headers from AGENTS.md)
- Request-ID middleware (generates/propagates X-Request-ID)
- Sentry context middleware (enriches Sentry scope per request)
- Generic production error handler (no stack traces to clients)
- Registered routers (health, users, admin)

Local dev:  uv run uvicorn app.main:app --reload
Production: gunicorn -k uvicorn.workers.UvicornWorker app.main:app

Middleware execution order (outermost → innermost, i.e. first to see a
request → closest to the route handler):
  CORS → security-headers → request-ID → Sentry context → handler

In Starlette, the LAST call to add_middleware() becomes the outermost layer.
So middlewares are registered here in the reverse of the execution order
(innermost first, outermost last).
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging, get_logger
from app.middleware.error_handler import generic_exception_handler
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.sentry_context import SentryContextMiddleware
from app.observability.sentry import init_sentry
from app.routers.admin import router as admin_router
from app.routers.health import router as health_router
from app.routers.users import router as users_router

settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifespan handler.

    Startup order:
    1. Configure structlog (must happen before any logging).
    2. Initialise Sentry (before other init so startup errors are captured).
    3. Initialise DB engine (before Firebase so the pool is ready).
    4. Initialise Firebase Admin SDK.

    Shutdown order:
    1. Dispose DB engine (drains the connection pool cleanly).
    """
    # 1. Logging — must be first so all subsequent startup messages are captured.
    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info("starting fivvle api", environment=settings.environment)

    # 2. Sentry — initialise before other services so startup errors are captured.
    init_sentry(settings)

    # 3. Database engine — initialise before Firebase so the pool is ready.
    from app.db.session import dispose_engine, init_engine  # noqa: PLC0415

    init_engine(settings)

    # 4. Firebase Admin SDK.
    from app.auth.firebase import init_firebase  # noqa: PLC0415

    init_firebase(settings)

    yield

    # --- Shutdown ----------------------------------------------------------
    await dispose_engine()
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
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

# Registered before middleware so the handler is available to all layers.
# FastAPI/Starlette dispatch HTTPException to its own built-in handler first
# (more-specific type wins), so HTTPExceptions never reach this handler.
app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# Middleware — registration order matters.
#
# Starlette builds the middleware stack so the LAST add_middleware() call
# becomes the OUTERMOST layer (first to process incoming requests).
# Register innermost → outermost so execution order is:
#   CORS → security-headers → request-ID → Sentry context → handler
# ---------------------------------------------------------------------------

# 1. Sentry context — innermost; runs closest to the route handler.
app.add_middleware(SentryContextMiddleware)

# 2. Request ID — sets request_id before Sentry context reads it.
app.add_middleware(RequestIDMiddleware)


# 3. Security headers — applied to every response (AGENTS.md "Security headers").
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Any:
    response = await call_next(request)

    # Content-Security-Policy: backend serves JSON only, so 'self' is sufficient.
    # The Next.js frontend has its own, more permissive CSP in next.config.js.
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    # HSTS: production only — setting this on localhost breaks browser dev flows.
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


# 4. CORS — outermost; handles preflight OPTIONS before any other middleware.
# Never combine allow_origins=["*"] with allow_credentials=True (AGENTS.md "CORS").
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(users_router)
app.include_router(admin_router)
