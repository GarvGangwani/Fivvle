"""Tests for idea theme classification and original-idea capture."""

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
from app.services.idea_theme_service import (
    _THEME_MODEL,
    _THEME_PROVIDER,
    classify_idea_theme,
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
    ("idea", "theme"),
    [
        ("A dating app for Indian couples tracking milestones", "pink"),
        ("Fintech wallet for SMB payments and investing", "green"),
        ("Food delivery for neighborhood restaurants", "orange"),
        ("A B2B SaaS CRM for logistics fleets", "violet"),
    ],
)
async def test_classify_idea_theme_maps_domains(
    db_session: AsyncSession,
    idea: str,
    theme: str,
) -> None:
    parsed = IdeaThemeOutput(theme=theme)  # type: ignore[arg-type]
    mock_complete = AsyncMock(return_value=(parsed, _make_llm_meta()))

    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await classify_idea_theme(db_session, idea, experiment_id=uuid4())

    assert result == theme
    _, kwargs = mock_complete.call_args
    assert kwargs["provider"] == _THEME_PROVIDER
    assert kwargs["model"] == _THEME_MODEL
    assert kwargs["prompt_name"] == PROMPT_NAME
    assert kwargs["phase"] == "idea_theme"
    assert kwargs["max_tokens"] == 64


@pytest.mark.asyncio
async def test_classify_idea_theme_soft_fails_to_violet(
    db_session: AsyncSession,
) -> None:
    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        AsyncMock(side_effect=RuntimeError("llm down")),
    ):
        result = await classify_idea_theme(db_session, "any idea", experiment_id=uuid4())
    assert result == "violet"


@pytest.mark.asyncio
async def test_classify_idea_theme_empty_input_returns_violet(
    db_session: AsyncSession,
) -> None:
    with patch(
        "app.services.idea_theme_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_complete:
        result = await classify_idea_theme(db_session, "   ")
    assert result == "violet"
    mock_complete.assert_not_called()


@pytest.mark.asyncio
async def test_capture_original_idea_writes_fields_and_freezes_attachments(
    db_session: AsyncSession,
) -> None:
    user, experiment = await _seed_user_experiment(db_session)
    raw_before = experiment.raw_idea
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
        "app.services.idea_capture_service.classify_idea_theme",
        AsyncMock(return_value="pink"),
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
    assert result.idea_theme == "pink"
    assert result.original_idea_captured_at is not None
    assert experiment.original_idea == "A dating app for couples."
    assert experiment.idea_theme == "pink"
    assert experiment.original_idea_captured_at is not None
    assert experiment.raw_idea == raw_before
    assert att.origin_experiment_id == experiment.id
    assert len(result.frozen_attachments) == 1
    assert result.frozen_attachments[0].id == att.id


@pytest.mark.asyncio
async def test_capture_original_idea_second_call_raises_and_preserves(
    db_session: AsyncSession,
) -> None:
    user, experiment = await _seed_user_experiment(db_session)
    experiment.original_idea = "Already frozen"
    experiment.original_idea_captured_at = datetime.now(UTC)
    experiment.idea_theme = "green"
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
    assert experiment.idea_theme == "green"


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
    assert "idea_theme:" not in empty_block

    experiment.original_idea = "Frozen origin text for context"
    experiment.idea_theme = "orange"
    experiment.original_idea_captured_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(experiment)

    ctx = await get_experiment_project_context(db_session, experiment)
    block = ctx.to_prompt_block()
    assert ctx.has_original_idea is True
    assert ctx.idea_theme == "orange"
    assert "has_original_idea: true" in block
    assert "original_idea: Frozen origin text for context" in block
    assert "idea_theme: orange" in block
