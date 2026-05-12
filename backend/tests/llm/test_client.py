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

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.llm_call import LLMCall
from app.llm.client import complete_structured
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

    fake_raw = MagicMock()
    fake_raw.id = "msg_acc_single_001"
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

    stmt = select(LLMCall).where(LLMCall.request_id == "msg_acc_single_001")
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
        MagicMock(id="msg_acc_multi_001", usage=MagicMock(input_tokens=120, output_tokens=50)),
    ]

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

    stmt = select(LLMCall).where(LLMCall.request_id == "msg_acc_multi_001")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == expected_prompt
    assert rows[0].completion_tokens == expected_completion
    await db_session.delete(rows[0])
    await db_session.commit()
