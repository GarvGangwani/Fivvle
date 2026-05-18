"""Tests for the Instructor usage-accumulator fix in app.llm.client.

These tests verify that complete_structured tallies tokens across ALL
Instructor retry attempts, not just the final successful response.

The completion:response hook fires on every provider API call inside
Instructor's retry loop (including calls that fail schema validation and
are retried).  Each test controls how many times the hook fires by
embedding hook.emit_completion_response() calls inside a fake
create_with_completion implementation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.llm_call import LLMCall
from app.llm.client import (
    USER_CACHE_ZONE_BOUNDARY,
    CacheBreakpoint,
    complete_structured,
)
from app.llm.cost import compute_anthropic_cached_cost_usd, compute_cost_usd
from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID  # noqa: F401


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Standalone async session for accumulator tests.

    Mirrors the db_session fixture in tests/test_llm_client.py — a fresh
    engine per test avoids dependency on lifespan ordering.
    """
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


class _Reply(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Test 1 — single attempt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structured_single_attempt_accumulates_usage(mock_firebase, db_session):
    """Single Instructor attempt: LLMCall row reflects that one response's usage.

    The mock fires the completion:response hook exactly once before returning,
    which is what Instructor does when validation passes on the first try.
    """
    parsed_instance = _Reply(message="ok")

    req_id = f"msg_acc_single_001_{uuid4()}"
    fake_raw = MagicMock()
    fake_raw.id = req_id
    fake_raw.usage = MagicMock(input_tokens=200, output_tokens=80)

    async def _fake_create_with_completion(**kwargs):
        hooks = kwargs.get("hooks")
        if hooks is not None:
            hooks.emit_completion_response(fake_raw)
        return (parsed_instance, fake_raw)

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = _fake_create_with_completion

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        parsed, meta = await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="acc_single_test",
            system="respond with JSON",
            user="give me a message",
            response_model=_Reply,
        )
        await db_session.commit()

    assert parsed.message == "ok"
    assert meta.prompt_tokens == 200
    assert meta.completion_tokens == 80
    assert meta.cost_usd > Decimal("0")

    stmt = select(LLMCall).where(LLMCall.request_id == req_id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == 200
    assert rows[0].completion_tokens == 80
    assert rows[0].cost_usd > Decimal("0")
    await db_session.delete(rows[0])
    await db_session.commit()


# ---------------------------------------------------------------------------
# Test 2 — multi-attempt retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structured_multi_attempt_accumulates_usage(mock_firebase, db_session):
    """Three Instructor attempts: LLMCall row sums all three responses' usage.

    Simulates two schema-validation failures followed by a successful parse.
    Anthropic bills for all three API calls; the LLMCall row must reflect the
    total, not just the final attempt.
    """
    parsed_instance = _Reply(message="third try")

    # Three separate fake responses, each with distinct token counts so the
    # test is sensitive to which subset was recorded.
    attempt_responses = [
        MagicMock(id=None, usage=MagicMock(input_tokens=100, output_tokens=40)),
        MagicMock(id=None, usage=MagicMock(input_tokens=110, output_tokens=45)),
        MagicMock(id=None, usage=MagicMock(input_tokens=120, output_tokens=50)),
    ]
    req_id = f"msg_acc_multi_001_{uuid4()}"
    attempt_responses[-1].id = req_id

    async def _fake_create_with_completion(**kwargs):
        hooks = kwargs.get("hooks")
        if hooks is not None:
            for resp in attempt_responses:
                hooks.emit_completion_response(resp)
        return (parsed_instance, attempt_responses[-1])

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = _fake_create_with_completion

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        parsed, meta = await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="acc_multi_test",
            system="respond with JSON",
            user="give me a message",
            response_model=_Reply,
        )
        await db_session.commit()

    expected_prompt = 100 + 110 + 120  # 330
    expected_completion = 40 + 45 + 50  # 135

    assert parsed.message == "third try"
    assert meta.prompt_tokens == expected_prompt, (
        f"Expected accumulated prompt_tokens={expected_prompt}, got {meta.prompt_tokens}. "
        "Only the final attempt's tokens were recorded — accumulator not working."
    )
    assert meta.completion_tokens == expected_completion, (
        f"Expected accumulated completion_tokens={expected_completion}, "
        f"got {meta.completion_tokens}."
    )
    assert meta.cost_usd > Decimal("0")

    stmt = select(LLMCall).where(LLMCall.request_id == req_id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == expected_prompt
    assert rows[0].completion_tokens == expected_completion
    await db_session.delete(rows[0])
    await db_session.commit()


# ---------------------------------------------------------------------------
# Test 3 — max_retries is forwarded to create_with_completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structured_max_retries_forwarded(mock_firebase, db_session):
    """max_retries passed to complete_structured is forwarded to create_with_completion.

    Verifies the plumbing only — what Instructor does with max_retries is its
    own contract.
    """
    parsed_instance = _Reply(message="ok")

    req_id = f"msg_max_retries_001_{uuid4()}"
    fake_raw = MagicMock()
    fake_raw.id = req_id
    fake_raw.usage = MagicMock(input_tokens=150, output_tokens=60)

    captured_kwargs: dict = {}

    async def _fake_create_with_completion(**kwargs):
        captured_kwargs.update(kwargs)
        hooks = kwargs.get("hooks")
        if hooks is not None:
            hooks.emit_completion_response(fake_raw)
        return (parsed_instance, fake_raw)

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = _fake_create_with_completion

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="max_retries_test",
            system="respond with JSON",
            user="give me a message",
            response_model=_Reply,
            max_retries=1,
        )
        await db_session.commit()

    assert captured_kwargs.get("max_retries") == 1

    stmt = select(LLMCall).where(LLMCall.request_id == req_id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    await db_session.delete(rows[0])
    await db_session.commit()


# ---------------------------------------------------------------------------
# Prompt caching (ADR 0014 foundation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_structured_no_cache_breakpoints_identical_behavior(mock_firebase, db_session):
    parsed_instance = _Reply(message="ok")

    req_id = f"msg_no_cache_behavior_{uuid4()}"
    fake_raw = MagicMock()
    fake_raw.id = req_id
    fake_raw.usage = MagicMock(input_tokens=200, output_tokens=80)

    captured: dict = {}

    async def _fake_create_with_completion(**kwargs):
        captured.update(kwargs)
        hooks = kwargs.get("hooks")
        if hooks is not None:
            hooks.emit_completion_response(fake_raw)
        return (parsed_instance, fake_raw)

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = _fake_create_with_completion

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        parsed, meta = await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt_name="no_cache_behavior",
            system="sys body",
            user="user body",
            response_model=_Reply,
            cache_breakpoints=None,
        )
        await db_session.commit()

    assert captured.get("system") == "sys body"
    assert captured.get("messages") == [{"role": "user", "content": "user body"}]
    assert parsed.message == "ok"
    assert meta.prompt_tokens == 200
    assert meta.completion_tokens == 80

    rows = (
        (await db_session.execute(select(LLMCall).where(LLMCall.request_id == req_id))).scalars().all()
    )
    assert len(rows) == 1
    assert rows[0].cached_input_tokens is None
    assert rows[0].cache_creation_input_tokens is None
    await db_session.delete(rows[0])
    await db_session.commit()


@pytest.mark.asyncio
async def test_complete_structured_with_cache_breakpoints_injects_markers(mock_firebase, db_session):
    parsed_instance = _Reply(message="cached")

    req_id = f"msg_cache_markers_{uuid4()}"
    fake_raw = MagicMock()
    fake_raw.id = req_id
    fake_raw.usage = MagicMock(input_tokens=12, output_tokens=3)

    captured: dict = {}

    async def _fake_create_with_completion(**kwargs):
        captured.update(kwargs)
        hooks = kwargs.get("hooks")
        if hooks is not None:
            hooks.emit_completion_response(fake_raw)
        return (parsed_instance, fake_raw)

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = _fake_create_with_completion

    ua, ub, uc = "ZONE_A", "ZONE_B", "ZONE_C_TAIL"
    user = f"{ua}{USER_CACHE_ZONE_BOUNDARY}{ub}{USER_CACHE_ZONE_BOUNDARY}{uc}"
    breakpoints = [
        CacheBreakpoint(position="system_end", ttl="1h"),
        CacheBreakpoint(position="user_zone_a_end", ttl="5m"),
        CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
    ]

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt_name="cache_markers_test",
            system="instructions",
            user=user,
            response_model=_Reply,
            cache_breakpoints=breakpoints,
        )
        await db_session.commit()

    sys_arg = captured.get("system")
    assert isinstance(sys_arg, list) and len(sys_arg) == 1
    assert sys_arg[0]["type"] == "text"
    assert sys_arg[0]["text"] == "instructions"
    assert sys_arg[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}

    msgs = captured.get("messages")
    blocks = msgs[0]["content"]
    assert isinstance(blocks, list) and len(blocks) == 3
    assert blocks[0]["text"] == ua
    assert blocks[0]["cache_control"]["ttl"] == "5m"
    assert blocks[1]["text"] == ub
    assert blocks[2]["text"] == uc
    assert "cache_control" not in blocks[2]

    row = (
        (await db_session.execute(select(LLMCall).where(LLMCall.request_id == req_id))).scalars().first()
    )
    assert row is not None
    await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_complete_structured_persists_cached_token_fields(mock_firebase, db_session):
    parsed_instance = _Reply(message="persist")

    req_id = f"msg_cache_usage_persist_{uuid4()}"
    fake_raw = MagicMock()
    fake_raw.id = req_id

    uc = MagicMock(
        ephemeral_5m_input_tokens=15,
        ephemeral_1h_input_tokens=5,
    )
    fake_raw.usage = MagicMock(
        input_tokens=120,
        output_tokens=33,
        cache_read_input_tokens=40,
        cache_creation_input_tokens=20,
        cache_creation=uc,
    )

    async def _fake_create_with_completion(**kwargs):
        hooks = kwargs.get("hooks")
        if hooks is not None:
            hooks.emit_completion_response(fake_raw)
        return (parsed_instance, fake_raw)

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = _fake_create_with_completion

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt_name="cache_persist_test",
            system="s",
            user="u",
            response_model=_Reply,
        )
        await db_session.commit()

    row = (
        (await db_session.execute(select(LLMCall).where(LLMCall.request_id == req_id))).scalars().first()
    )
    assert row is not None
    assert row.cached_input_tokens == 40
    assert row.cache_creation_input_tokens == 20
    assert row.prompt_tokens == 120 + 40 + 20
    await db_session.delete(row)
    await db_session.commit()


def test_cost_calculation_uncached_only():
    model = "claude-sonnet-4-6"
    baseline = compute_cost_usd("anthropic", model, 400_000, 55_555)
    split = compute_anthropic_cached_cost_usd(
        model,
        uncached_tail_input_tokens=400_000,
        cache_read_input_tokens=0,
        cache_creation_ephemeral_5m=0,
        cache_creation_ephemeral_1h=0,
        completion_tokens=55_555,
    )
    assert baseline == split


def test_cost_calculation_with_cached_read():
    cost = compute_anthropic_cached_cost_usd(
        "claude-sonnet-4-6",
        uncached_tail_input_tokens=0,
        cache_read_input_tokens=1_000_000,
        cache_creation_ephemeral_5m=0,
        cache_creation_ephemeral_1h=0,
        completion_tokens=0,
    )
    assert cost == Decimal("0.300000")


def test_cost_calculation_with_cache_write_5m():
    cost = compute_anthropic_cached_cost_usd(
        "claude-sonnet-4-6",
        uncached_tail_input_tokens=0,
        cache_read_input_tokens=0,
        cache_creation_ephemeral_5m=1_000_000,
        cache_creation_ephemeral_1h=0,
        completion_tokens=0,
    )
    assert cost == Decimal("3.750000")


def test_cost_calculation_with_cache_write_1h():
    cost = compute_anthropic_cached_cost_usd(
        "claude-sonnet-4-6",
        uncached_tail_input_tokens=0,
        cache_read_input_tokens=0,
        cache_creation_ephemeral_5m=0,
        cache_creation_ephemeral_1h=1_000_000,
        completion_tokens=0,
    )
    assert cost == Decimal("6.000000")
