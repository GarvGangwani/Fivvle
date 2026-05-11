"""
Health check endpoints.

Two endpoints as specified in AGENTS.md and .cursorrules:
- GET /health  — liveness probe (no dependencies, always fast)
- GET /health/ready — readiness probe (checks Firebase Admin SDK state)

These endpoints are intentionally synchronous — they perform no I/O.
"""

from fastapi import APIRouter, HTTPException

from app.auth import firebase

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    """Liveness probe.

    Returns 200 immediately with no dependency checks.  The orchestrator
    (Cloud Run) uses this to determine whether the container process is alive.
    """
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> dict[str, object]:
    """Readiness probe.

    Checks that the Firebase Admin SDK has been initialized.  Additional
    checks (e.g., DB connectivity) are added in build step 2 when SQLAlchemy
    is wired.

    Returns:
        200 with check results when all checks pass.

    Raises:
        HTTPException: 503 if any required dependency is not ready.
    """
    firebase_ok = firebase.is_initialized()

    if not firebase_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": {"firebase": "not_initialized"},
            },
        )

    return {
        "status": "ready",
        "checks": {"firebase": "ok"},
    }
