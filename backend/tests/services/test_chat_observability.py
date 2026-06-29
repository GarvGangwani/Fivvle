"""Unit tests for app.services.chat_observability."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import (
    ChatRole,
    ChatTurnKind,
    DispatchTrigger,
    ExperimentStatus,
)
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.cost.category import resolve_cost_category_from_phase
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.services import chat_observability

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _future_updated_at(since: datetime, *, seconds: int = 10) -> datetime:
    """Place seeded rows far in the future so only this test's rows match ``since``."""
    return since + timedelta(days=365, seconds=seconds)


async def _persist_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"chat-obs-{uuid4()}",
        email=f"chat-obs-{uuid4()}@example.com",
        name="Chat Observability User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _persist_thread(db: AsyncSession, user: User) -> ChatThread:
    thread = ChatThread(user_id=user.id, title="obs thread")
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


# ---------------------------------------------------------------------------
# a. refinement_turn_count_distribution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refinement_turn_count_distribution(db_session: AsyncSession) -> None:
    since = datetime.now(timezone.utc)
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    updated_at = _future_updated_at(since)

    for refinement_count in (0, 1, 3):
        exp = Experiment(
            user_id=user.id,
            thread_id=thread.id,
            raw_idea=f"idea-{refinement_count}",
            slug=f"obs-ref-turn-{uuid4().hex[:12]}",
            refinement_count=refinement_count,
        )
        exp.updated_at = updated_at
        db_session.add(exp)

    await db_session.commit()

    result = await chat_observability.refinement_turn_count_distribution(
        db_session, since=since
    )
    assert result == {0: 1, 1: 1, 2: 0, 3: 1}


# ---------------------------------------------------------------------------
# b. user_reply_length_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_reply_length_stats(db_session: AsyncSession) -> None:
    # Unique window to avoid cross-test pollution in shared Postgres.
    base_time = datetime.now(timezone.utc) + timedelta(days=400)
    since = base_time - timedelta(seconds=1)
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)

    messages = [
        (ChatRole.USER, "initial user message", None, base_time),
        (
            ChatRole.ASSISTANT,
            "What audience?",
            ChatTurnKind.REFINEMENT_CLARIFY,
            base_time + timedelta(seconds=1),
        ),
        (
            ChatRole.USER,
            "x" * 50,
            None,
            base_time + timedelta(seconds=2),
        ),
        (
            ChatRole.ASSISTANT,
            "Researching: test",
            ChatTurnKind.REFINEMENT_FINALIZE,
            base_time + timedelta(seconds=3),
        ),
        (
            ChatRole.USER,
            "x" * 40,
            None,
            base_time + timedelta(seconds=4),
        ),
    ]
    for role, content, turn_kind, created_at in messages:
        db_session.add(
            ChatMessage(
                thread_id=thread.id,
                role=role,
                content=content,
                turn_kind=turn_kind,
                created_at=created_at,
            )
        )
    await db_session.commit()

    result = await chat_observability.user_reply_length_stats(db_session, since=since)
    assert result["count"] == 1
    assert result["median"] == 50
    assert result["max"] == 50


# ---------------------------------------------------------------------------
# c. dispatch_to_completion_latency_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_to_completion_latency_stats(db_session: AsyncSession) -> None:
    since = datetime.now(timezone.utc)
    user = await _persist_user(db_session)
    t0 = _future_updated_at(since)
    completion = t0 + timedelta(seconds=120)

    exp = Experiment(
        user_id=user.id,
        raw_idea="latency idea",
        slug=f"obs-latency-{uuid4().hex[:12]}",
        status=ExperimentStatus.RESEARCH_READY,
        dispatch_trigger=DispatchTrigger.AUTO_FIRE,
    )
    exp.updated_at = completion
    db_session.add(exp)
    await db_session.flush()

    db_session.add(
        LLMCall(
            experiment_id=exp.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="planner",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.01"),
            latency_ms=500,
            phase="planner",
            cost_category=resolve_cost_category_from_phase("planner").value,
            called_at=t0,
        )
    )
    db_session.add(
        ValidationReport(
            experiment_id=exp.id,
            raw_report={"executive_summary": "test"},
            generated_at=completion,
        )
    )
    await db_session.commit()

    result = await chat_observability.dispatch_to_completion_latency_stats(
        db_session, since=since
    )
    assert result["count"] == 1
    assert result["median_seconds"] == 120
    assert result["p90_seconds"] == 120


# ---------------------------------------------------------------------------
# d. dispatch_trigger_ratio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_trigger_ratio(db_session: AsyncSession) -> None:
    since = datetime.now(timezone.utc)
    user = await _persist_user(db_session)
    updated_at = _future_updated_at(since)

    for _ in range(3):
        exp = Experiment(
            user_id=user.id,
            raw_idea="auto",
            slug=f"obs-auto-{uuid4().hex[:12]}",
            dispatch_trigger=DispatchTrigger.AUTO_FIRE,
        )
        exp.updated_at = updated_at
        db_session.add(exp)
    for _ in range(2):
        exp = Experiment(
            user_id=user.id,
            raw_idea="confirm",
            slug=f"obs-confirm-{uuid4().hex[:12]}",
            dispatch_trigger=DispatchTrigger.USER_CONFIRM,
        )
        exp.updated_at = updated_at
        db_session.add(exp)

    await db_session.commit()

    result = await chat_observability.dispatch_trigger_ratio(db_session, since=since)
    assert result == {"auto_fire": 3, "user_confirm": 2}


# ---------------------------------------------------------------------------
# e. first_turn_dimension_distribution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_turn_dimension_distribution(db_session: AsyncSession) -> None:
    since = datetime.now(timezone.utc)
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    base_time = _future_updated_at(since)
    dimensions = ("audience", "audience", "scope", "contradiction")

    for idx, dimension in enumerate(dimensions):
        exp = Experiment(
            user_id=user.id,
            thread_id=thread.id,
            raw_idea=f"dim-{idx}",
            slug=f"obs-dim-{uuid4().hex[:12]}",
        )
        db_session.add(exp)
        await db_session.flush()

        db_session.add(
            ChatMessage(
                thread_id=thread.id,
                experiment_id=exp.id,
                role=ChatRole.ASSISTANT,
                content=f"clarify {dimension}?",
                turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
                clarifying_dimension=dimension,
                created_at=base_time + timedelta(seconds=idx),
            )
        )

    await db_session.commit()

    result = await chat_observability.first_turn_dimension_distribution(
        db_session, since=since
    )
    assert result == {"audience": 2, "scope": 1, "contradiction": 1}
