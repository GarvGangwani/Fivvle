"""
Smoke test for the /health liveness endpoint.

Scope (build step 1): only the liveness endpoint is tested here.
/health/ready requires Firebase Admin SDK initialization with a real service
account file — a mocked version is added in build step 3.

Run:
    uv run pytest tests/test_health.py -v
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_liveness_returns_200_ok() -> None:
    """GET /health must return 200 with body {"status": "ok"}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
