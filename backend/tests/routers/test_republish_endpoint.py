"""Tests for POST /experiments/{id}/landing-page/republish (PR-3 Step 3)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from tests.routers.test_landing_page_slug import landing_page_fixture  # noqa: F401

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _engine_session():
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    return engine, sm


def _publish(client: TestClient, experiment_id: str) -> dict:
    with patch(
        "app.routers.experiments.notify_live_landing_page_changed",
        new_callable=AsyncMock,
    ):
        resp = client.post(
            f"/experiments/{experiment_id}/landing-page/publish",
            json={},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _republish(client: TestClient, experiment_id: str):
    return client.post(
        f"/experiments/{experiment_id}/landing-page/republish",
        headers=_AUTH_HEADER,
    )


def _fetch_cohorts(experiment_id: str) -> list[LandingPagePublish]:
    engine, sm = _engine_session()

    async def _run() -> list[LandingPagePublish]:
        async with sm() as session:
            lp = (
                await session.execute(
                    select(LandingPage).where(
                        LandingPage.experiment_id == UUID(experiment_id),
                    ),
                )
            ).scalar_one()
            rows = (
                await session.execute(
                    select(LandingPagePublish)
                    .where(LandingPagePublish.landing_page_id == lp.id)
                    .order_by(LandingPagePublish.publish_number),
                )
            ).scalars().all()
            return list(rows)

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_republish_closes_old_cohort_and_opens_new(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, slug = landing_page_fixture
    first = _publish(client, experiment_id)
    assert first["publish_number"] == 1

    before = datetime.now(timezone.utc)
    resp = _republish(client, experiment_id)
    after = datetime.now(timezone.utc)
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == slug
    assert body["publish_number"] == 2
    assert "public_url" in body

    cohorts = _fetch_cohorts(experiment_id)
    assert len(cohorts) == 2
    assert cohorts[0].publish_number == 1
    assert cohorts[0].ended_at is not None
    assert before <= cohorts[0].ended_at <= after
    assert cohorts[1].publish_number == 2
    assert cohorts[1].ended_at is None
    assert before <= cohorts[1].published_at <= after

    # status and live_at unchanged
    engine, sm = _engine_session()

    async def _assert_unchanged() -> None:
        async with sm() as session:
            experiment = (
                await session.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id)),
                )
            ).scalar_one()
            landing = (
                await session.execute(
                    select(LandingPage).where(
                        LandingPage.experiment_id == UUID(experiment_id),
                    ),
                )
            ).scalar_one()
            assert experiment.status == ExperimentStatus.LANDING_LIVE
            assert landing.live_at is not None

    try:
        asyncio.get_event_loop().run_until_complete(_assert_unchanged())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_republish_rejected_when_not_landing_live(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, _slug = landing_page_fixture
    resp = _republish(client, experiment_id)
    assert resp.status_code == 409
    assert "LANDING_LIVE" in resp.json()["detail"]


def test_republish_increments_publish_number_across_multiple(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, _slug = landing_page_fixture
    _publish(client, experiment_id)

    for expected in (2, 3, 4):
        resp = _republish(client, experiment_id)
        assert resp.status_code == 200
        assert resp.json()["publish_number"] == expected

    cohorts = _fetch_cohorts(experiment_id)
    assert [c.publish_number for c in cohorts] == [1, 2, 3, 4]
    assert all(c.ended_at is not None for c in cohorts[:-1])
    assert cohorts[-1].ended_at is None


def test_republish_rejected_when_live_at_null(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, _slug = landing_page_fixture
    _publish(client, experiment_id)

    engine, sm = _engine_session()

    async def _clear_live_at() -> None:
        async with sm() as session:
            await session.execute(
                update(LandingPage)
                .where(LandingPage.experiment_id == UUID(experiment_id))
                .values(live_at=None),
            )
            await session.commit()

    try:
        asyncio.get_event_loop().run_until_complete(_clear_live_at())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())

    resp = _republish(client, experiment_id)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower() or "not live" in resp.json()["detail"].lower()
