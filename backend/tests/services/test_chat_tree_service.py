"""Tests for chat message tree helpers and branching retry/edit."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.schemas.refinement import ClarifyingQuestion, RefinementTurnDecision
from app.services.chat_service import retry_assistant_message
from app.services.chat_tree_service import (
    get_active_branch,
    get_leaf_of_branch,
    get_siblings,
    set_active_leaf,
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


async def _user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"tree-{uuid4()}",
        email=f"tree-{uuid4()}@example.com",
        name="Tree Test",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _thread(db: AsyncSession, user: User) -> ChatThread:
    thread = ChatThread(user_id=user.id, title="Tree thread")
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


@pytest.mark.asyncio
async def test_get_active_branch_walks_parent_chain(db_session: AsyncSession) -> None:
    user = await _user(db_session)
    thread = await _thread(db_session, user)

    root = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="opener",
        parent_message_id=None,
    )
    db_session.add(root)
    await db_session.flush()

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="answer",
        parent_message_id=root.id,
    )
    db_session.add(user_msg)
    await db_session.flush()

    assistant = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="follow-up",
        parent_message_id=user_msg.id,
        turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
    )
    db_session.add(assistant)
    await db_session.flush()

    thread.active_leaf_message_id = assistant.id
    await db_session.commit()

    branch = await get_active_branch(db_session, thread.id)
    assert [m.content for m in branch] == ["opener", "answer", "follow-up"]


@pytest.mark.asyncio
async def test_siblings_and_leaf_navigation(db_session: AsyncSession) -> None:
    user = await _user(db_session)
    thread = await _thread(db_session, user)

    parent = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="q",
        parent_message_id=None,
    )
    db_session.add(parent)
    await db_session.flush()

    a1 = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="a1",
        parent_message_id=parent.id,
        turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
    )
    a2 = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="a2",
        parent_message_id=parent.id,
        turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
    )
    db_session.add_all([a1, a2])
    await db_session.flush()

    child = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="next",
        parent_message_id=a2.id,
    )
    db_session.add(child)
    await db_session.flush()
    thread.active_leaf_message_id = child.id
    await db_session.commit()

    siblings = await get_siblings(db_session, a1.id)
    assert [s.content for s in siblings] == ["a1", "a2"]

    leaf = await get_leaf_of_branch(db_session, a2.id)
    assert leaf.content == "next"

    await set_active_leaf(db_session, thread.id, a1.id)
    await db_session.commit()
    await db_session.refresh(thread)
    assert thread.active_leaf_message_id == a1.id


@pytest.mark.asyncio
@patch("app.services.refinement_service.run_turn", new_callable=AsyncMock)
async def test_retry_creates_sibling_not_delete(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = RefinementTurnDecision(
        decision="clarify",
        assistant_message="Retried reply",
        clarifying_dimension="audience",
        clarifying_questions=[
            ClarifyingQuestion(
                question="Who?",
                selection_mode="multiple",
                options=["A", "B", "C"],
            )
        ],
        reasoning_trace="retry",
    )

    user = await _user(db_session)
    thread = await _thread(db_session, user)
    experiment = Experiment(
        user_id=user.id,
        thread_id=thread.id,
        raw_idea="An idea about coaches and Excel.",
        status=ExperimentStatus.REFINING,
        refinement_count=1,
    )
    db_session.add(experiment)
    await db_session.flush()

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="My answer",
        experiment_id=experiment.id,
        parent_message_id=None,
    )
    db_session.add(user_msg)
    await db_session.flush()

    original = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="Original reply",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
        parent_message_id=user_msg.id,
    )
    db_session.add(original)
    await db_session.flush()
    thread.active_leaf_message_id = original.id
    await db_session.commit()

    class _Disp:
        async def dispatch(self, experiment_id: object) -> None:
            return None

    result = await retry_assistant_message(
        db_session,
        user,
        experiment.id,
        original.id,
        _Disp(),
    )

    assert result.assistant_message == "Retried reply"
    assert result.message_id != original.id

    rows = list(
        (
            await db_session.execute(
                select(ChatMessage).where(ChatMessage.thread_id == thread.id)
            )
        )
        .scalars()
        .all()
    )
    assistants = [r for r in rows if r.role == ChatRole.ASSISTANT]
    assert len(assistants) == 2
    assert all(a.parent_message_id == user_msg.id for a in assistants)

    await db_session.refresh(thread)
    assert thread.active_leaf_message_id == result.message_id
    assert await db_session.get(ChatMessage, original.id) is not None
