"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.

Module-level singletons (_engine, _sessionmaker) are initialized once
during application startup via init_engine() and disposed on shutdown
via dispose_engine(). The lifespan handler in app.main wires these in
build step 2C (after the first Alembic migration exists).

Public surface:
    init_engine(settings)     — startup hook
    dispose_engine()          — shutdown hook
    get_session()             — FastAPI Depends() dependency
    check_db_health()         — readiness probe helper (wired in 2C)
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.logging_config import get_logger

_logger = get_logger(__name__)

# Module-level engine and sessionmaker — initialized on first call to init_engine().
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> None:
    """Initialize the async engine and sessionmaker.

    Idempotent — safe to call multiple times (subsequent calls are no-ops).
    Called once during application startup in the lifespan handler.

    Pool tuning rationale:
    - pool_size=5 / max_overflow=10: conservative baseline for Cloud Run.
      Cloud Run scales horizontally; each instance holds its own pool.
    - pool_pre_ping=True: Cloud SQL drops idle connections after ~10 minutes;
      pre-ping validates the connection before handing it to a handler.
    - pool_recycle=1800: recycle connections every 30 minutes to prevent
      accumulation of long-lived connections that GCP may drop silently.
    - echo=False: never log SQL in production (AGENTS.md "Logging hygiene").
    """
    global _engine, _sessionmaker  # noqa: PLW0603

    if _engine is not None:
        return

    _engine = create_async_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
    )

    _sessionmaker = async_sessionmaker(
        bind=_engine,
        expire_on_commit=False,  # objects usable after commit without re-fetch
        autoflush=False,
        autocommit=False,
    )

    _logger.info("db engine initialized")


async def dispose_engine() -> None:
    """Close the async engine and all pooled connections.

    Called during application shutdown in the lifespan handler.
    Idempotent — safe to call when engine was never initialized.
    """
    global _engine, _sessionmaker  # noqa: PLW0603

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        _logger.info("db engine disposed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an AsyncSession per request.

    Commits on successful handler return; rolls back on any exception.
    The rollback ensures connection pool integrity even when handlers raise.

    Usage in route handlers:
        async def my_route(db: Annotated[AsyncSession, Depends(get_session)]):
            ...
    """
    if _sessionmaker is None:
        raise RuntimeError(
            "DB sessionmaker is not initialized. "
            "Did init_engine() run in the lifespan?"
        )

    async with _sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_health() -> bool:
    """Verify the DB is reachable. Used by /health/ready (wired in build step 2C).

    Runs a trivial SELECT 1 with asyncpg's default connect timeout.
    Returns True on success. Returns False on any failure — readiness
    probes must never raise, only return healthy/unhealthy.
    """
    if _engine is None:
        return False

    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        _logger.warning("db health check failed", error=str(exc))
        return False
