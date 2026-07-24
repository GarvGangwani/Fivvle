"""Unit tests for app.services.universal_chat_service and project context.

LLM calls are mocked; a real async DB session is used (mirrors evidence chat tests).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.llm.prompts.universal_chat import (
    PROMPT_NAME_UNIVERSAL_CHAT,
    build_universal_chat_user_prompt,
)
from app.schemas.chat import ChatMessageItem
from app.services.experiment_project_context import (
    current_act_for_status,
    get_experiment_project_context,
)
from app.services.universal_chat_service import (
    UniversalChatNotFound,
    UniversalChatUnavailable,
    list_universal_chat_messages,
    send_universal_chat_message,
)

_LLM_PATCH_TARGET = "app.services.universal_chat_service.llm_client.complete"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _fake_llm_result(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


def _refined_idea_dict() -> dict[str, Any]:
    return {
        "refined_one_liner": "A Slack app that answers HR policy questions for employees.",
        "target_audience": "HR teams at 200-person startups fielding repetitive policy questions.",
        "value_proposition": "Cuts repetitive HR question volume so teams focus on real cases.",
        "risks": [
            "Do existing Slack HR bots already own this workflow for most buyers?",
            "Is the policy content fresh enough to trust without manual review?",
            "Can pricing support a venture-scale business at SMB seat counts?",
        ],
        "project_name": "PolicyPal",
        "headline": "Policy answers in Slack, instantly",
        "subheadline": "Your team gets trusted HR answers without pinging people.",
        "cta_text": "Join the waitlist",
    }


async def _seed_user_and_experiment(
    db: AsyncSession,
    *,
    status: ExperimentStatus = ExperimentStatus.SPARK,
    raw_idea: str = "An app that helps founders validate ideas faster.",
    refined_idea: dict[str, Any] | None = None,
) -> tuple[User, Experiment]:
    user = User(
        firebase_uid=f"univ-svc-{uuid4()}",
        email=f"univ-{uuid4()}@example.com",
        name="Universal Test User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    experiment = Experiment(
        user_id=user.id,
        name="Universal Chat Project",
        raw_idea=raw_idea,
        refined_idea=refined_idea,
        status=status,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return user, experiment


async def _seed_other_user(db: AsyncSession) -> User:
    other = User(
        firebase_uid=f"univ-other-{uuid4()}",
        email=f"univ-other-{uuid4()}@example.com",
        name="Other User",
    )
    db.add(other)
    await db.commit()
    await db.refresh(other)
    return other


@pytest.mark.asyncio
async def test_send_creates_thread_on_first_call(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = _fake_llm_result(
            "You're in Spark. Capture your idea clearly, then move to Refine."
        )
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "Where am I in the journey?"
        )

    await db_session.refresh(experiment)
    assert experiment.universal_thread_id == result.thread_id
    assert result.user_message.role == ChatRole.USER
    assert result.assistant_message.role == ChatRole.ASSISTANT
    assert result.user_message.turn_kind == ChatTurnKind.UNIVERSAL_CHAT
    assert result.assistant_message.turn_kind == ChatTurnKind.UNIVERSAL_CHAT
    assert result.assistant_message.parent_message_id == result.user_message.id

    mock_complete.assert_awaited_once()
    kwargs = mock_complete.await_args.kwargs
    assert kwargs["prompt_name"] == PROMPT_NAME_UNIVERSAL_CHAT
    assert kwargs["phase"] == "universal_chat"
    assert "raw_idea" in kwargs["user"]
    assert "current_act: spark" in kwargs["user"]


@pytest.mark.asyncio
async def test_send_reuses_thread_on_second_call(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = _fake_llm_result("First reply.")
        first = await send_universal_chat_message(
            db_session, user, experiment.id, "Hello"
        )
        mock_complete.return_value = _fake_llm_result("Second reply.")
        second = await send_universal_chat_message(
            db_session, user, experiment.id, "What next?"
        )

    assert first.thread_id == second.thread_id
    thread_count = await db_session.scalar(
        select(func.count())
        .select_from(ChatThread)
        .where(ChatThread.user_id == user.id)
    )
    assert thread_count == 1

    listed = await list_universal_chat_messages(db_session, user, experiment.id)
    assert len(listed.messages) == 4
    assert [m.content for m in listed.messages] == [
        "Hello",
        "First reply.",
        "What next?",
        "Second reply.",
    ]
    assert listed.active_leaf_message_id == second.assistant_message.id


@pytest.mark.asyncio
async def test_send_rejects_wrong_owner(db_session: AsyncSession) -> None:
    owner, experiment = await _seed_user_and_experiment(db_session)
    other = await _seed_other_user(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock):
        with pytest.raises(UniversalChatNotFound):
            await send_universal_chat_message(
                db_session, other, experiment.id, "Hi"
            )
    assert owner.id != other.id


@pytest.mark.asyncio
async def test_send_rejects_archived(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.ARCHIVED
    )
    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock):
        with pytest.raises(UniversalChatUnavailable):
            await send_universal_chat_message(
                db_session, user, experiment.id, "Hi"
            )


@pytest.mark.asyncio
async def test_list_empty_without_thread(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(db_session)
    result = await list_universal_chat_messages(db_session, user, experiment.id)
    assert result.thread_id is None
    assert result.messages == []
    assert result.active_leaf_message_id is None


@pytest.mark.asyncio
async def test_list_serializes_tool_rows(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(db_session)
    thread = ChatThread(user_id=user.id, title="Universal chat fixture")
    db_session.add(thread)
    await db_session.flush()
    experiment.universal_thread_id = thread.id

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="Run a status check",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=None,
    )
    db_session.add(user_msg)
    await db_session.flush()

    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="I'll check your project status.",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=user_msg.id,
    )
    db_session.add(assistant_msg)
    await db_session.flush()

    tool_call = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.TOOL_CALL,
        content="Called: get_project_status",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=assistant_msg.id,
        tool_payload={"tool_name": "get_project_status", "arguments": {}},
    )
    db_session.add(tool_call)
    await db_session.flush()

    tool_result = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.TOOL_RESULT,
        content="Result received",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=tool_call.id,
        tool_payload={
            "tool_name": "get_project_status",
            "result": {"current_act": "spark"},
        },
    )
    db_session.add(tool_result)
    await db_session.flush()
    thread.active_leaf_message_id = tool_result.id
    await db_session.commit()

    listed = await list_universal_chat_messages(db_session, user, experiment.id)
    assert len(listed.messages) == 4
    roles = [m.role for m in listed.messages]
    assert roles == [
        ChatRole.USER,
        ChatRole.ASSISTANT,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
    ]

    items = [ChatMessageItem.from_orm_message(m) for m in listed.messages]
    assert items[2].tool_payload == {
        "tool_name": "get_project_status",
        "arguments": {},
    }
    assert items[3].tool_payload == {
        "tool_name": "get_project_status",
        "result": {"current_act": "spark"},
    }
    assert items[2].content == "Called: get_project_status"
    assert items[3].content == "Result received"


@pytest.mark.asyncio
async def test_project_context_act_mapping(db_session: AsyncSession) -> None:
    assert current_act_for_status(ExperimentStatus.SPARK) == "spark"
    assert current_act_for_status(ExperimentStatus.REFINING) == "refine"
    assert current_act_for_status(ExperimentStatus.RESEARCH_READY) == "evidence"
    assert current_act_for_status(ExperimentStatus.LANDING_LIVE) == "launch"
    assert current_act_for_status(ExperimentStatus.INSIGHT_READY) == "signal"
    assert current_act_for_status(ExperimentStatus.ARCHIVED) == "archived"

    user, experiment = await _seed_user_and_experiment(
        db_session,
        status=ExperimentStatus.REFINED,
        refined_idea=_refined_idea_dict(),
    )
    ctx = await get_experiment_project_context(db_session, experiment)
    block = ctx.to_prompt_block()
    assert "current_act: refine" in block
    assert "refined_one_liner:" in block
    assert "has_validation_report: false" in block
    assert "has_landing_page: false" in block
    assert "has_insight_report: false" in block
    assert user.id == experiment.user_id


def test_prompt_assembly_snapshots() -> None:
    """Eyeball fixtures: what the LLM sees for a few experiment states."""
    spark_ctx = (
        "status: SPARK\n"
        "current_act: spark\n"
        "project_name: Universal Chat Project\n"
        "raw_idea: An app that helps founders validate ideas faster.\n"
        "has_validation_report: false\n"
        "has_landing_page: false\n"
        "has_insight_report: false"
    )
    spark_prompt = build_universal_chat_user_prompt(
        project_context=spark_ctx,
        chat_history="",
        user_message="What should I do next?",
    )
    assert "<project_context>" in spark_prompt
    assert "current_act: spark" in spark_prompt
    assert "What should I do next?" in spark_prompt

    landing_ctx = (
        "status: LANDING_LIVE\n"
        "current_act: launch\n"
        "project_name: PolicyPal\n"
        "refined_one_liner: A Slack app that answers HR policy questions.\n"
        "has_validation_report: true\n"
        "has_landing_page: true\n"
        "has_insight_report: false"
    )
    landing_prompt = build_universal_chat_user_prompt(
        project_context=landing_ctx,
        chat_history="[user]: How is traffic?\n[assistant]: Open Signal for live metrics.",
        user_message="Is my page live?",
    )
    assert "current_act: launch" in landing_prompt
    assert "has_landing_page: true" in landing_prompt
    assert "[user]: How is traffic?" in landing_prompt
