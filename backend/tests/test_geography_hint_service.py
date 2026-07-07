"""Unit tests for geography_hint_service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.geography_source_hint import GeographySourceHint
from app.db.models.llm_call import LLMCall
from app.schemas.geography_hint import GeographyHintDraft
from app.services.geography_hint_service import (
    _normalize_geography,
    get_include_domains_for_geography,
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh async session per test; independent of FastAPI lifespan."""
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _mock_llm_meta() -> MagicMock:
    meta = MagicMock()
    meta.cost_usd = Decimal("0.002")
    meta.latency_ms = 120
    return meta


def _cached_row(
    *,
    normalized_key: str = "india",
    domains: list[str] | None = None,
) -> GeographySourceHint:
    return GeographySourceHint(
        normalized_key=normalized_key,
        original_geography="India",
        include_domains=domains or ["livemint.com", "inc42.com"],
        rationale="Local business press",
        model_used="anthropic:claude-haiku-4-5",
    )


@pytest.mark.asyncio
async def test_empty_raw_geography_returns_empty_without_llm() -> None:
    db = AsyncMock(spec=AsyncSession)
    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_llm:
        assert await get_include_domains_for_geography(db, "") == []
        assert await get_include_domains_for_geography(db, "   ") == []
    mock_llm.assert_not_called()
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_too_short_or_long_normalized_returns_empty() -> None:
    db = AsyncMock(spec=AsyncSession)
    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_llm:
        assert await get_include_domains_for_geography(db, "x") == []
        assert await get_include_domains_for_geography(db, "a" * 201) == []
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_cache_hit_returns_domains_without_llm() -> None:
    db = AsyncMock(spec=AsyncSession)
    row = _cached_row()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(),
    ) as mock_llm:
        domains = await get_include_domains_for_geography(db, "India")

    assert domains == ["livemint.com", "inc42.com"]
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_cache_miss_persists_and_returns_sanitized_domains() -> None:
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.flush = AsyncMock()

    draft = GeographyHintDraft(
        include_domains=[
            "HTTPS://WWW.LiveMint.com/markets",
            "inc42.com",
            "inc42.com",
        ],
        rationale="India startup press",
    )

    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _mock_llm_meta())),
    ):
        domains = await get_include_domains_for_geography(db, "  India  ")

    assert domains == ["livemint.com", "inc42.com"]
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, GeographySourceHint)
    assert added.normalized_key == "india"
    assert added.original_geography == "  India  "[:200]


@pytest.mark.asyncio
async def test_llm_failure_returns_empty_without_persisting() -> None:
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(side_effect=RuntimeError("provider down")),
    ):
        domains = await get_include_domains_for_geography(db, "Japan")

    assert domains == []
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_domain_sanitization_rejects_garbage() -> None:
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.flush = AsyncMock()

    draft = GeographyHintDraft(
        include_domains=["not a domain", "bad", "valid.jp"],
        rationale="",
    )

    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _mock_llm_meta())),
    ):
        domains = await get_include_domains_for_geography(db, "Japan")

    assert domains == ["valid.jp"]
    added = db.add.call_args[0][0]
    assert added.include_domains == ["valid.jp"]


@pytest.mark.asyncio
async def test_integrity_error_race_reads_winner() -> None:
    db = AsyncMock(spec=AsyncSession)
    winner = _cached_row(domains=["winner.com"])
    call_num = 0

    async def execute_side_effect(*_args, **_kwargs):
        nonlocal call_num
        call_num += 1
        result = MagicMock()
        if call_num == 1:
            result.scalar_one_or_none.return_value = None
        else:
            result.scalar_one_or_none.return_value = winner
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))
    db.rollback = AsyncMock()

    draft = GeographyHintDraft(include_domains=["loser.com"], rationale="")

    with patch(
        "app.services.geography_hint_service.llm_client.complete_structured",
        AsyncMock(return_value=(draft, _mock_llm_meta())),
    ):
        domains = await get_include_domains_for_geography(db, "India")

    assert domains == ["winner.com"]


@pytest.mark.asyncio
async def test_race_condition_preserves_outer_transaction(db_session: AsyncSession) -> None:
    """SAVEPOINT rollback must not undo the caller's outer transaction."""
    sentinel_id = uuid4()
    winner = GeographySourceHint(
        normalized_key="india",
        original_geography="India",
        include_domains=["winner.com", "inc42.com"],
        rationale="Pre-seeded winner",
        model_used="anthropic:claude-haiku-4-5",
    )

    trans = await db_session.begin()
    try:
        db_session.add(
            LLMCall(
                id=sentinel_id,
                provider="anthropic",
                model="claude-haiku-4-5",
                prompt_name="sentinel",
                prompt_tokens=1,
                completion_tokens=1,
                cost_usd=Decimal("0.000001"),
                latency_ms=1,
                phase="geography_hint",
            )
        )
        db_session.add(winner)
        await db_session.flush()

        call_num = 0

        async def _get_cached_side_effect(
            _db: AsyncSession, _normalized_key: str
        ) -> GeographySourceHint | None:
            nonlocal call_num
            call_num += 1
            if call_num == 1:
                return None
            return winner

        draft = GeographyHintDraft(include_domains=["loser.com"], rationale="")

        with (
            patch(
                "app.services.geography_hint_service._get_cached",
                AsyncMock(side_effect=_get_cached_side_effect),
            ),
            patch(
                "app.services.geography_hint_service.llm_client.complete_structured",
                AsyncMock(return_value=(draft, _mock_llm_meta())),
            ),
        ):
            domains = await get_include_domains_for_geography(db_session, "India")

        assert domains == ["winner.com", "inc42.com"]
        sentinel = (
            await db_session.execute(select(LLMCall).where(LLMCall.id == sentinel_id))
        ).scalar_one_or_none()
        assert sentinel is not None
    finally:
        await trans.rollback()


def test_normalization_collapses_case_and_whitespace() -> None:
    assert _normalize_geography("India") == "india"
    assert _normalize_geography("  India  ") == "india"
    assert _normalize_geography("INDIA") == "india"


def test_normalization_keeps_tier_variants_distinct() -> None:
    assert _normalize_geography("India") != _normalize_geography("India - tier 1 cities")
