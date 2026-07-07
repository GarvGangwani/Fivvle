"""Unit tests for subreddit_selection_service."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.subreddit_selection_hint import SubredditSelectionHint
from app.schemas.subreddit_selection import SubredditSelectionDraft
from app.services.subreddit_selection_service import (
    _normalize_key,
    get_subreddits_for_topic,
)


def _mock_llm_meta() -> MagicMock:
    meta = MagicMock()
    meta.cost_usd = Decimal("0.002")
    meta.latency_ms = 100
    return meta


@pytest.mark.asyncio
async def test_cache_hit_returns_subreddits_without_llm() -> None:
    db = AsyncMock()
    row = SubredditSelectionHint(
        normalized_key="saas for nurses||india",
        original_topic="saas for nurses",
        original_geography="India",
        subreddits=["india", "startups"],
        rationale="test",
        model_used="kimi:kimi-k2.6",
    )
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "app.services.subreddit_selection_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_llm:
        subs = await get_subreddits_for_topic(
            db, topic="SaaS for nurses", geography="India"
        )

    assert subs == ["india", "startups"]
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_cache_miss_llm_success_persists() -> None:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.flush = AsyncMock()
    nested = MagicMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    db.begin_nested = MagicMock(return_value=nested)

    draft = SubredditSelectionDraft(
        subreddits=["r/India", "startups"],
        rationale="India founders",
    )

    with patch(
        "app.services.subreddit_selection_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _mock_llm_meta())),
    ):
        subs = await get_subreddits_for_topic(
            db, topic="  SaaS for nurses  ", geography="India", experiment_id=uuid4()
        )

    assert subs == ["india", "startups"]
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_cache_miss_llm_failure_returns_empty() -> None:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "app.services.subreddit_selection_service.llm_client.complete_structured",
        AsyncMock(side_effect=RuntimeError("down")),
    ):
        subs = await get_subreddits_for_topic(db, topic="topic", geography=None)

    assert subs == []
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_race_condition_uses_winner_row() -> None:
    db = AsyncMock()
    winner = SubredditSelectionHint(
        normalized_key="topic||",
        original_topic="topic",
        original_geography=None,
        subreddits=["startups"],
        rationale="",
        model_used="kimi:kimi-k2.6",
    )

    first = MagicMock()
    first.scalar_one_or_none.return_value = None
    second = MagicMock()
    second.scalar_one_or_none.return_value = winner
    db.execute = AsyncMock(side_effect=[first, second])
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))
    db.begin_nested = MagicMock()
    nested = AsyncMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    db.begin_nested.return_value = nested

    draft = SubredditSelectionDraft(subreddits=["startups"], rationale="")

    with patch(
        "app.services.subreddit_selection_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _mock_llm_meta())),
    ):
        subs = await get_subreddits_for_topic(db, topic="topic", geography=None)

    assert subs == ["startups"]


def test_normalization_collapses_whitespace_and_case() -> None:
    a = _normalize_key("  SaaS Tool  ", "  India  ")
    b = _normalize_key("saas tool", "india")
    assert a == b
