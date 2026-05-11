"""
Health check endpoints.

Two endpoints as specified in AGENTS.md and .cursorrules:
- GET /health       — liveness probe (no dependencies, always fast)
- GET /health/ready — readiness probe (checks Firebase + DB connectivity)
"""

from fastapi import APIRouter, HTTPException

from app.auth.firebase import is_initialized as firebase_is_initialized
from app.db.session import check_db_health

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Liveness probe.

    Returns 200 immediately with no dependency checks. The orchestrator
    (Cloud Run) uses this to determine whether the container process is alive.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, object]:
    """Readiness probe.

    Checks:
    - Firebase Admin SDK was initialized at startup.
    - Postgres is accepting connections (SELECT 1 succeeds).

    Returns 200 with both check results when all pass.
    Returns 503 with details when any check fails so the orchestrator
    withholds traffic until the instance is genuinely ready.
    """
    checks = {
        "firebase": "ok" if firebase_is_initialized() else "not_initialized",
        "database": "ok" if await check_db_health() else "unreachable",
    }

    if all(v == "ok" for v in checks.values()):
        return {"status": "ready", "checks": checks}

    raise HTTPException(
        status_code=503,
        detail={"status": "not_ready", "checks": checks},
    )
