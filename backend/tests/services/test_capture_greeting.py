"""Tests for pre-capture greeting copy + seeding."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ChatRole
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.services.capture_greeting_service import (
    CaptureGreetingError,
    build_capture_greeting_text,
    ensure_capture_greeting,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def test_greeting_uses_experiment_name_when_present() -> None:
    text = build_capture_greeting_text(project_name="Orbitly")
    assert "Orbitly" in text
    assert "exactly what Orbitly is" in text


def test_greeting_falls_back_when_name_missing() -> None:
    text = build_capture_greeting_text(project_name=None)
    assert "Let's start with your idea" in text
    text2 = build_capture_greeting_text(project_name="   ")
    assert "Let's start with your idea" in text2


async def _seed(db: AsyncSession, *, name: str = "Named Project") -> tuple[User, Experiment]:
    user = User(
        firebase_uid=f"fb-{uuid4()}",
        email=f"{uuid4()}@example.com",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(user_id=user.id, raw_idea="", name=name)
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    await db.refresh(user)
    return user, experiment


@pytest.mark.asyncio
async def test_ensure_capture_greeting_seeds_once(db_session: AsyncSession) -> None:
    user, experiment = await _seed(db_session, name="Pulseboard")
    msg, created = await ensure_capture_greeting(
        db_session, experiment=experiment, user=user
    )
    assert created is True
    assert msg.role == ChatRole.ASSISTANT
    assert "Pulseboard" in (msg.content or "")
    assert msg.metadata_json is not None
    assert msg.metadata_json.get("capture_greeting") is True

    msg2, created2 = await ensure_capture_greeting(
        db_session, experiment=experiment, user=user
    )
    assert created2 is False
    assert msg2.id == msg.id


@pytest.mark.asyncio
async def test_ensure_capture_greeting_rejects_after_capture(
    db_session: AsyncSession,
) -> None:
    user, experiment = await _seed(db_session)
    experiment.original_idea = "Already sealed"
    await db_session.commit()
    await db_session.refresh(experiment)

    with pytest.raises(CaptureGreetingError) as exc:
        await ensure_capture_greeting(db_session, experiment=experiment, user=user)
    assert exc.value.status_code == 409
