"""Unit tests for app.services.universal_chat_service and project context.

LLM calls are mocked; a real async DB session is used (mirrors evidence chat tests).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
import json
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import (
    ChatRole,
    ChatTurnKind,
    ExperimentStatus,
    LandingCtaType,
    LandingDensity,
)
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.db.models.waitlist_signup import WaitlistSignup
from app.llm.client import LLMResult, ToolsLLMResult, ToolUseRequest
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
    _history_for_prompt,
    list_universal_chat_messages,
    send_universal_chat_message,
)
from app.services.universal_chat_tools import execute_tool, get_tool_schemas

_LLM_PATCH_TARGET = "app.services.universal_chat_service.llm_client.complete_with_tools"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _patch_tools_provider(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "universal_chat_tools_provider", provider)
    if provider == "kimi":
        monkeypatch.setattr(settings, "universal_chat_tools_model", "kimi-k2.6")
    else:
        monkeypatch.setattr(settings, "universal_chat_tools_model", "claude-sonnet-4-6")
    monkeypatch.setattr(settings, "universal_chat_tools_fallback_provider", "anthropic")
    monkeypatch.setattr(
        settings, "universal_chat_tools_fallback_model", "claude-sonnet-4-6"
    )


def _llm_meta(*, text: str = "", provider: str = "anthropic") -> LLMResult:
    model = "kimi-k2.6" if provider == "kimi" else "claude-sonnet-4-6"
    return LLMResult(
        text=text,
        provider=provider,
        model=model,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=Decimal("0.001"),
        latency_ms=50,
    )


def _tools_result(
    *,
    text: str | None = None,
    tool_uses: list[ToolUseRequest] | None = None,
    provider: str = "anthropic",
) -> ToolsLLMResult:
    uses = tool_uses or []
    if provider == "kimi":
        tool_calls = [
            {
                "id": use.id,
                "type": "function",
                "function": {
                    "name": use.name,
                    "arguments": json.dumps(use.input),
                },
            }
            for use in uses
        ]
        assistant_turn: dict[str, Any] = {
            "role": "assistant",
            "content": text,
        }
        if tool_calls:
            assistant_turn["tool_calls"] = tool_calls
    else:
        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        for use in uses:
            content.append(
                {
                    "type": "tool_use",
                    "id": use.id,
                    "name": use.name,
                    "input": use.input,
                }
            )
        assistant_turn = {"role": "assistant", "content": content}
    return ToolsLLMResult(
        assistant_text=text,
        tool_uses=uses,
        assistant_turn=assistant_turn,
        llm_result=_llm_meta(text=text or "", provider=provider),
    )


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
async def test_send_creates_thread_on_first_call(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = _tools_result(
            text="You're in Spark. Capture your idea clearly, then move to Refine.",
            provider="kimi",
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
    assert [m.role for m in result.messages] == [ChatRole.USER, ChatRole.ASSISTANT]

    mock_complete.assert_awaited_once()
    kwargs = mock_complete.await_args.kwargs
    assert kwargs["prompt_name"] == PROMPT_NAME_UNIVERSAL_CHAT
    assert kwargs["phase"] == "universal_chat"
    assert kwargs["provider"] == "kimi"
    assert "raw_idea" in kwargs["messages"][0]["content"]
    assert "current_act: spark" in kwargs["messages"][0]["content"]
    assert kwargs["tools"]  # schemas present on first (non-cap) call


@pytest.mark.asyncio
async def test_send_reuses_thread_on_second_call(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = _tools_result(text="First reply.")
        first = await send_universal_chat_message(
            db_session, user, experiment.id, "Hello"
        )
        mock_complete.return_value = _tools_result(text="Second reply.")
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
@pytest.mark.parametrize("provider", ["kimi", "anthropic"])
async def test_send_tool_loop_persists_linear_tool_rows(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    _patch_tools_provider(monkeypatch, provider)
    user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.LANDING_LIVE
    )
    landing = LandingPage(
        experiment_id=experiment.id,
        slug=f"univ-{uuid4().hex[:10]}",
        template_id="minimal",
        palette_id="default",
        font_pair_id="sans",
        density=LandingDensity.ROOMY,
        headline="Try PolicyPal",
        subheadline="HR answers in Slack",
        problem_desc="Repetitive HR questions clog Slack.",
        solution_desc="Instant policy answers in Slack.",
        cta_text="Join the waitlist",
        cta_type=LandingCtaType.WAITLIST,
        live_at=datetime.now(UTC),
    )
    db_session.add(landing)
    db_session.add(
        PageView(experiment_id=experiment.id, source_tag="twitter")
    )
    db_session.add(
        PageView(experiment_id=experiment.id, source_tag="twitter")
    )
    db_session.add(
        WaitlistSignup(
            experiment_id=experiment.id,
            email="a@example.com",
            source_tag="twitter",
        )
    )
    await db_session.commit()

    tool_then_text = [
        _tools_result(
            text=None,
            tool_uses=[
                ToolUseRequest(
                    id="toolu_metrics_1",
                    name="get_metrics_summary",
                    input={},
                )
            ],
            provider=provider,
        ),
        _tools_result(
            text="You have 2 page views and 1 signup, mostly from twitter.",
            provider=provider,
        ),
    ]

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = tool_then_text
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "How are my metrics looking?"
        )

    assert mock_complete.await_count == 2
    assert mock_complete.await_args_list[0].kwargs["provider"] == provider
    roles = [m.role for m in result.messages]
    assert roles == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
        ChatRole.ASSISTANT,
    ]
    assert result.messages[1].tool_payload == {
        "tool_name": "get_metrics_summary",
        "arguments": {},
    }
    # Dialect-specific follow-up assembly on the second LLM call's messages.
    followup_msgs = mock_complete.await_args_list[1].kwargs["messages"]
    if provider == "anthropic":
        assert followup_msgs[1]["role"] == "assistant"
        assert isinstance(followup_msgs[1]["content"], list)
        assert followup_msgs[2]["role"] == "user"
        assert followup_msgs[2]["content"][0]["type"] == "tool_result"
    else:
        assert followup_msgs[1]["role"] == "assistant"
        assert "tool_calls" in followup_msgs[1]
        assert followup_msgs[2]["role"] == "tool"
        assert followup_msgs[2]["tool_call_id"] == "toolu_metrics_1"
    assert result.assistant_message.content.startswith("You have 2 page views")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["kimi", "anthropic"])
async def test_send_tool_round_cap_forces_text(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    _patch_tools_provider(monkeypatch, provider)
    user, experiment = await _seed_user_and_experiment(db_session)

    endless_tool = _tools_result(
        tool_uses=[
            ToolUseRequest(id="toolu_x", name="get_landing_status", input={})
        ],
        provider=provider,
    )
    final_text = _tools_result(
        text="Stopping after the tool budget.", provider=provider
    )

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            endless_tool,
            endless_tool,
            endless_tool,
            final_text,
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "Is my landing page live?"
        )

    assert mock_complete.await_count == 4
    fourth_kwargs = mock_complete.await_args_list[3].kwargs
    assert fourth_kwargs["provider"] == provider
    if provider == "anthropic":
        assert fourth_kwargs["tools"]  # schemas still present
        assert fourth_kwargs["tool_choice"] == {"type": "none"}
    else:
        assert fourth_kwargs["tools"] == []
        assert fourth_kwargs.get("tool_choice") is None
    assert result.assistant_message.content == "Stopping after the tool budget."
    assert len(result.messages) == 8
    for i in range(3):
        assert mock_complete.await_args_list[i].kwargs.get("tool_choice") is None
        assert mock_complete.await_args_list[i].kwargs["tools"]
    assert [m.role for m in result.messages].count(ChatRole.TOOL_CALL) == 3
    assert result.messages[-1].role == ChatRole.ASSISTANT


@pytest.mark.asyncio
async def test_send_no_tool_turn_single_invocation(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = _tools_result(
            text="You're in Spark — capture the idea, then move to Refine.",
            provider="kimi",
        )
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "What should I do next?"
        )

    assert mock_complete.await_count == 1
    kwargs = mock_complete.await_args.kwargs
    assert kwargs["phase"] == "universal_chat"
    assert kwargs["prompt_name"] == PROMPT_NAME_UNIVERSAL_CHAT
    assert kwargs["provider"] == "kimi"
    assert kwargs.get("tool_choice") is None
    assert [m.role for m in result.messages] == [ChatRole.USER, ChatRole.ASSISTANT]
    assert not any(m.role in {ChatRole.TOOL_CALL, ChatRole.TOOL_RESULT} for m in result.messages)


@pytest.mark.asyncio
async def test_send_soft_fail_executor_continues(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    async def _boom(
        _db: AsyncSession,
        _experiment: Experiment,
        _args: dict[str, Any],
        _user: User | None,
    ) -> dict[str, Any]:
        raise RuntimeError("db blew up")

    from app.services.universal_chat_tools import UniversalChatTool, _EMPTY_INPUT_SCHEMA

    broken = UniversalChatTool(
        name="get_landing_status",
        description="test",
        input_schema=_EMPTY_INPUT_SCHEMA,
        executor=_boom,
    )

    with (
        patch.dict(
            "app.services.universal_chat_tools._TOOLS_BY_NAME",
            {"get_landing_status": broken},
        ),
        patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete,
    ):
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_soft",
                        name="get_landing_status",
                        input={},
                    )
                ],
                provider="kimi",
            ),
            _tools_result(
                text="I couldn't load landing status — try again in a moment.",
                provider="kimi",
            ),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "Is my landing page live?"
        )

    assert mock_complete.await_count == 2
    assert [m.role for m in result.messages] == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
        ChatRole.ASSISTANT,
    ]
    payload = result.messages[2].tool_payload or {}
    assert payload["tool_name"] == "get_landing_status"
    assert "error" in payload
    assert "RuntimeError" in payload["error"]
    assert result.assistant_message.content.startswith("I couldn't load")


@pytest.mark.asyncio
async def test_send_mixed_text_and_tool_use_drops_interim_text(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interim text alongside tool_use must not become an assistant chat row."""
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)
    interim = "Let me pull your metrics for a second."
    final = "You have a quiet funnel so far — share the link more widely."

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            _tools_result(
                text=interim,
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_mix",
                        name="get_metrics_summary",
                        input={},
                    )
                ],
                provider="kimi",
            ),
            _tools_result(text=final, provider="kimi"),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "How are metrics?"
        )

    # API still gets the mixed assistant_turn for the follow-up turn.
    first_append = mock_complete.await_args_list[1].kwargs["messages"]
    assert any(
        msg.get("role") == "assistant" and msg.get("content") == interim
        for msg in first_append
    )

    assistant_rows = [m for m in result.messages if m.role == ChatRole.ASSISTANT]
    assert len(assistant_rows) == 1
    assert assistant_rows[0].content == final
    assert interim not in {m.content for m in result.messages}
    assert [m.role for m in result.messages] == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
        ChatRole.ASSISTANT,
    ]


@pytest.mark.asyncio
async def test_send_data_absent_tool_persists_available_false(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_absent",
                        name="get_landing_status",
                        input={},
                    )
                ],
                provider="kimi",
            ),
            _tools_result(
                text="No landing page yet — finish Launch when you're ready.",
                provider="kimi",
            ),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "Is my page live?"
        )

    payload = result.messages[2].tool_payload or {}
    assert payload["tool_name"] == "get_landing_status"
    assert payload["result"]["available"] is False
    assert "reason" in payload["result"]
    assert result.messages[-1].role == ChatRole.ASSISTANT


@pytest.mark.asyncio
async def test_send_response_messages_order_one_tool_turn(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_ord",
                        name="get_report_summary",
                        input={},
                    )
                ],
                provider="kimi",
            ),
            _tools_result(text="No validation report yet.", provider="kimi"),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "What did research find?"
        )

    roles = [m.role for m in result.messages]
    assert roles == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
        ChatRole.ASSISTANT,
    ]
    assert result.user_message.id == result.messages[0].id
    assert result.assistant_message.id == result.messages[-1].id
    assert mock_complete.await_count == 2
    for call in mock_complete.await_args_list:
        assert call.kwargs["phase"] == "universal_chat"
        assert call.kwargs["prompt_name"] == "universal_chat_v3"
        assert call.kwargs["provider"] == "kimi"


@pytest.mark.asyncio
async def test_send_initial_kimi_fallback_to_anthropic(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with (
        patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete,
        patch("app.services.universal_chat_service._logger") as mock_logger,
    ):
        mock_complete.side_effect = [
            RuntimeError("kimi unavailable"),
            _tools_result(
                text="Fallback coach answer from Anthropic.",
                provider="anthropic",
            ),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "What should I do next?"
        )

    assert mock_complete.await_count == 2
    assert mock_complete.await_args_list[0].kwargs["provider"] == "kimi"
    assert mock_complete.await_args_list[1].kwargs["provider"] == "anthropic"
    assert result.assistant_message.content.startswith("Fallback coach")
    assert [m.role for m in result.messages] == [ChatRole.USER, ChatRole.ASSISTANT]
    mock_logger.warning.assert_any_call(
        "universal_chat_tool_fallback",
        primary_provider="kimi",
        fallback_provider="anthropic",
        error_type="RuntimeError",
        experiment_id=str(experiment.id),
    )


@pytest.mark.asyncio
async def test_send_mid_loop_failure_does_not_fallback(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_mid",
                        name="get_landing_status",
                        input={},
                    )
                ],
                provider="kimi",
            ),
            RuntimeError("mid-loop provider failure"),
        ]
        with pytest.raises(RuntimeError, match="mid-loop"):
            await send_universal_chat_message(
                db_session, user, experiment.id, "Is my page live?"
            )

    assert mock_complete.await_count == 2
    # Both calls stayed on kimi — no cross-provider recovery mid-loop.
    assert mock_complete.await_args_list[0].kwargs["provider"] == "kimi"
    assert mock_complete.await_args_list[1].kwargs["provider"] == "kimi"


@pytest.mark.asyncio
async def test_history_flattens_tool_rows_without_payload(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Next-turn history uses short content labels, not tool_payload JSON."""
    _patch_tools_provider(monkeypatch, "kimi")
    user, experiment = await _seed_user_and_experiment(db_session)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_hist",
                        name="get_metrics_summary",
                        input={},
                    )
                ],
                provider="kimi",
            ),
            _tools_result(text="Quiet so far.", provider="kimi"),
        ]
        first = await send_universal_chat_message(
            db_session, user, experiment.id, "Metrics?"
        )
        tool_result = first.messages[2]
        tool_result.tool_payload = {
            "tool_name": "get_metrics_summary",
            "result": {"available": True, "blob": "x" * 50_000},
        }
        await db_session.commit()

        mock_complete.side_effect = None
        mock_complete.return_value = _tools_result(
            text="Next step: share the page.", provider="kimi"
        )
        await send_universal_chat_message(
            db_session, user, experiment.id, "What next?"
        )

    second_user_content = mock_complete.await_args.kwargs["messages"][0]["content"]
    assert "[tool_call]: Called: get_metrics_summary" in second_user_content
    assert "[tool_result]: Result received" in second_user_content
    assert "x" * 100 not in second_user_content
    assert "tool_use" not in second_user_content


def test_history_for_prompt_uses_content_only_and_truncates() -> None:
    """Flattened history is `[role]: content` — payload never enters the budget."""
    from types import SimpleNamespace

    toolish = [
        SimpleNamespace(
            role=ChatRole.TOOL_CALL,
            content="Called: get_metrics_summary",
            tool_payload={"tool_name": "get_metrics_summary", "arguments": {}},
        ),
        SimpleNamespace(
            role=ChatRole.TOOL_RESULT,
            content="Result received",
            tool_payload={
                "tool_name": "get_metrics_summary",
                "result": {"blob": "x" * 20_000},
            },
        ),
    ]
    flat = _history_for_prompt(toolish)  # type: ignore[arg-type]
    assert flat == (
        "[tool_call]: Called: get_metrics_summary\n"
        "[tool_result]: Result received"
    )
    assert "blob" not in flat
    assert "xxxx" not in flat

    long_msgs = [
        SimpleNamespace(role=ChatRole.USER, content="U" * 8000),
        SimpleNamespace(role=ChatRole.ASSISTANT, content="A" * 8000),
        SimpleNamespace(role=ChatRole.USER, content="newest"),
    ]
    rendered = _history_for_prompt(long_msgs)  # type: ignore[arg-type]
    assert "[user]: newest" in rendered
    assert len(rendered) <= 12000
    # Oldest user line dropped under the 12000-char budget.
    assert not rendered.startswith("[user]: " + ("U" * 100))


@pytest.mark.asyncio
async def test_send_rejects_wrong_owner(db_session: AsyncSession) -> None:
    owner, experiment = await _seed_user_and_experiment(db_session)
    other = await _seed_other_user(db_session)

    with (
        patch(_LLM_PATCH_TARGET, new_callable=AsyncMock),
        pytest.raises(UniversalChatNotFound),
    ):
        await send_universal_chat_message(
            db_session, other, experiment.id, "Hi"
        )
    assert owner.id != other.id


@pytest.mark.asyncio
async def test_send_rejects_archived(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.ARCHIVED
    )
    with (
        patch(_LLM_PATCH_TARGET, new_callable=AsyncMock),
        pytest.raises(UniversalChatUnavailable),
    ):
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

    tool_call = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.TOOL_CALL,
        content="Called: get_landing_status",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.UNIVERSAL_CHAT,
        parent_message_id=user_msg.id,
        tool_payload={"tool_name": "get_landing_status", "arguments": {}},
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
            "tool_name": "get_landing_status",
            "result": {"available": False, "reason": "No landing page yet."},
        },
    )
    db_session.add(tool_result)
    await db_session.flush()
    thread.active_leaf_message_id = tool_result.id
    await db_session.commit()

    listed = await list_universal_chat_messages(db_session, user, experiment.id)
    assert len(listed.messages) == 3
    roles = [m.role for m in listed.messages]
    assert roles == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
    ]

    items = [ChatMessageItem.from_orm_message(m) for m in listed.messages]
    assert items[1].tool_payload == {
        "tool_name": "get_landing_status",
        "arguments": {},
    }
    assert items[2].content == "Result received"


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
    assert "spark_version_current: 0" in block
    assert "refined_idea_version: 0" in block
    assert "STALENESS:" not in block
    assert ctx.refine_is_stale is False
    assert ctx.evidence_is_stale is False
    assert ctx.launch_is_stale is False
    assert ctx.insight_is_stale is False
    assert ctx.staleness_line is None
    assert user.id == experiment.user_id


@pytest.mark.asyncio
async def test_project_context_staleness_block_when_evidence_lags(
    db_session: AsyncSession,
) -> None:
    from app.db.models.validation_report import ValidationReport

    user, experiment = await _seed_user_and_experiment(
        db_session,
        status=ExperimentStatus.RESEARCH_READY,
        refined_idea=_refined_idea_dict(),
    )
    experiment.refined_idea_version = 2
    db_session.add(
        ValidationReport(
            experiment_id=experiment.id,
            raw_report={"version": "test"},
            refined_idea_version=1,
        )
    )
    await db_session.commit()
    await db_session.refresh(experiment)

    ctx = await get_experiment_project_context(db_session, experiment)
    assert ctx.evidence_is_stale is True
    assert ctx.insight_is_stale is False
    assert ctx.staleness_line is not None
    assert "STALENESS:" in ctx.staleness_line
    assert "refined idea" in ctx.staleness_line
    assert "evidence" in ctx.staleness_line
    block = ctx.to_prompt_block()
    assert "STALENESS:" in block
    assert user.id == experiment.user_id


def test_format_staleness_line_omits_when_fresh() -> None:
    from app.services.experiment_project_context import _format_staleness_line
    from app.services.spark_version_service import SparkPhaseVersionInfo

    info = SparkPhaseVersionInfo(
        current_spark_version=1,
        current_refined_idea_version=1,
        current_edited_doc_version=0,
        refine_spark_version=1,
        evidence_spark_version=1,
        launch_spark_version=1,
        signal_spark_version=1,
        refine_refined_idea_version=None,
        evidence_refined_idea_version=1,
        launch_refined_idea_version=1,
        signal_refined_idea_version=1,
        launch_edited_doc_version=0,
        refine_is_stale=False,
        evidence_is_stale=False,
        launch_is_stale=False,
        signal_is_stale=False,
        refine_stale_reasons=[],
        evidence_stale_reasons=[],
        launch_stale_reasons=[],
        signal_stale_reasons=[],
    )
    assert _format_staleness_line(info) is None


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


def test_tool_schemas_are_provider_dialect() -> None:
    anthropic_schemas = get_tool_schemas("anthropic")
    names = {s["name"] for s in anthropic_schemas}
    assert names == {
        "get_metrics_summary",
        "get_report_summary",
        "get_landing_status",
        "ask_refine_agent",
        "ask_research_agent",
    }
    for schema in anthropic_schemas:
        assert "input_schema" in schema
        assert "type" not in schema or schema.get("type") != "function"

    kimi_schemas = get_tool_schemas("kimi")
    assert {s["function"]["name"] for s in kimi_schemas} == names
    for schema in kimi_schemas:
        assert schema["type"] == "function"
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"

    refine_schema = next(s for s in anthropic_schemas if s["name"] == "ask_refine_agent")
    assert refine_schema["input_schema"]["required"] == ["query"]
    research_schema = next(
        s for s in anthropic_schemas if s["name"] == "ask_research_agent"
    )
    assert research_schema["input_schema"]["required"] == ["query"]


def test_prompt_name_is_universal_chat_v3() -> None:
    assert PROMPT_NAME_UNIVERSAL_CHAT == "universal_chat_v3"


@pytest.mark.asyncio
async def test_execute_tool_soft_fails_unknown(db_session: AsyncSession) -> None:
    user, experiment = await _seed_user_and_experiment(db_session)
    result = await execute_tool("not_a_real_tool", {}, db_session, experiment)
    assert result == {"error": "Unknown tool: not_a_real_tool"}
    assert user.id == experiment.user_id


@pytest.mark.asyncio
async def test_get_report_summary_available_false_without_report(
    db_session: AsyncSession,
) -> None:
    _user, experiment = await _seed_user_and_experiment(db_session)
    result = await execute_tool("get_report_summary", {}, db_session, experiment)
    assert result["available"] is False


@pytest.mark.asyncio
async def test_get_report_summary_top_findings(db_session: AsyncSession) -> None:
    _user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.RESEARCH_READY
    )
    raw = {
        "overall_recommendation": "proceed",
        "overall_score": 72,
        "competitors": [],
        "questions_and_findings": [
            {
                "question_id": "q1",
                "question": "Is demand real?",
                "score": 40,
                "findings": [
                    {
                        "question_id": "q1",
                        "claim": "Low-score finding that should rank below q2.",
                        "evidence_summary": "Weak signal from one forum thread.",
                        "citations": [
                            {
                                "url": "https://example.com/a",
                                "title": "A",
                                "snippet": "snip",
                            }
                        ],
                        "confidence": "low",
                        "confidence_rationale": "Single weak source.",
                    }
                ],
            },
            {
                "question_id": "q2",
                "question": "Who competes?",
                "score": 90,
                "findings": [
                    {
                        "question_id": "q2",
                        "claim": "Acme owns the incumbent workflow with 10k teams.",
                        "evidence_summary": "Pricing page and G2 reviews.",
                        "citations": [
                            {
                                "url": "https://example.com/b",
                                "title": "B",
                                "snippet": "snip",
                            }
                        ],
                        "confidence": "high",
                        "confidence_rationale": "Multiple strong sources.",
                    }
                ],
            },
        ],
    }
    db_session.add(
        ValidationReport(experiment_id=experiment.id, raw_report=raw)
    )
    await db_session.commit()

    result = await execute_tool("get_report_summary", {}, db_session, experiment)
    assert result["available"] is True
    assert result["overall_recommendation"] == "proceed"
    assert result["overall_score"] == 72
    assert result["total_finding_count"] == 2
    assert result["top_findings"][0]["claim"].startswith("Acme owns")


# --- Phase 2 sub-agents -------------------------------------------------


def test_build_source_refs_preserves_markers_and_order() -> None:
    from app.services.subagent_executors import build_source_refs_from_evidence_text

    text = (
        "Demand is real [cite: https://example.com/a]. "
        "Gap on pricing [ref: q2]. Overlap with Acme [ref: competitor:Acme]."
    )
    report = {
        "questions_and_findings": [
            {
                "question_id": "q2",
                "question": "Who competes?",
                "findings": [
                    {
                        "citations": [
                            {
                                "url": "https://example.com/a",
                                "title": "Demand survey",
                            }
                        ]
                    }
                ],
            }
        ],
        "competitors": [],
    }
    refs = build_source_refs_from_evidence_text(text, report)
    assert [r["ref_number"] for r in refs] == [1, 2, 3]
    assert refs[0]["marker_id"].lower().startswith("[cite:")
    assert refs[0]["source_url"] == "https://example.com/a"
    assert refs[0]["source_title"] == "Demand survey"
    assert refs[1]["source_url"] is None
    assert refs[1]["source_title"].startswith("q2:")
    assert refs[2]["source_title"] == "Competitor: Acme"


@pytest.mark.asyncio
async def test_ask_refine_agent_maps_turn_decision(
    db_session: AsyncSession,
) -> None:
    from app.db.enums import ChatTurnKind
    from app.schemas.refinement import ClarifyingQuestion
    from app.services.chat_service import ChatTurnResult
    from app.services.subagent_executors import exec_ask_refine_agent

    user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.REFINING
    )
    experiment.refined_idea_current = None
    await db_session.commit()

    turn = ChatTurnResult(
        thread_id=uuid4(),
        message_id=uuid4(),
        experiment_id=experiment.id,
        assistant_message="Who is the primary buyer?",
        turn_kind=ChatTurnKind.REFINEMENT_CLARIFY,
        clarifying_dimension="audience",
        clarifying_questions=(
            ClarifyingQuestion(
                question="Who is the primary buyer?",
                selection_mode="single",
                options=["HR managers", "Employees", "Both"],
            ),
        ),
        pipeline_dispatched=False,
        dispatched_at=None,
        experiment_status=ExperimentStatus.REFINING,
        research_error_detail=None,
        user_facing_error=None,
        refinement_count=1,
    )

    async def _fake_handle_turn(*_args: Any, **_kwargs: Any) -> ChatTurnResult:
        experiment.refined_idea_current = _refined_idea_dict()
        await db_session.commit()
        return turn

    with patch(
        "app.services.subagent_executors.chat_service.handle_turn",
        new=_fake_handle_turn,
    ):
        result = await exec_ask_refine_agent(
            db_session,
            experiment,
            {"query": "Help me name the product"},
            user,
        )

    assert result["assistant_text"] == "Who is the primary buyer?"
    assert result["has_pending_mcq"] is True
    assert result["log_entry"] == "audience"
    assert isinstance(result["refined_idea_patch"], dict)
    assert result["refined_idea_patch"]["project_name"] == "PolicyPal"


@pytest.mark.asyncio
async def test_ask_research_agent_maps_citations(
    db_session: AsyncSession,
) -> None:
    from app.services.evidence_chat_service import EvidenceChatResult
    from app.services.subagent_executors import exec_ask_research_agent

    user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.RESEARCH_READY
    )
    raw = {
        "questions_and_findings": [
            {
                "question_id": "q1",
                "question": "Is demand real?",
                "findings": [
                    {
                        "citations": [
                            {
                                "url": "https://example.com/demand",
                                "title": "Demand post",
                            }
                        ]
                    }
                ],
            }
        ],
        "competitors": [],
    }
    db_session.add(ValidationReport(experiment_id=experiment.id, raw_report=raw))
    await db_session.commit()

    assistant = ChatMessage(
        thread_id=uuid4(),
        role=ChatRole.ASSISTANT,
        content=(
            "Demand looks real [cite: https://example.com/demand]. "
            "See also [ref: q1]."
        ),
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
    )
    user_msg = ChatMessage(
        thread_id=assistant.thread_id,
        role=ChatRole.USER,
        content="What does research say?",
        experiment_id=experiment.id,
        turn_kind=ChatTurnKind.EVIDENCE_CHAT,
    )

    async def _fake_evidence(*_args: Any, **_kwargs: Any) -> EvidenceChatResult:
        return EvidenceChatResult(
            user_message=user_msg,
            assistant_message=assistant,
            thread_id=assistant.thread_id,
        )

    with patch(
        "app.services.subagent_executors.send_evidence_chat_message",
        new=_fake_evidence,
    ):
        result = await exec_ask_research_agent(
            db_session,
            experiment,
            {"query": "What does the research say about demand?"},
            user,
        )

    assert "[cite:" in result["assistant_text_with_citations"]
    assert len(result["source_refs"]) == 2
    assert result["source_refs"][0]["source_title"] == "Demand post"
    assert result["source_refs"][0]["source_url"] == "https://example.com/demand"


@pytest.mark.asyncio
async def test_master_loop_ask_refine_agent_persists_linearly(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "anthropic")
    user, experiment = await _seed_user_and_experiment(
        db_session, status=ExperimentStatus.REFINING
    )

    async def _fake_refine(
        _db: AsyncSession,
        _experiment: Experiment,
        _args: dict[str, Any],
        _user: User | None,
    ) -> dict[str, Any]:
        return {
            "assistant_text": "Let's tighten the one-liner.",
            "refined_idea_patch": None,
            "has_pending_mcq": False,
            "log_entry": None,
        }

    with (
        patch(
            "app.services.universal_chat_tools.exec_ask_refine_agent",
            new=_fake_refine,
        ),
        patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete,
    ):
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_refine",
                        name="ask_refine_agent",
                        input={"query": "Help me name this"},
                    )
                ],
            ),
            _tools_result(text="Refine suggested tightening the one-liner."),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "Help me name this"
        )

    roles = [m.role for m in result.messages]
    assert roles == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
        ChatRole.ASSISTANT,
    ]
    tool_call = result.messages[1]
    tool_result = result.messages[2]
    assert tool_call.tool_payload == {
        "tool_name": "ask_refine_agent",
        "arguments": {"query": "Help me name this"},
    }
    assert tool_result.tool_payload == {
        "tool_name": "ask_refine_agent",
        "result": {
            "assistant_text": "Let's tighten the one-liner.",
            "refined_idea_patch": None,
            "has_pending_mcq": False,
            "log_entry": None,
        },
    }
    assert result.assistant_message.content == (
        "Refine suggested tightening the one-liner."
    )


@pytest.mark.asyncio
async def test_ask_refine_agent_soft_fail_continues(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_tools_provider(monkeypatch, "anthropic")
    user, experiment = await _seed_user_and_experiment(db_session)

    async def _boom(
        _db: AsyncSession,
        _experiment: Experiment,
        _args: dict[str, Any],
        _user: User | None,
    ) -> dict[str, Any]:
        raise RuntimeError("refine service down")

    with (
        patch(
            "app.services.universal_chat_tools.exec_ask_refine_agent",
            new=_boom,
        ),
        patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete,
    ):
        mock_complete.side_effect = [
            _tools_result(
                tool_uses=[
                    ToolUseRequest(
                        id="toolu_refine_fail",
                        name="ask_refine_agent",
                        input={"query": "Name it"},
                    )
                ],
            ),
            _tools_result(text="Refine is briefly unavailable — try again."),
        ]
        result = await send_universal_chat_message(
            db_session, user, experiment.id, "Name it"
        )

    tool_result = result.messages[2]
    assert tool_result.role == ChatRole.TOOL_RESULT
    assert tool_result.tool_payload is not None
    assert "error" in tool_result.tool_payload
    assert result.assistant_message.content.startswith("Refine is briefly unavailable")
