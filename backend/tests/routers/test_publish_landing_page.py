"""Tests for POST /experiments/{id}/landing-page/publish (PR-3 Step 2)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from tests.routers.test_landing_page_slug import landing_page_fixture  # noqa: F401

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _fetch_cohorts(landing_page_id: UUID) -> list[LandingPagePublish]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _run() -> list[LandingPagePublish]:
        async with sm() as session:
            rows = (
                await session.execute(
                    select(LandingPagePublish)
                    .where(LandingPagePublish.landing_page_id == landing_page_id)
                    .order_by(LandingPagePublish.publish_number),
                )
            ).scalars().all()
            return list(rows)

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def _landing_page_id(experiment_id: str) -> UUID:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _run() -> UUID:
        async with sm() as session:
            lp = (
                await session.execute(
                    select(LandingPage).where(
                        LandingPage.experiment_id == UUID(experiment_id),
                    ),
                )
            ).scalar_one()
            return lp.id

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_first_publish_creates_cohort_one(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, slug = landing_page_fixture
    with patch(
        "app.routers.experiments.notify_live_landing_page_changed",
        new_callable=AsyncMock,
    ):
        resp = client.post(
            f"/experiments/{experiment_id}/landing-page/publish",
            json={},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == slug
    assert body["publish_number"] == 1
    assert "public_url" in body

    lp_id = _landing_page_id(experiment_id)
    cohorts = _fetch_cohorts(lp_id)
    assert len(cohorts) == 1
    assert cohorts[0].publish_number == 1
    assert cohorts[0].ended_at is None

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _assert_live() -> None:
        async with sm() as session:
            experiment = (
                await session.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id)),
                )
            ).scalar_one()
            landing = (
                await session.execute(
                    select(LandingPage).where(LandingPage.experiment_id == UUID(experiment_id)),
                )
            ).scalar_one()
            assert experiment.status == ExperimentStatus.LANDING_LIVE
            assert landing.live_at is not None

    try:
        asyncio.get_event_loop().run_until_complete(_assert_live())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_publish_rejected_if_cohort_already_exists(
    client: TestClient,
    mock_firebase: None,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, _slug = landing_page_fixture
    with patch(
        "app.routers.experiments.notify_live_landing_page_changed",
        new_callable=AsyncMock,
    ):
        first = client.post(
            f"/experiments/{experiment_id}/landing-page/publish",
            json={},
            headers=_AUTH_HEADER,
        )
    assert first.status_code == 200

    # Simulate draft reopen while cohort #1 remains (republish is the right path).
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _reset_to_draft() -> None:
        async with sm() as session:
            experiment = (
                await session.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id)),
                )
            ).scalar_one()
            experiment.status = ExperimentStatus.LANDING_DRAFT
            await session.commit()

    try:
        asyncio.get_event_loop().run_until_complete(_reset_to_draft())
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())

    with patch(
        "app.routers.experiments.notify_live_landing_page_changed",
        new_callable=AsyncMock,
    ):
        second = client.post(
            f"/experiments/{experiment_id}/landing-page/publish",
            json={},
            headers=_AUTH_HEADER,
        )
    assert second.status_code == 409
    assert "republish" in second.json()["detail"].lower()

    lp_id = _landing_page_id(experiment_id)
    cohorts = _fetch_cohorts(lp_id)
    assert len(cohorts) == 1
    assert cohorts[0].publish_number == 1
