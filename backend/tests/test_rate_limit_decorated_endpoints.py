"""Regression tests: rate-limit decorators on real app endpoints.

These tests verify that adding @limiter.limit(...) to existing endpoints:
  - Did not break happy-path behaviour (endpoints still return 200).
  - That X-RateLimit-* headers are present on successful responses
    (slowapi injects these when headers_enabled=True on the limiter).

We do NOT exhaust the real 60/minute limit here — that would require 60
requests per test and is unnecessarily slow.  The full rate-limit mechanics
are tested in test_rate_limit.py using tiny in-process apps with low limits.

Auth fixtures (mock_firebase, client) are defined in tests/conftest.py and
are available automatically via pytest's fixture discovery.

The admin endpoints require an admin User row in Postgres.  We reuse the
_create_admin_user helper from test_admin_cost.py rather than duplicating it.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.user import User
from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID


# ---------------------------------------------------------------------------
# Standalone DB session fixture (same pattern as test_admin_cost.py)
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh async session per test; independent of FastAPI lifespan."""
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helper — insert admin user so auth resolves correctly
# ---------------------------------------------------------------------------


async def _create_admin_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=FAKE_FIREBASE_UID,
        email=FAKE_EMAIL,
        name="Rate Limit Test Admin",
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# 1. POST /users/sync still works with the rate-limit decorator
# ---------------------------------------------------------------------------


def test_users_sync_still_returns_200_with_rate_limit_decorator(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Decorator did not break the sync endpoint happy path."""
    resp = client.post(
        "/users/sync",
        json={"name": "Rate Limit Smoke Test"},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. GET /admin/cost/daily still works with the rate-limit decorator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_daily_cost_still_returns_200_with_rate_limit_decorator(
    client: TestClient,
    mock_firebase: None,
    db_session: AsyncSession,
) -> None:
    """Decorator did not break the admin daily-cost endpoint happy path."""
    await _create_admin_user(db_session)
    resp = client.get(
        "/admin/cost/daily",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. X-RateLimit-* headers are present on successful decorated responses
# ---------------------------------------------------------------------------


def test_rate_limit_headers_present_on_users_sync_200(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """slowapi injects X-RateLimit-* headers when headers_enabled=True."""
    resp = client.post(
        "/users/sync",
        json={},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert resp.status_code == 200
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers
    assert "x-ratelimit-reset" in resp.headers
