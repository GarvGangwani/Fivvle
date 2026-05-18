"""Tests for app.llm.client.

All provider SDK calls are mocked. We're testing the WRAPPER behavior:
- LLMCall row is created on every call (success and failure)
- Cost computation matches the pricing table
- Failures are logged with zero tokens but still re-raised
- Unknown models produce a warning but still log
"""

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anthropic
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.llm_call import LLMCall
from app.llm.client import complete, complete_structured
from app.llm.cost import compute_cost_usd
from pydantic import BaseModel
from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID  # noqa: F401


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Standalone async session per LLM test.

    The module-level _sessionmaker may be None if a prior TestClient fixture
    ran its lifespan shutdown (which calls dispose_engine). Creating a fresh
    engine here avoids any dependency on lifespan ordering — same pattern
    used by _cleanup_test_users in conftest.
    """
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


class _DummyAnthropicResponse:
    """Mimics the shape of anthropic.types.Message."""

    def __init__(self, text: str, input_tokens: int, output_tokens: int, request_id: str):
        self.id = request_id
        self.content = [MagicMock(text=text)]
        self.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)


class _DummyGroqResponse:
    """Mimics the shape of groq.types.chat.ChatCompletion."""

    def __init__(self, text: str, prompt_tokens: int, completion_tokens: int, request_id: str):
        self.id = request_id
        self.choices = [MagicMock(message=MagicMock(content=text))]
        self.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)


@pytest.mark.asyncio
async def test_anthropic_complete_logs_cost(mock_firebase, db_session):
    """Successful anthropic call writes one LLMCall row with non-zero cost."""
    fake_response = _DummyAnthropicResponse(
        text="Hello",
        input_tokens=100,
        output_tokens=50,
        request_id="msg_test_001",
    )

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    with patch("app.llm.client._anthropic_client", fake_client):
        result = await complete(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="test_prompt",
            system="be brief",
            user="hi",
        )
        await db_session.commit()

    assert result.text == "Hello"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50
    assert result.cost_usd > Decimal("0")

    stmt = select(LLMCall).where(LLMCall.request_id == "msg_test_001")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].provider == "anthropic"
    assert rows[0].cost_usd > Decimal("0")
    await db_session.delete(rows[0])
    await db_session.commit()


@pytest.mark.asyncio
async def test_groq_complete_logs_cost(mock_firebase, db_session):
    """Successful groq call writes one LLMCall row with non-zero cost."""
    fake_response = _DummyGroqResponse(
        text="reply",
        prompt_tokens=200,
        completion_tokens=100,
        request_id="groq_test_001",
    )

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("app.llm.client._groq_client", fake_client):
        result = await complete(
            db_session,
            provider="groq",
            model="llama-3.3-70b-versatile",
            prompt_name="test_prompt",
            system="be brief",
            user="hi",
        )
        await db_session.commit()

    assert result.text == "reply"
    assert result.prompt_tokens == 200
    assert result.completion_tokens == 100
    assert result.cost_usd > Decimal("0")

    stmt = select(LLMCall).where(LLMCall.request_id == "groq_test_001")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd > Decimal("0")
    await db_session.delete(rows[0])
    await db_session.commit()


@pytest.mark.asyncio
async def test_failed_call_logs_zero_cost_row(mock_firebase, db_session):
    """When the provider raises, we still log a zero-cost row and re-raise."""
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=MagicMock())
    )

    with patch("app.llm.client._anthropic_client", fake_client):
        with pytest.raises(anthropic.APIConnectionError):
            await complete(
                db_session,
                provider="anthropic",
                model="claude-sonnet-4-5",
                prompt_name="failing_prompt",
                system="x",
                user="y",
            )
        await db_session.commit()

    stmt = select(LLMCall).where(LLMCall.prompt_name == "failing_prompt")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].prompt_tokens == 0
    assert rows[0].completion_tokens == 0
    assert rows[0].cost_usd == Decimal("0")
    await db_session.delete(rows[0])
    await db_session.commit()


@pytest.mark.asyncio
async def test_unknown_model_still_logs(mock_firebase, db_session):
    """Unknown model pair produces a warning log but still writes a LLMCall row."""
    fake_response = _DummyAnthropicResponse(
        text="ok",
        input_tokens=10,
        output_tokens=5,
        request_id="msg_unknown_model_001",
    )

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    with patch("app.llm.client._anthropic_client", fake_client):
        result = await complete(
            db_session,
            provider="anthropic",
            model="claude-future-model-9999",
            prompt_name="unknown_model_prompt",
            system="test",
            user="test",
        )
        await db_session.commit()

    # Cost is zero because model isn't in the pricing table
    assert result.cost_usd == Decimal("0")

    stmt = select(LLMCall).where(LLMCall.request_id == "msg_unknown_model_001")
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost_usd == Decimal("0")
    await db_session.delete(rows[0])
    await db_session.commit()


@pytest.mark.asyncio
async def test_complete_structured_logs_cost(mock_firebase, db_session):
    """Successful structured call via mocked instructor writes a LLMCall row."""

    class _Reply(BaseModel):
        message: str

    parsed_instance = _Reply(message="structured reply")

    req_id = f"msg_structured_001_{uuid4()}"
    fake_raw = MagicMock()
    fake_raw.id = req_id
    fake_raw.usage.input_tokens = 80
    fake_raw.usage.output_tokens = 40

    fake_instructor = MagicMock()
    fake_instructor.create_with_completion = AsyncMock(
        return_value=(parsed_instance, fake_raw)
    )

    with patch("app.llm.client._instructor_anthropic_client", fake_instructor):
        parsed, meta = await complete_structured(
            db_session,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="structured_test",
            system="respond with JSON",
            user="give me a message",
            response_model=_Reply,
        )
        await db_session.commit()

    assert parsed.message == "structured reply"
    assert meta.prompt_tokens == 80
    assert meta.completion_tokens == 40
    assert meta.cost_usd > Decimal("0")

    stmt = select(LLMCall).where(LLMCall.request_id == req_id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].provider == "anthropic"
    assert rows[0].cost_usd > Decimal("0")
    await db_session.delete(rows[0])
    await db_session.commit()


def test_compute_cost_known_model():
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-5", 1_000_000, 1_000_000)
    # input + output = 3.00 + 15.00 = 18.00 USD for 1M each
    assert cost == Decimal("18.000000")


def test_compute_cost_unknown_model_returns_zero():
    cost = compute_cost_usd("anthropic", "claude-future-model-9000", 1000, 500)
    assert cost == Decimal("0")
