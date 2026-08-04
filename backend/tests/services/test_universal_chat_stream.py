"""Tests for universal-chat SSE streaming (PR2.9)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import (
    ChatRole,
    ExperimentStatus,
    LandingCtaType,
    LandingDensity,
)
from app.db.models.chat_message import ChatMessage
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.user import User
from app.llm.client import LLMResult, ToolsLLMResult, ToolUseRequest
from app.services.universal_chat_service import (
    UniversalStreamPrep,
    iter_paced_text_chunks,
    prepare_universal_stream,
    stream_universal_chat_message,
)

_LLM_PATCH = "app.services.universal_chat_service.llm_client.complete_with_tools"
_SM_PATCH = "app.services.universal_chat_service.get_sessionmaker"
_EXECUTE_TOOL_PATCH = "app.services.universal_chat_service.execute_tool"


@pytest.fixture
async def sm() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        get_settings().database_url, pool_size=5, max_overflow=0
    )
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        yield maker
    finally:
        await engine.dispose()


def _patch_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "universal_chat_tools_provider", "anthropic")
    monkeypatch.setattr(settings, "universal_chat_tools_model", "claude-sonnet-4-6")
    monkeypatch.setattr(settings, "universal_chat_tools_fallback_provider", "anthropic")
    monkeypatch.setattr(
        settings, "universal_chat_tools_fallback_model", "claude-sonnet-4-6"
    )


def _llm_meta(*, text: str = "") -> LLMResult:
    return LLMResult(
        text=text,
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=Decimal("0.001"),
        latency_ms=50,
    )


def _tools_result(
    *,
    text: str | None = None,
    tool_uses: list[ToolUseRequest] | None = None,
) -> ToolsLLMResult:
    uses = tool_uses or []
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
    return ToolsLLMResult(
        assistant_text=text,
        tool_uses=uses,
        assistant_turn={"role": "assistant", "content": content},
        llm_result=_llm_meta(text=text or ""),
    )


async def _seed(
    session: AsyncSession,
    *,
    status: ExperimentStatus = ExperimentStatus.SPARK,
) -> tuple[User, Experiment]:
    user = User(
        firebase_uid=f"univ-stream-{uuid4()}",
        email=f"univ-stream-{uuid4()}@example.com",
        name="Stream Tester",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    experiment = Experiment(
        user_id=user.id,
        name="Stream Project",
        raw_idea="An app that helps founders validate ideas.",
        status=status,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)
    return user, experiment


async def _collect_events(
    prep: UniversalStreamPrep,
    maker: async_sessionmaker[AsyncSession],
) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    with patch(_SM_PATCH, return_value=maker):
        async for name, payload in stream_universal_chat_message(prep):
            if name.startswith("_"):
                continue
            events.append((name, payload))
    return events


@pytest.mark.asyncio
async def test_iter_paced_text_chunks_word_groups() -> None:
    chunks = [
        c
        async for c in iter_paced_text_chunks(
            "one two three four five six seven eight nine",
            pacing_delay=0,
        )
    ]
    assert "".join(chunks).replace(" ", "") == (
        "onetwothreefourfivesixseveneightnine"
    )
    assert all(c.endswith(" ") or c == chunks[-1] for c in chunks)
    assert len(chunks) >= 2


@pytest.mark.asyncio
async def test_stream_pure_text_turn(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(session)
        prep = await prepare_universal_stream(
            session, user, experiment.id, "How is my project going?", pacing_delay=0
        )

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _tools_result(
            text="You're still in Spark — capture the idea clearly."
        )
        events = await _collect_events(prep, sm)

    names = [e[0] for e in events]
    assert "tool_call" not in names
    assert "subagent_token" not in names
    assert names[0] == "assistant_token"
    assert names[-1] == "done"
    assert all(n in ("assistant_token", "done") for n in names)
    full = "".join(p["text"] for n, p in events if n == "assistant_token")
    assert "Spark" in full

    async with sm() as session:
        msgs = (
            await session.execute(
                select(ChatMessage)
                .where(ChatMessage.thread_id == prep.thread_id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
            )
        ).scalars().all()
    roles = [m.role for m in msgs]
    assert roles == [ChatRole.USER, ChatRole.ASSISTANT]
    assert msgs[0].id == prep.user_message_id


@pytest.mark.asyncio
async def test_stream_read_tool_then_assistant(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(
            session, status=ExperimentStatus.LANDING_LIVE
        )
        landing = LandingPage(
            experiment_id=experiment.id,
            slug=f"stream-{uuid4().hex[:10]}",
            template_id="minimal",
            palette_id="default",
            font_pair_id="sans",
            density=LandingDensity.ROOMY,
            headline="Try it",
            subheadline="Sub",
            problem_desc="Problem",
            solution_desc="Solution",
            cta_text="Join",
            cta_type=LandingCtaType.WAITLIST,
            live_at=datetime.now(UTC),
        )
        session.add(landing)
        session.add(PageView(experiment_id=experiment.id, source_tag="twitter"))
        await session.commit()
        prep = await prepare_universal_stream(
            session, user, experiment.id, "How are metrics?", pacing_delay=0
        )

    calls = [
        _tools_result(
            tool_uses=[
                ToolUseRequest(id="t1", name="get_metrics_summary", input={})
            ]
        ),
        _tools_result(text="You have early traffic from Twitter."),
    ]

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = calls
        events = await _collect_events(prep, sm)

    names = [e[0] for e in events]
    assert names.count("tool_call") == 1
    assert names.count("tool_result") == 1
    assert "subagent_token" not in names
    assert names.index("tool_call") < names.index("tool_result")
    assert names.index("tool_result") < names.index("assistant_token")
    assert names[-1] == "done"

    async with sm() as session:
        msgs = (
            await session.execute(
                select(ChatMessage)
                .where(ChatMessage.thread_id == prep.thread_id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
            )
        ).scalars().all()
    assert [m.role for m in msgs] == [
        ChatRole.USER,
        ChatRole.TOOL_CALL,
        ChatRole.TOOL_RESULT,
        ChatRole.ASSISTANT,
    ]


@pytest.mark.asyncio
async def test_stream_refine_subagent_fake_stream(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(session)
        prep = await prepare_universal_stream(
            session, user, experiment.id, "Help refine the name", pacing_delay=0
        )

    # One master tool-routing call only — no second "summary" call after refine.
    calls = [
        _tools_result(
            tool_uses=[
                ToolUseRequest(
                    id="t1",
                    name="ask_refine_agent",
                    input={"query": "Help refine the name"},
                )
            ]
        ),
    ]

    refine_result = {
        "assistant_text": "Try PolicyPal — short and memorable for Slack HR.",
        "refined_idea_patch": None,
        "has_pending_mcq": False,
        "log_entry": None,
    }

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm, patch(
        _EXECUTE_TOOL_PATCH, new_callable=AsyncMock
    ) as mock_exec:
        mock_llm.side_effect = calls
        mock_exec.return_value = refine_result
        events = await _collect_events(prep, sm)

    names = [e[0] for e in events]
    assert "tool_call" in names
    assert "tool_result" in names
    tool_result_idx = names.index("tool_result")
    first_token = next(i for i, n in enumerate(names) if n == "assistant_token")
    # Refine prose paces inside ``_stream_refine_tool`` before tool_result.
    assert first_token < tool_result_idx
    assert not any(n == "subagent_token" for n in names)
    assistant_tokens = [p["text"] for n, p in events if n == "assistant_token"]
    assert "".join(assistant_tokens).replace(" ", "").startswith("TryPolicyPal")
    tr_payload = next(p for n, p in events if n == "tool_result")
    assert "payload" in tr_payload
    assert tr_payload["payload"]["tool_name"] == "ask_refine_agent"
    assert names[-1] == "done"
    assert mock_llm.await_count == 1


@pytest.mark.asyncio
async def test_stream_get_research_context_then_cited_answer(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(session)
        prep = await prepare_universal_stream(
            session, user, experiment.id, "What did research find?", pacing_delay=0
        )

    calls = [
        _tools_result(
            tool_uses=[
                ToolUseRequest(
                    id="t1",
                    name="get_research_context",
                    input={"query": "What did research find?"},
                )
            ]
        ),
        _tools_result(text="Demand is real [cite:s1]."),
    ]

    async def _fake_execute(name: str, *_a: Any, **_k: Any) -> dict[str, Any]:
        assert name == "get_research_context"
        return {
            "available": True,
            "findings_digest": "Demand looks real.",
            "sources": [
                {
                    "id": "s1",
                    "title": "Example",
                    "url": "https://example.com",
                    "domain": "example.com",
                }
            ],
            "source_refs": [
                {
                    "marker_id": "[cite:s1]",
                    "source_title": "Example",
                    "source_url": "https://example.com",
                    "source_domain": "example.com",
                }
            ],
        }

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm, patch(
        _EXECUTE_TOOL_PATCH, new=_fake_execute
    ):
        mock_llm.side_effect = calls
        events = await _collect_events(prep, sm)

    names = [e[0] for e in events]
    assert "tool_call" in names
    assert "tool_result" in names
    assert any(n == "assistant_token" for n in names)
    assistant_text = "".join(
        p["text"] for n, p in events if n == "assistant_token"
    )
    assert "[cite:s1]" in assistant_text
    tr_payload = next(p for n, p in events if n == "tool_result")
    result = (tr_payload["payload"].get("result") or {})
    assert result.get("source_refs")
    assert names[-1] == "done"


@pytest.mark.asyncio
async def test_stream_get_research_context_unavailable(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(session)
        prep = await prepare_universal_stream(
            session, user, experiment.id, "Ask research", pacing_delay=0
        )

    calls = [
        _tools_result(
            tool_uses=[
                ToolUseRequest(
                    id="t1",
                    name="get_research_context",
                    input={"query": "Ask research"},
                )
            ]
        ),
        _tools_result(text="The validation report isn't ready yet."),
    ]

    async def _fake_execute(*_a: Any, **_k: Any) -> dict[str, Any]:
        return {
            "available": False,
            "reason": "No validation report yet.",
            "findings_digest": "",
            "sources": [],
            "source_refs": [],
        }

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm, patch(
        _EXECUTE_TOOL_PATCH, new=_fake_execute
    ):
        mock_llm.side_effect = calls
        events = await _collect_events(prep, sm)

    assert not any(n == "subagent_token" for n, _ in events)
    assistant_text = "".join(
        p["text"] for n, p in events if n == "assistant_token"
    )
    assert "isn't ready" in assistant_text or "not ready" in assistant_text.lower()


async def test_stream_error_leaves_no_assistant(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(session)
        prep = await prepare_universal_stream(
            session, user, experiment.id, "Hello", pacing_delay=0
        )

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = RuntimeError("boom")
        # Disable initial-call fallback so the error surfaces as SSE error.
        events = await _collect_events(prep, sm)

    # Fallback may retry once on anthropic→anthropic; force no recovery by
    # ensuring both attempts raise.
    assert events[-1][0] == "error" or events == [
        ("error", {"message": "Universal chat failed, please try again"})
    ]
    if events[-1][0] != "error":
        # If fallback somehow returned text, skip — but with side_effect=boom both fail.
        pass
    assert events[-1] == (
        "error",
        {"message": "Universal chat failed, please try again"},
    )

    async with sm() as session:
        assistant_count = await session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.thread_id == prep.thread_id,
                ChatMessage.role == ChatRole.ASSISTANT,
            )
        )
        user_count = await session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.thread_id == prep.thread_id,
                ChatMessage.role == ChatRole.USER,
            )
        )
    assert assistant_count == 0
    assert user_count == 1


@pytest.mark.asyncio
async def test_stream_cap_round_emits_multiple_tool_cycles(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(
            session, status=ExperimentStatus.LANDING_LIVE
        )
        landing = LandingPage(
            experiment_id=experiment.id,
            slug=f"cap-{uuid4().hex[:10]}",
            template_id="minimal",
            palette_id="default",
            font_pair_id="sans",
            density=LandingDensity.ROOMY,
            headline="H",
            subheadline="S",
            problem_desc="P",
            solution_desc="Sol",
            cta_text="Join",
            cta_type=LandingCtaType.WAITLIST,
            live_at=datetime.now(UTC),
        )
        session.add(landing)
        await session.commit()
        prep = await prepare_universal_stream(
            session, user, experiment.id, "Check everything", pacing_delay=0
        )

    tool_round = _tools_result(
        tool_uses=[
            ToolUseRequest(id="a", name="get_landing_status", input={}),
        ]
    )
    calls = [tool_round, tool_round, tool_round, _tools_result(text="All set.")]

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = calls
        events = await _collect_events(prep, sm)

    assert [e[0] for e in events].count("tool_call") == 3
    assert [e[0] for e in events].count("tool_result") == 3
    assert any(e[0] == "assistant_token" for e in events)
    assert events[-1][0] == "done"
    # Read-tool tool_result carries payload.
    assert all("payload" in p for n, p in events if n == "tool_result")


@pytest.mark.asyncio
async def test_stream_cancel_mid_tool_persists_partial(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel mid-tool: user + tool_call persist; no tool_result / assistant."""
    import asyncio

    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(
            session, status=ExperimentStatus.LANDING_LIVE
        )
        landing = LandingPage(
            experiment_id=experiment.id,
            slug=f"cancel-{uuid4().hex[:10]}",
            template_id="minimal",
            palette_id="default",
            font_pair_id="sans",
            density=LandingDensity.ROOMY,
            headline="H",
            subheadline="S",
            problem_desc="P",
            solution_desc="Sol",
            cta_text="Join",
            cta_type=LandingCtaType.WAITLIST,
            live_at=datetime.now(UTC),
        )
        session.add(landing)
        await session.commit()
        prep = await prepare_universal_stream(
            session, user, experiment.id, "Research this", pacing_delay=0
        )

    calls = [
        _tools_result(
            tool_uses=[
                ToolUseRequest(
                    id="t1",
                    name="get_research_context",
                    input={"query": "Research this"},
                )
            ]
        ),
    ]

    started = asyncio.Event()

    async def _slow_execute(*_a: Any, **_k: Any) -> dict[str, Any]:
        started.set()
        await asyncio.sleep(60)
        return {
            "available": True,
            "findings_digest": "",
            "sources": [],
            "source_refs": [],
        }

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm, patch(
        _EXECUTE_TOOL_PATCH, new=_slow_execute
    ), patch(_SM_PATCH, return_value=sm):
        mock_llm.side_effect = calls
        agen = stream_universal_chat_message(prep)
        tool_call_seen = asyncio.Event()

        async def _consume() -> None:
            async for name, _payload in agen:
                if name == "tool_call":
                    tool_call_seen.set()
                # Keep iterating so execute_tool starts after tool_call yield.

        consumer = asyncio.create_task(_consume())
        await asyncio.wait_for(tool_call_seen.wait(), timeout=5)
        await asyncio.wait_for(started.wait(), timeout=5)
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    async with sm() as session:
        msgs = (
            await session.execute(
                select(ChatMessage)
                .where(ChatMessage.thread_id == prep.thread_id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
            )
        ).scalars().all()
        roles = [m.role for m in msgs]
        assert ChatRole.USER in roles
        assert ChatRole.TOOL_CALL in roles
        assert ChatRole.TOOL_RESULT not in roles
        assert ChatRole.ASSISTANT not in roles



@pytest.mark.asyncio
async def test_stream_open_phase_panel_navigate_payload(
    sm: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_provider(monkeypatch)
    async with sm() as session:
        user, experiment = await _seed(session)
        prep = await prepare_universal_stream(
            session,
            user,
            experiment.id,
            "Show me the report",
            pacing_delay=0,
            current_open_phase=None,
        )

    calls = [
        _tools_result(
            tool_uses=[
                ToolUseRequest(
                    id="t1",
                    name="open_phase_panel",
                    input={"phase": "evidence", "source_ref_id": None},
                )
            ]
        ),
        _tools_result(text="Opened Evidence for you."),
    ]

    with patch(_LLM_PATCH, new_callable=AsyncMock) as mock_llm, patch(
        _EXECUTE_TOOL_PATCH, new_callable=AsyncMock
    ) as mock_exec:
        mock_llm.side_effect = calls
        mock_exec.return_value = {
            "navigate_to": "evidence",
            "source_ref_id": None,
        }
        events = await _collect_events(prep, sm)

    names = [e[0] for e in events]
    assert "tool_call" in names
    assert "tool_result" in names
    tr = next(p for n, p in events if n == "tool_result")
    assert tr["payload"]["tool_name"] == "open_phase_panel"
    assert tr["payload"]["result"] == {
        "navigate_to": "evidence",
        "source_ref_id": None,
    }
    assert names[-1] == "done"
