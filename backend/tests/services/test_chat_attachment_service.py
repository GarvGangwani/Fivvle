"""Tests for chat attachment upload + deferred vision extraction."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.chat_attachment import ChatAttachment
from app.db.models.user import User
from app.llm.client import LLMResult
from app.services import chat_attachment_service as attach_svc
from app.services.chat_attachment_service import (
    create_chat_attachment,
    resolve_chat_attachments,
    schedule_deferred_image_extraction,
)


@pytest.fixture(autouse=True)
def _clear_pending_images() -> None:
    attach_svc._pending_images.clear()
    yield
    attach_svc._pending_images.clear()


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


_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

_MOCK_VISION = LLMResult(
    text="Screenshot shows a waitlist landing page headline.",
    provider="kimi",
    model="kimi-k2.6",
    prompt_tokens=100,
    completion_tokens=20,
    cost_usd=Decimal("0.001"),
    latency_ms=50,
)


@pytest.mark.asyncio
async def test_image_upload_defers_vision_call(
    db_session: AsyncSession,
) -> None:
    """Upload must return before vision; extraction runs after schedule."""
    user = await _persist_user(db_session)

    with patch(
        "app.services.chat_attachment_service.llm_client.complete_with_image",
        new_callable=AsyncMock,
        return_value=_MOCK_VISION,
    ) as vision_mock:
        result = await create_chat_attachment(
            db_session,
            user=user,
            filename="mockup.png",
            file_bytes=_PNG_BYTES,
        )
        await db_session.commit()

        assert result.content_kind == "image"
        assert result.char_count == 0
        assert result.id in attach_svc._pending_images
        vision_mock.assert_not_awaited()

        schedule_deferred_image_extraction(result.id)
        pending = attach_svc._pending_images[result.id]
        assert pending.task is not None
        await pending.task

        vision_mock.assert_awaited_once()
        call_kwargs = vision_mock.await_args.kwargs
        assert call_kwargs["provider"] == "kimi"
        assert call_kwargs["model"] == "kimi-k2.6"
        assert call_kwargs["prompt_name"] == "chat_attachment_image_extract"
        assert call_kwargs["max_tokens"] == 384

        row = await db_session.get(ChatAttachment, result.id)
        assert row is not None
        await db_session.refresh(row)
        assert "waitlist" in row.extracted_text


@pytest.mark.asyncio
async def test_resolve_awaits_deferred_image_extraction(
    db_session: AsyncSession,
) -> None:
    user = await _persist_user(db_session)

    with patch(
        "app.services.chat_attachment_service.llm_client.complete_with_image",
        new_callable=AsyncMock,
        return_value=_MOCK_VISION,
    ) as vision_mock:
        uploaded = await create_chat_attachment(
            db_session,
            user=user,
            filename="ui.png",
            file_bytes=_PNG_BYTES,
        )
        await db_session.commit()
        schedule_deferred_image_extraction(uploaded.id)

        resolved = await resolve_chat_attachments(
            db_session,
            user=user,
            attachment_ids=[uploaded.id],
        )
        await db_session.commit()

    assert len(resolved) == 1
    assert "waitlist" in resolved[0].extracted_text
    vision_mock.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_extracts_on_demand_if_not_scheduled(
    db_session: AsyncSession,
) -> None:
    """If background never started, resolve extracts with held bytes."""
    user = await _persist_user(db_session)

    with patch(
        "app.services.chat_attachment_service.llm_client.complete_with_image",
        new_callable=AsyncMock,
        return_value=_MOCK_VISION,
    ) as vision_mock:
        uploaded = await create_chat_attachment(
            db_session,
            user=user,
            filename="late.png",
            file_bytes=_PNG_BYTES,
        )
        await db_session.commit()
        # Intentionally do not schedule — on-demand path.
        resolved = await resolve_chat_attachments(
            db_session,
            user=user,
            attachment_ids=[uploaded.id],
        )
        await db_session.commit()

    assert resolved[0].extracted_text.startswith("Screenshot")
    vision_mock.assert_awaited_once()
