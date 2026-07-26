"""Unit tests for complete_with_tools (Anthropic + Kimi)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.llm_call import LLMCall
from app.llm.client import (
    _parse_anthropic_tool_content,
    _parse_kimi_tool_message,
    complete_with_tools,
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


def test_parse_anthropic_mixed_content_blocks() -> None:
    blocks = [
        SimpleNamespace(type="text", text="Checking metrics. "),
        SimpleNamespace(
            type="tool_use",
            id="toolu_1",
            name="get_metrics_summary",
            input={},
        ),
        SimpleNamespace(type="text", text="One moment."),
    ]
    text, tool_uses, assistant_turn = _parse_anthropic_tool_content(blocks)
    assert text == "Checking metrics. One moment."
    assert len(tool_uses) == 1
    assert tool_uses[0].name == "get_metrics_summary"
    assert assistant_turn["role"] == "assistant"
    assert assistant_turn["content"][1]["type"] == "tool_use"
    assert assistant_turn["content"][1]["id"] == "toolu_1"


def test_parse_kimi_tool_calls_json_arguments() -> None:
    message = SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(
                    name="get_metrics_summary",
                    arguments='{"unused": true}',
                ),
            ),
            SimpleNamespace(
                id="call_2",
                function=SimpleNamespace(
                    name="get_landing_status",
                    arguments="",
                ),
            ),
            SimpleNamespace(
                id="call_3",
                function=SimpleNamespace(
                    name="get_report_summary",
                    arguments="not-json{",
                ),
            ),
        ],
    )
    text, tool_uses, assistant_turn = _parse_kimi_tool_message(message)
    assert text is None
    assert tool_uses[0].input == {"unused": True}
    assert tool_uses[1].input == {}
    assert tool_uses[2].input == {}
    assert assistant_turn["role"] == "assistant"
    assert len(assistant_turn["tool_calls"]) == 3
    assert assistant_turn["tool_calls"][0]["function"]["name"] == "get_metrics_summary"


@pytest.mark.asyncio
async def test_complete_with_tools_rejects_unsupported_provider(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(NotImplementedError, match="anthropic and kimi only"):
        await complete_with_tools(
            db_session,
            provider="groq",  # type: ignore[arg-type]
            model="llama-3.3-70b-versatile",
            prompt_name="universal_chat_v2",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )


@pytest.mark.asyncio
async def test_complete_with_tools_logs_and_parses_anthropic(
    db_session: AsyncSession,
) -> None:
    fake_response = SimpleNamespace(
        id="msg_tools_1",
        content=[
            SimpleNamespace(type="text", text="Looking that up."),
            SimpleNamespace(
                type="tool_use",
                id="toolu_abc",
                name="get_landing_status",
                input={},
            ),
        ],
        usage=SimpleNamespace(input_tokens=20, output_tokens=8),
    )

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    with patch("app.llm.client._anthropic_client", fake_client):
        result = await complete_with_tools(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt_name="universal_chat_v2",
            system="You are a coach.",
            messages=[{"role": "user", "content": "Is my page live?"}],
            tools=[
                {
                    "name": "get_landing_status",
                    "description": "Landing status",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            experiment_id=None,
            phase="universal_chat",
        )
        await db_session.commit()

    assert result.assistant_text == "Looking that up."
    assert len(result.tool_uses) == 1
    assert result.assistant_turn["role"] == "assistant"
    assert result.llm_result.prompt_tokens == 20

    row = (
        await db_session.execute(
            select(LLMCall).where(LLMCall.request_id == "msg_tools_1")
        )
    ).scalar_one()
    assert row.prompt_name == "universal_chat_v2"
    assert row.phase == "universal_chat"
    assert row.provider == "anthropic"
    await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_complete_with_tools_logs_and_parses_kimi(
    db_session: AsyncSession,
) -> None:
    fake_message = SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call_abc",
                function=SimpleNamespace(
                    name="get_landing_status",
                    arguments="{}",
                ),
            )
        ],
    )
    fake_response = SimpleNamespace(
        id="kimi_tools_1",
        choices=[SimpleNamespace(message=fake_message)],
        usage=SimpleNamespace(prompt_tokens=15, completion_tokens=6),
    )

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("app.llm.client._kimi_client", fake_client):
        result = await complete_with_tools(
            db_session,
            provider="kimi",
            model="kimi-k2.6",
            prompt_name="universal_chat_v2",
            system="You are a coach.",
            messages=[{"role": "user", "content": "Is my page live?"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_landing_status",
                        "description": "Landing status",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            experiment_id=None,
            phase="universal_chat",
        )
        await db_session.commit()

    assert result.tool_uses[0].name == "get_landing_status"
    assert result.tool_uses[0].input == {}
    assert result.assistant_turn["tool_calls"][0]["id"] == "call_abc"
    create_kwargs = fake_client.chat.completions.create.await_args.kwargs
    assert create_kwargs["temperature"] == 0.6
    assert create_kwargs["extra_body"] == {"thinking": {"type": "disabled"}}

    row = (
        await db_session.execute(
            select(LLMCall).where(LLMCall.request_id == "kimi_tools_1")
        )
    ).scalar_one()
    assert row.provider == "kimi"
    assert row.phase == "universal_chat"
    await db_session.delete(row)
    await db_session.commit()
