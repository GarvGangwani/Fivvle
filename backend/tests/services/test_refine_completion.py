"""Tests for the founder's explicit refine-completion stamp."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.services.experiment_project_context import get_experiment_project_context
from app.services.refine_session_service import mark_refine_complete


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _seed_experiment(db: AsyncSession) -> Experiment:
    user = User(
        firebase_uid=f"fb-{uuid4()}",
        email=f"{uuid4()}@example.com",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        raw_idea="A tool that turns customer calls into a weekly product digest.",
        name="Refine Completion Test",
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


@pytest.mark.asyncio
async def test_mark_refine_complete_is_write_once(db_session: AsyncSession) -> None:
    experiment = await _seed_experiment(db_session)
    assert experiment.refine_completed_at is None

    await mark_refine_complete(db_session, experiment)
    first_stamp = experiment.refine_completed_at
    assert first_stamp is not None

    # Second call is a no-op: the founder can tap again, or the request can be
    # retried, without moving the stamp.
    await mark_refine_complete(db_session, experiment)
    assert experiment.refine_completed_at == first_stamp

    await db_session.refresh(experiment)
    assert experiment.refine_completed_at == first_stamp


@pytest.mark.asyncio
async def test_project_context_exposes_refine_completed(
    db_session: AsyncSession,
) -> None:
    experiment = await _seed_experiment(db_session)

    before = await get_experiment_project_context(db_session, experiment)
    assert before.refine_completed is False
    assert "refine_completed: false" in before.to_prompt_block()

    await mark_refine_complete(db_session, experiment)

    after = await get_experiment_project_context(db_session, experiment)
    assert after.refine_completed is True
    assert "refine_completed: true" in after.to_prompt_block()


@pytest.mark.asyncio
async def test_refined_idea_alone_does_not_complete_refine(
    db_session: AsyncSession,
) -> None:
    """Completion is an explicit founder action, never derived from the idea."""
    experiment = await _seed_experiment(db_session)
    experiment.refined_idea = {
        "refined_one_liner": "Turns support calls into a weekly product digest.",
        "target_audience": "Heads of product at 20-100 person B2B SaaS companies.",
        "value_proposition": "Surfaces what customers actually asked for, weekly.",
        "risks": [
            "Do product teams already read call transcripts themselves?",
            "Will sales let a tool sit on recorded customer calls?",
            "Is weekly the right cadence, or does it need to be real time?",
        ],
        "headline": "Your calls, summarized",
        "subheadline": "One digest a week.",
        "cta_text": "Join the waitlist",
    }
    experiment.refined_idea_version = 3
    await db_session.commit()
    await db_session.refresh(experiment)

    context = await get_experiment_project_context(db_session, experiment)
    assert context.refine_completed is False
    assert experiment.refine_completed_at is None
