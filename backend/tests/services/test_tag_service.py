"""Tests for experiment tag validation and generation routing."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from instructor.core.exceptions import InstructorRetryException
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMResult
from app.llm.prompts.tag_generator import PROMPT_NAME
from app.schemas.tags import TagGeneratorOutput
from app.services.tag_service import (
    _TAG_MODEL,
    _TAG_PROVIDER,
    generate_tags,
    validate_tags,
)


def test_validate_tags_accepts_vocabulary() -> None:
    assert validate_tags(["FINTECH", "B2B"]) == ["FINTECH", "B2B"]


def test_validate_tags_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown tag"):
        validate_tags(["NOT_A_TAG"])


def test_validate_tags_rejects_b2b_and_b2c_together() -> None:
    with pytest.raises(ValueError, match="B2B and B2C"):
        validate_tags(["B2B", "B2C"])


def _make_llm_meta() -> LLMResult:
    """Real LLMResult shape — no total_tokens attribute."""
    return LLMResult(
        text="",
        provider="kimi",
        model="kimi-k2.6",
        prompt_tokens=220,
        completion_tokens=60,
        cost_usd=Decimal("0.000200"),
        latency_ms=450,
    )


@pytest.mark.asyncio
async def test_generate_tags_uses_kimi_k26() -> None:
    db = AsyncMock(spec=AsyncSession)
    parsed = TagGeneratorOutput(tags=["FINTECH", "B2B"])
    mock_meta = _make_llm_meta()
    mock_complete = AsyncMock(return_value=(parsed, mock_meta))

    with patch(
        "app.services.tag_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await generate_tags(
            db,
            "A B2B fintech tool for SMB invoicing.",
            uuid4(),
        )

    assert result == ["FINTECH", "B2B"]
    mock_complete.assert_awaited_once()
    _, call_kwargs = mock_complete.call_args
    assert call_kwargs["provider"] == _TAG_PROVIDER
    assert call_kwargs["model"] == _TAG_MODEL
    assert call_kwargs["prompt_name"] == PROMPT_NAME
    assert call_kwargs["phase"] == "refinement"


@pytest.mark.asyncio
async def test_generate_tags_falls_back_to_anthropic_on_json_shape_error() -> None:
    db = AsyncMock(spec=AsyncSession)
    parsed = TagGeneratorOutput(tags=["SAAS", "B2B"])
    mock_meta = _make_llm_meta()
    json_exc = InstructorRetryException(
        "Invalid JSON: json_invalid",
        n_attempts=3,
        total_usage=MagicMock(prompt_tokens=200, completion_tokens=40),
        failed_attempts=[],
    )
    mock_complete = AsyncMock(
        side_effect=[
            json_exc,
            (parsed, mock_meta),
        ]
    )

    with patch(
        "app.services.tag_service.llm_client.complete_structured",
        mock_complete,
    ):
        result = await generate_tags(db, "Enterprise SaaS for HR teams.", uuid4())

    assert result == ["SAAS", "B2B"]
    assert mock_complete.await_count == 2
    first_kwargs = mock_complete.await_args_list[0].kwargs
    second_kwargs = mock_complete.await_args_list[1].kwargs
    assert first_kwargs["provider"] == "kimi"
    assert first_kwargs["model"] == "kimi-k2.6"
    assert second_kwargs["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_generate_tags_returns_empty_on_empty_input() -> None:
    db = AsyncMock(spec=AsyncSession)
    with patch(
        "app.services.tag_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_complete:
        result = await generate_tags(db, "   ", uuid4())
    assert result == []
    mock_complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_tags_does_not_raise_on_real_llm_result_shape() -> None:
    """Regression: LLMResult has no total_tokens — must not fail the happy path."""
    db = AsyncMock(spec=AsyncSession)
    parsed = TagGeneratorOutput(tags=["CREATOR", "B2C", "MARKETPLACE"])
    meta = _make_llm_meta()
    assert not hasattr(meta, "total_tokens")

    with patch(
        "app.services.tag_service.llm_client.complete_structured",
        AsyncMock(return_value=(parsed, meta)),
    ):
        result = await generate_tags(db, "Crowdfunding for indie filmmakers.", uuid4())

    assert result == ["CREATOR", "B2C", "MARKETPLACE"]


@pytest.mark.asyncio
async def test_generate_tags_returns_empty_when_logger_raises() -> None:
    """Soft-fail must survive even if the failure logger itself raises."""
    db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "app.services.tag_service.llm_client.complete_structured",
            AsyncMock(side_effect=RuntimeError("upstream boom")),
        ),
        patch(
            "app.services.tag_service._logger.warning",
            side_effect=UnicodeEncodeError("charmap", "x", 0, 1, "boom"),
        ),
    ):
        result = await generate_tags(db, "Some idea text", uuid4())

    assert result == []
