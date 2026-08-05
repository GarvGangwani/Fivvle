"""Tests for canvas palette classification and original-idea capture."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.chat_attachment import ChatAttachment
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.llm.client import LLMResult
from app.llm.prompts.idea_theme import PROMPT_NAME
from app.schemas.idea_capture import IdeaThemeOutput
from app.services.idea_capture_service import (
    IdeaAlreadyCapturedError,
    capture_original_idea,
)
from app.services.idea_theme_palettes import (
    DEFAULT_THEME_PALETTE,
    THEME_PALETTES,
)
from app.services.idea_theme_service import (
    _THEME_MODEL,
    _THEME_PROVIDER,
    classify_theme_palette,
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


def _make_llm_meta() -> LLMResult:
    return LLMResult(
        text="",
        provider="kimi",
        model="kimi-k2.6",
        prompt_tokens=40,
        completion_tokens=5,
        cost_usd=Decimal("0.000050"),
        latency_ms=120,
    )


async def _seed_user_experiment(db: AsyncSession) -> tuple[User, Experiment]:
    user = User(
        firebase_uid=f"fb-{uuid4()}",
        email=f"{uuid4()}@example.com",
    )
    db.add(user)
    await db.flush()
    experiment = Experiment(
        user_id=user.id,
        raw_idea="",
        name="Capture Test",
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    await db.refresh(user)
    return user, experiment


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("idea", "palette"),
    [
        ("A dating app for Indian couples tracking milestones", "rose"),
        ("Fintech wallet for SMB payments and investing", "emerald"),
        ("Food delivery for neighborhood restaurants", "amber"),
        ("A project tracker for remote product teams", "sky"),
        ("A co-op roguelike with cross-platform matchmaking", "crimson"),
        ("Habit tracker for physiotherapy patients", "teal"),
        ("Spaced-repetition tutor for high school physics", "indigo"),
        ("A B2B CRM for logistics fleets", "founder-purple"),
    ],
)
async def test_classify_theme_palette_maps_domains(
    db_session: AsyncSession,
    idea: str,
    palette: str,
) -> None:
    parsed = IdeaThemeOutput(theme=palette)  # type: ignore[arg-type]
    mock_complete = AsyncMock(return_value=(parsed, _make_llm_meta()))

    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await classify_theme_palette(db_session, idea, experiment_id=uuid4())

    assert result == palette
    assert result in THEME_PALETTES
    _, kwargs = mock_complete.call_args
    assert kwargs["provider"] == _THEME_PROVIDER
    assert kwargs["model"] == _THEME_MODEL
    assert kwargs["prompt_name"] == PROMPT_NAME
    assert kwargs["phase"] == "idea_theme"
    assert kwargs["max_tokens"] == 64


@pytest.mark.asyncio
async def test_classify_theme_palette_soft_fails_to_default(
    db_session: AsyncSession,
) -> None:
    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        AsyncMock(side_effect=RuntimeError("llm down")),
    ):
        result = await classify_theme_palette(
            db_session,
            "any idea",
            experiment_id=uuid4(),
        )
    assert result == DEFAULT_THEME_PALETTE


@pytest.mark.asyncio
async def test_classify_theme_palette_rejects_unknown_name(
    db_session: AsyncSession,
) -> None:
    """A palette outside the curated set must not reach the canvas."""
    parsed = IdeaThemeOutput.model_construct(theme="chartreuse")

    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        AsyncMock(return_value=(parsed, _make_llm_meta())),
    ):
        result = await classify_theme_palette(db_session, "an idea")
    assert result == DEFAULT_THEME_PALETTE


@pytest.mark.asyncio
async def test_classify_theme_palette_empty_input_returns_default(
    db_session: AsyncSession,
) -> None:
    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_complete:
        result = await classify_theme_palette(db_session, "   ")
    assert result == DEFAULT_THEME_PALETTE
    mock_complete.assert_not_called()


@pytest.mark.asyncio
async def test_capture_original_idea_writes_fields_and_freezes_attachments(
    db_session: AsyncSession,
) -> None:
    user, experiment = await _seed_user_experiment(db_session)
    att = ChatAttachment(
        user_id=user.id,
        original_filename="moodboard.png",
        content_kind="image",
        media_type="image/png",
        extracted_text="",
    )
    db_session.add(att)
    await db_session.commit()
    await db_session.refresh(att)

    with patch(
        "app.services.idea_capture_service.classify_theme_palette",
        AsyncMock(return_value="rose"),
    ):
        result = await capture_original_idea(
            db_session,
            experiment=experiment,
            user_id=user.id,
            idea_text="  A dating app for couples.  ",
            attachment_ids=[att.id],
        )

    await db_session.refresh(experiment)
    await db_session.refresh(att)

    assert result.original_idea == "A dating app for couples."
    assert result.suggested_palette == "rose"
    assert result.user_message_id is not None
    assert result.original_idea_captured_at is not None
    assert experiment.original_idea == "A dating app for couples."
    assert experiment.suggested_palette == "rose"
    # Suggestion only — the canvas stays on the default until the founder accepts.
    assert experiment.theme_palette is None
    assert experiment.original_idea_captured_at is not None
    assert experiment.raw_idea == "A dating app for couples."
    assert att.origin_experiment_id == experiment.id
    assert len(result.frozen_attachments) == 1
    assert result.frozen_attachments[0].id == att.id

    from app.db.enums import ChatRole
    from app.db.models.chat_message import ChatMessage

    user_msg = await db_session.get(ChatMessage, result.user_message_id)
    assert user_msg is not None
    assert user_msg.role == ChatRole.USER
    assert user_msg.content == "A dating app for couples."
    assert user_msg.metadata_json is not None
    assert user_msg.metadata_json.get("capture_submission") is True
    assert len(user_msg.metadata_json.get("attachments") or []) == 1


@pytest.mark.asyncio
async def test_capture_original_idea_second_call_raises_and_preserves(
    db_session: AsyncSession,
) -> None:
    user, experiment = await _seed_user_experiment(db_session)
    experiment.original_idea = "Already frozen"
    experiment.original_idea_captured_at = datetime.now(UTC)
    experiment.suggested_palette = "emerald"
    await db_session.commit()
    await db_session.refresh(experiment)

    with pytest.raises(IdeaAlreadyCapturedError):
        await capture_original_idea(
            db_session,
            experiment=experiment,
            user_id=user.id,
            idea_text="Should not overwrite",
            attachment_ids=[],
        )

    await db_session.refresh(experiment)
    assert experiment.original_idea == "Already frozen"
    assert experiment.suggested_palette == "emerald"


@pytest.mark.asyncio
async def test_project_context_exposes_original_idea_flags(
    db_session: AsyncSession,
) -> None:
    from app.services.experiment_project_context import get_experiment_project_context

    _user, experiment = await _seed_user_experiment(db_session)
    ctx_empty = await get_experiment_project_context(db_session, experiment)
    empty_block = ctx_empty.to_prompt_block()
    assert ctx_empty.has_original_idea is False
    assert "has_original_idea: false" in empty_block
    assert "\noriginal_idea:" not in empty_block
    assert not empty_block.startswith("original_idea:")

    experiment.original_idea = "Frozen origin text for context"
    experiment.original_idea_captured_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(experiment)

    ctx = await get_experiment_project_context(db_session, experiment)
    block = ctx.to_prompt_block()
    assert ctx.has_original_idea is True
    assert "has_original_idea: true" in block
    assert "original_idea: Frozen origin text for context" in block
    # Palette is presentation-only — it must not leak into the LLM context.
    assert "palette" not in block
