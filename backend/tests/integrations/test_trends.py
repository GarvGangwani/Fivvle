"""Wrapper-only tests for app.integrations.trends (ADR 0015)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pandas as pd
import pytest
from pytrends.exceptions import ResponseError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.external_api_call import ExternalAPICall
from app.integrations.trends import fetch_trends
from app.reliability.circuit_breakers import CircuitBreaker, _breakers
from app.schemas.search import TrendsSeries


@pytest.fixture(autouse=True)
def _reset_pytrends_breaker() -> None:
    _breakers.pop("pytrends", None)
    yield
    _breakers.pop("pytrends", None)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _make_trends_df(keywords: list[str], *, values: dict[str, list[int]] | None = None) -> pd.DataFrame:
    dates = pd.to_datetime(["2025-01-01", "2025-01-08"])
    data: dict[str, list[int] | bool] = {}
    for kw in keywords:
        data[kw] = (values or {}).get(kw, [50, 75])
    data["isPartial"] = [False, False]
    return pd.DataFrame(data, index=dates)


async def _pytrends_ids_before(session: AsyncSession) -> set[UUID]:
    stmt = select(ExternalAPICall.id).where(ExternalAPICall.provider == "pytrends")
    return set((await session.execute(stmt)).scalars().all())


@pytest.mark.asyncio
async def test_fetch_trends_happy_path(db_session: AsyncSession) -> None:
    pre_ids = await _pytrends_ids_before(db_session)
    keywords = ["startup", "MVP"]
    fake_df = _make_trends_df(keywords)

    mock_instance = MagicMock()
    mock_instance.build_payload = MagicMock()
    mock_instance.interest_over_time = MagicMock(return_value=fake_df)
    mock_trend_req = MagicMock(return_value=mock_instance)

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, keywords)
        await db_session.commit()

    assert result is not None
    assert set(result.keys()) == set(keywords)
    assert all(isinstance(s, TrendsSeries) for s in result.values())
    assert result["startup"].points[0].value == 50
    assert result["startup"].points[1].value == 75

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "pytrends")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].operation == "fetch_trends"
    assert rows[0].success is True
    assert rows[0].cost_usd == Decimal("0")
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_fetch_trends_transient_response_error_succeeds_on_third_retry(
    db_session: AsyncSession,
) -> None:
    pre_ids = await _pytrends_ids_before(db_session)
    keywords = ["saas"]
    fake_df = _make_trends_df(keywords)

    mock_instance = MagicMock()
    mock_instance.build_payload = MagicMock()
    mock_instance.interest_over_time = MagicMock(
        side_effect=[
            ResponseError("flaky", MagicMock()),
            ResponseError("flaky", MagicMock()),
            fake_df,
        ]
    )
    mock_trend_req = MagicMock(return_value=mock_instance)

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, keywords)
        await db_session.commit()

    assert result is not None
    assert "saas" in result
    assert mock_instance.interest_over_time.call_count == 3

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "pytrends")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is True
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_fetch_trends_persistent_response_error_returns_none(
    db_session: AsyncSession,
) -> None:
    pre_ids = await _pytrends_ids_before(db_session)
    keywords = ["niche"]

    mock_instance = MagicMock()
    mock_instance.build_payload = MagicMock()
    mock_instance.interest_over_time = MagicMock(
        side_effect=ResponseError("persistent", MagicMock())
    )
    mock_trend_req = MagicMock(return_value=mock_instance)

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, keywords)
        await db_session.commit()

    assert result is None
    assert mock_instance.interest_over_time.call_count == 4  # initial + 3 retries

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "pytrends")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_fetch_trends_circuit_breaker_open_returns_none(db_session: AsyncSession) -> None:
    pre_ids = await _pytrends_ids_before(db_session)
    keywords = ["blocked"]

    breaker = CircuitBreaker(name="pytrends", failure_threshold=5, cooldown_seconds=9999)
    _breakers["pytrends"] = breaker

    async def _fail() -> None:
        raise ResponseError("open circuit", MagicMock())

    for _ in range(5):
        with pytest.raises(ResponseError):
            await breaker.call(_fail)

    mock_trend_req = MagicMock()

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, keywords)
        await db_session.commit()

    assert result is None
    mock_trend_req.assert_not_called()

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "pytrends")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    for row in rows:
        await db_session.delete(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_fetch_trends_empty_keywords_returns_none_without_api_call(
    db_session: AsyncSession,
) -> None:
    pre_ids = await _pytrends_ids_before(db_session)
    mock_trend_req = MagicMock()

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, [])
        await db_session.commit()

    assert result is None
    mock_trend_req.assert_not_called()

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "pytrends")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_fetch_trends_empty_dataframe_returns_empty_points(db_session: AsyncSession) -> None:
    keywords = ["quiet"]
    empty_df = pd.DataFrame()

    mock_instance = MagicMock()
    mock_instance.build_payload = MagicMock()
    mock_instance.interest_over_time = MagicMock(return_value=empty_df)
    mock_trend_req = MagicMock(return_value=mock_instance)

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, keywords)
        await db_session.commit()

    assert result is not None
    assert result["quiet"].points == []


@pytest.mark.asyncio
async def test_fetch_trends_schema_validation_failure_returns_none(
    db_session: AsyncSession,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pre_ids = await _pytrends_ids_before(db_session)
    keywords = ["bad-value"]
    fake_df = _make_trends_df(keywords, values={"bad-value": [50, 150]})

    mock_instance = MagicMock()
    mock_instance.build_payload = MagicMock()
    mock_instance.interest_over_time = MagicMock(return_value=fake_df)
    mock_trend_req = MagicMock(return_value=mock_instance)

    with patch("pytrends.request.TrendReq", mock_trend_req):
        result = await fetch_trends(db_session, keywords)
        await db_session.commit()

    assert result is None
    captured = capsys.readouterr()
    assert "schema validation failed" in captured.out

    stmt = select(ExternalAPICall).where(ExternalAPICall.provider == "pytrends")
    if pre_ids:
        stmt = stmt.where(~ExternalAPICall.id.in_(pre_ids))
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_fetch_trends_concurrent_calls_use_independent_trend_req_instances() -> None:
    keywords_a = ["alpha"]
    keywords_b = ["beta"]
    instances: list[MagicMock] = []

    shared_df = _make_trends_df(["alpha", "beta"])

    def _factory(*_args: object, **_kwargs: object) -> MagicMock:
        inst = MagicMock()
        inst.build_payload = MagicMock()
        inst.interest_over_time = MagicMock(return_value=shared_df)
        instances.append(inst)
        return inst

    mock_trend_req = MagicMock(side_effect=_factory)
    engine = create_async_engine(get_settings().database_url, pool_size=2, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _fetch(keywords: list[str]) -> dict[str, TrendsSeries] | None:
        async with sm() as session:
            with patch("pytrends.request.TrendReq", mock_trend_req):
                return await fetch_trends(session, keywords)

    try:
        with patch("pytrends.request.TrendReq", mock_trend_req):
            await asyncio.gather(_fetch(keywords_a), _fetch(keywords_b))
    finally:
        await engine.dispose()

    assert len(instances) == 2
    assert instances[0] is not instances[1]


@pytest.mark.asyncio
async def test_fetch_trends_logging_never_contains_raw_keywords(
    db_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_a = f"secret-keyword-{uuid4().hex}"
    secret_b = f"another-secret-{uuid4().hex}"
    fake_df = _make_trends_df([secret_a, secret_b])

    mock_instance = MagicMock()
    mock_instance.build_payload = MagicMock()
    mock_instance.interest_over_time = MagicMock(return_value=fake_df)
    mock_trend_req = MagicMock(return_value=mock_instance)

    with patch("pytrends.request.TrendReq", mock_trend_req):
        with caplog.at_level("INFO"):
            await fetch_trends(db_session, [secret_a, secret_b])
        await db_session.commit()

    log_blob = " ".join(f"{r.getMessage()} {r.message}" for r in caplog.records)
    assert secret_a not in log_blob
    assert secret_b not in log_blob
