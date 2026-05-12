"""Reliability tests for app.llm.client (circuit breakers + retry).

These tests verify the NEW circuit-breaker/retry wiring added in step 5B:
- CircuitOpenError from an open breaker still produces an LLMCall failure row
  (admin dashboards must see breaker-open failures, not silently miss them).
- Retried-then-successful calls produce exactly ONE LLMCall row (for the
  success), not one row per attempt.

Existing test_llm_client.py tests are NOT modified and must continue to pass.
DB fixture pattern is identical to test_llm_client.py.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.llm_call import LLMCall
from app.llm.client import complete
from app.reliability.circuit_breakers import CircuitOpenError, _breakers

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_breakers():
    """Isolate circuit breaker state between tests."""
    _breakers.clear()
    yield
    _breakers.clear()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _DummyAnthropicResponse:
    def __init__(self, text="ok", input_tokens=10, output_tokens=5, rid="msg_test"):
        self.id = rid
        self.content = [MagicMock(text=text)]
        self.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)


class _DummyGroqResponse:
    def __init__(self, text="ok", prompt_tokens=10, completion_tokens=5, rid="groq_test"):
        self.id = rid
        self.choices = [MagicMock(message=MagicMock(content=text))]
        self.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)


# ---------------------------------------------------------------------------
# Anthropic — breaker open produces a failure row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_open_breaker_logs_failure_row(mock_firebase, db_session):
    """When Anthropic breaker is OPEN, complete() raises CircuitOpenError AND writes
    a zero-cost LLMCall row so admin dashboards capture the failure."""
    # Force the Anthropic breaker open by pre-populating failures.
    from app.reliability.circuit_breakers import CircuitBreaker

    breaker = CircuitBreaker(name="anthropic", failure_threshold=1, cooldown_seconds=9999)
    _breakers["anthropic"] = breaker
    # Trigger one failure to open it.
    with pytest.raises(httpx.ConnectError):
        await breaker.call(_raise_connect_error)

    assert breaker._state.value == "open"

    prompt_name = "reliability_test_anthropic_open"
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_DummyAnthropicResponse())

    with patch("app.llm.client._anthropic_client", fake_client):
        with pytest.raises(CircuitOpenError):
            await complete(
                db_session,
                provider="anthropic",
                model="claude-sonnet-4-5",
                prompt_name=prompt_name,
                system="x",
                user="y",
            )
        await db_session.commit()

    stmt = select(LLMCall).where(LLMCall.prompt_name == prompt_name)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == 0
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()

    # SDK was NOT called (breaker rejected the call before reaching it).
    fake_client.messages.create.assert_not_called()


# ---------------------------------------------------------------------------
# Anthropic — retry + eventual success produces exactly one LLMCall row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_retry_then_success_writes_one_row(mock_firebase, db_session):
    """2 transient failures then success → ONE LLMCall row (not three)."""
    fake_response = _DummyAnthropicResponse(rid="msg_retry_success_001")
    call_count = 0

    async def _flaky_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("flaky")
        return fake_response

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(side_effect=_flaky_create)

    with (
        patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock),
        patch("app.llm.client._anthropic_client", fake_client),
    ):
        result = await complete(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="reliability_retry_success",
            system="x",
            user="y",
        )
        await db_session.commit()

    assert result.text == "ok"
    assert call_count == 3  # 2 failures + 1 success

    stmt = select(LLMCall).where(LLMCall.request_id == "msg_retry_success_001")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1  # only the successful call logged
    assert rows[0].cost_usd > Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ---------------------------------------------------------------------------
# Groq — breaker open produces a failure row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_groq_open_breaker_logs_failure_row(mock_firebase, db_session):
    from app.reliability.circuit_breakers import CircuitBreaker

    breaker = CircuitBreaker(name="groq", failure_threshold=1, cooldown_seconds=9999)
    _breakers["groq"] = breaker
    with pytest.raises(httpx.ConnectError):
        await breaker.call(_raise_connect_error)

    prompt_name = "reliability_test_groq_open"
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=_DummyGroqResponse())

    with patch("app.llm.client._groq_client", fake_client):
        with pytest.raises(CircuitOpenError):
            await complete(
                db_session,
                provider="groq",
                model="llama-3.3-70b-versatile",
                prompt_name=prompt_name,
                system="x",
                user="y",
            )
        await db_session.commit()

    stmt = select(LLMCall).where(LLMCall.prompt_name == prompt_name)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ---------------------------------------------------------------------------
# Groq — retry + eventual success produces exactly one LLMCall row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_groq_retry_then_success_writes_one_row(mock_firebase, db_session):
    fake_response = _DummyGroqResponse(rid="groq_retry_success_001")
    call_count = 0

    async def _flaky_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("flaky")
        return fake_response

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=_flaky_create)

    with (
        patch("app.reliability.retry.asyncio.sleep", new_callable=AsyncMock),
        patch("app.llm.client._groq_client", fake_client),
    ):
        result = await complete(
            db_session,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_name="reliability_groq_retry_success",
            system="x",
            user="y",
        )
        await db_session.commit()

    assert result.text == "ok"
    assert call_count == 3

    stmt = select(LLMCall).where(LLMCall.request_id == "groq_retry_success_001")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd > Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

async def _raise_connect_error():
    raise httpx.ConnectError("test error")
