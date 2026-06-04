"""HTTP integration tests for admin chat-quality observability endpoints."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import DispatchTrigger
from app.db.models.experiment import Experiment
from app.db.models.user import User
from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _create_admin_user(db_session: AsyncSession) -> User:
    user = User(
        firebase_uid=FAKE_FIREBASE_UID,
        email=FAKE_EMAIL,
        name="Admin User",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def test_refinement_turns_without_auth_returns_401(client: TestClient) -> None:
    response = client.get("/admin/chat-quality/refinement-turns")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refinement_turns_with_auth_and_since_returns_200(
    client: TestClient,
    mock_firebase: None,
    db_session: AsyncSession,
) -> None:
    await _create_admin_user(db_session)

    response = client.get(
        "/admin/chat-quality/refinement-turns",
        params={"since": "2026-01-01T00:00:00Z"},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "distribution" in body
    assert isinstance(body["distribution"], dict)
    for key in ("0", "1", "2", "3"):
        assert key in body["distribution"]
        assert isinstance(body["distribution"][key], int)


@pytest.mark.asyncio
async def test_dispatch_triggers_with_auth_returns_expected_keys(
    client: TestClient,
    mock_firebase: None,
    db_session: AsyncSession,
) -> None:
    user = await _create_admin_user(db_session)
    marker = datetime.now(timezone.utc)

    for _ in range(2):
        exp = Experiment(
            user_id=user.id,
            raw_idea="auto fire",
            slug=f"admin-obs-auto-{uuid4().hex[:12]}",
            dispatch_trigger=DispatchTrigger.AUTO_FIRE,
        )
        exp.updated_at = marker
        db_session.add(exp)

    await db_session.commit()

    response = client.get(
        "/admin/chat-quality/dispatch-triggers",
        params={"since": marker.isoformat()},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"user_confirm", "auto_fire"}
    assert body["auto_fire"] >= 2
    assert isinstance(body["user_confirm"], int)
