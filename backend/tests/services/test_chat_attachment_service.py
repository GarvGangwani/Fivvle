"""Tests for chat attachment vision extraction."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.user import User
from app.llm.client import LLMResult
from app.services.chat_attachment_service import create_chat_attachment


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _persist_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"attach-{uuid4()}",
        email=f"attach-{uuid4()}@example.com",
        name="Attachment Test User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_image_upload_uses_dedicated_vision_provider(
    db_session: AsyncSession,
) -> None:
    """Image extraction must not depend on refinement_provider."""
    user = await _persist_user(db_session)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
        b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    mock_result = LLMResult(
        text="Screenshot shows a waitlist landing page headline.",
        provider="kimi",
        model="kimi-k2.6",
        prompt_tokens=100,
        completion_tokens=20,
        cost_usd=Decimal("0.001"),
        latency_ms=50,
    )

    with patch(
        "app.services.chat_attachment_service.llm_client.complete_with_image",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as vision_mock:
        result = await create_chat_attachment(
            db_session,
            user=user,
            filename="mockup.png",
            file_bytes=png_bytes,
        )

    vision_mock.assert_awaited_once()
    call_kwargs = vision_mock.await_args.kwargs
    assert call_kwargs["provider"] == "kimi"
    assert call_kwargs["model"] == "kimi-k2.6"
    assert call_kwargs["prompt_name"] == "chat_attachment_image_extract"
    assert result.content_kind == "image"
    assert "waitlist" in result.excerpt
