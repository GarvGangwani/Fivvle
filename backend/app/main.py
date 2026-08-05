"""
FastAPI application entry point.

Wires together:
- Lifespan handler (startup / shutdown)
- CORS middleware (explicit allowlist — no wildcards, per AGENTS.md)
- Security headers middleware (6 headers from AGENTS.md)
- Request-ID middleware (generates/propagates X-Request-ID)
- SlowAPI rate-limiting middleware (per-endpoint limits, step 5C)
- Sentry context middleware (enriches Sentry scope per request)
- Generic production error handler (no stack traces to clients)
- Registered routers (health, users, admin)

Local dev:  uv run uvicorn app.main:app --reload
Production: gunicorn -k uvicorn.workers.UvicornWorker app.main:app

Middleware execution order (outermost → innermost, i.e. first to see a
request → closest to the route handler):
  CORS → security-headers → request-ID → SlowAPI → Sentry context → handler

In Starlette, the LAST call to add_middleware() becomes the outermost layer.
So middlewares are registered here in the reverse of the execution order
(innermost first, outermost last).

SlowAPI is registered BEFORE RequestIDMiddleware (making it inner) so that:
- RequestID runs first on every inbound request and sets request.state.request_id
  before the rate-limit decorator on the route fires RateLimitExceeded.
- 429 responses flow back out through RequestIDMiddleware (adds X-Request-ID
  header) and then SecurityHeaders, satisfying both correlation and security
  header requirements on rate-limited responses.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.logging_config import configure_logging, get_logger
from app.middleware.error_handler import generic_exception_handler
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.sentry_context import SentryContextMiddleware
from app.observability.sentry import init_sentry
from app.reliability.rate_limit import limiter, rate_limit_exceeded_handler
from app.routers.admin import router as admin_router
from app.routers.admin_chat_quality import router as admin_chat_quality_router
from app.routers.admin_coupons import router as admin_coupons_router
from app.routers.canvas_layout import router as canvas_layout_router
from app.routers.chat import router as chat_router
from app.routers.experiment_activity import router as experiment_activity_router
from app.routers.experiment_attachments import router as experiment_attachments_router
from app.routers.experiment_refine import router as experiment_refine_router
from app.routers.experiment_resources import router as experiment_resources_router
from app.routers.experiment_refine import router as experiment_refine_router
from app.routers.experiments import router as experiments_router
from app.routers.health import router as health_router
from app.routers.launch_kit import router as launch_kit_router
from app.routers.public import router as public_router
from app.routers.search import router as search_router
from app.routers.users import router as users_router
from app.routers.wallet import router as wallet_router
from app.routers.landing_page_v2 import router as landing_page_v2_router

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
    5. Construct the ResearchDispatcher and store on app.state (after DB).

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

    # 5. Research dispatcher (ADR 0009) — must run after init_engine so the
    #    InProcessDispatcher can import AsyncSessionLocal safely.
    from app.dispatchers.factory import (  # noqa: PLC0415
        get_dispatcher,
        get_insight_dispatcher,
        get_landing_page_dispatcher,
        get_launch_kit_dispatcher,
    )

    app.state.dispatcher = get_dispatcher(settings)
    app.state.insight_dispatcher = get_insight_dispatcher(settings)
    launch_kit_dispatcher = get_launch_kit_dispatcher(settings)
    app.state.launch_kit_dispatcher = launch_kit_dispatcher
    app.state.landing_page_dispatcher = get_landing_page_dispatcher(
        settings,
        launch_kit_dispatcher=launch_kit_dispatcher,
    )
    logger.info(
        "research dispatcher initialised",
        dispatcher_mode=settings.dispatcher_mode,
    )

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

# RateLimitExceeded is a subclass of HTTPException. FastAPI dispatches to the
# most-specific registered handler, so this takes precedence over the generic
# Exception handler above and over Starlette's built-in HTTPException handler.
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Make the limiter instance available to SlowAPIMiddleware via app.state.
app.state.limiter = limiter

# ---------------------------------------------------------------------------
# Middleware — registration order matters.
#
# Starlette builds the middleware stack so the LAST add_middleware() call
# becomes the OUTERMOST layer (first to process incoming requests).
# Register innermost → outermost so execution order is:
#   CORS → security-headers → request-ID → SlowAPI → Sentry context → handler
# ---------------------------------------------------------------------------

# 1. Sentry context — innermost; runs closest to the route handler.
app.add_middleware(SentryContextMiddleware)

# 2. SlowAPI — registered before RequestID so RequestID is outer.
#    Execution order: RequestID (outer) → SlowAPI → Sentry → handler.
#    When the rate-limit decorator fires RateLimitExceeded inside the route,
#    SlowAPIMiddleware catches it and returns a 429.  That response then flows
#    back out through RequestID (adds X-Request-ID) and SecurityHeaders.
app.add_middleware(SlowAPIMiddleware)

# 3. Request ID — outer of SlowAPI; sets request_id on every inbound request
#    so request.state.request_id is available when rate_limit_exceeded_handler
#    runs inside the SlowAPI layer.
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
    allow_origin_regex=settings.cors_landing_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(public_router, prefix="", tags=["Public"])
app.include_router(users_router)
app.include_router(search_router)
app.include_router(wallet_router)
app.include_router(landing_page_v2_router)
app.include_router(experiments_router)
app.include_router(launch_kit_router)
app.include_router(canvas_layout_router)
app.include_router(experiment_resources_router)
app.include_router(experiment_attachments_router)
app.include_router(experiment_refine_router)
app.include_router(experiment_activity_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(admin_chat_quality_router)
app.include_router(admin_coupons_router)
