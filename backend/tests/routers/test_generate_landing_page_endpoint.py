"""Tests for POST /experiments/{id}/generate-landing-page."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.dispatchers.dependencies import get_landing_page_dispatcher_dep
from app.main import app

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_VALID_RAW_IDEA = "A slack bot that answers HR policy questions so ops managers don't have to."


def _make_valid_refined_idea_dict() -> dict:
    return {
        "refined_one_liner": "A Slack bot that answers HR policy questions instantly.",
        "target_audience": "Ops managers at mid-size companies.",
        "value_proposition": "Fewer policy interrupts in Slack.",
        "risks": ["Market size", "Competition", "Pricing"],
        "headline": "Stop answering the same policy questions every week.",
        "subheadline": "AI trained on your handbook.",
        "cta_text": "Join the waitlist",
    }


def _fake_refined_idea() -> object:
    from app.schemas.refinement import RefinedIdea  # noqa: PLC0415

    return RefinedIdea(**_make_valid_refined_idea_dict())


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _create_refined_experiment(client: TestClient) -> str:
    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=_fake_refined_idea()),
    ):
        resp = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def _set_experiment_status(experiment_id: str, status: ExperimentStatus) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                await session.execute(
                    update(Experiment)
                    .where(Experiment.id == UUID(experiment_id))
                    .values(status=status)
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


class _FakeLandingPageDispatcher:
    def __init__(self) -> None:
        self.dispatched: list[tuple[UUID, str, str, str | None, bool]] = []

    async def dispatch(
        self,
        experiment_id: UUID,
        page_goal: str,
        template_id: str,
        regeneration_hint: str | None = None,
        was_live: bool = False,
    ) -> None:
        self.dispatched.append(
            (experiment_id, page_goal, template_id, regeneration_hint, was_live)
        )


@pytest.fixture
def fake_landing_page_dispatcher() -> _FakeLandingPageDispatcher:
    dispatcher = _FakeLandingPageDispatcher()
    app.dependency_overrides[get_landing_page_dispatcher_dep] = lambda: dispatcher
    yield dispatcher
    app.dependency_overrides.pop(get_landing_page_dispatcher_dep, None)


def _post_generate(
    client: TestClient,
    experiment_id: str,
    *,
    template_id: str = "editorial-saas",
) -> object:
    return client.post(
        f"/experiments/{experiment_id}/generate-landing-page",
        json={"template_id": template_id},
        headers=_AUTH_HEADER,
    )


def test_generate_landing_page_happy_path_from_research_ready(
    client: TestClient,
    mock_firebase: None,
    fake_landing_page_dispatcher: _FakeLandingPageDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _set_experiment_status(experiment_id, ExperimentStatus.RESEARCH_READY)

    resp = _post_generate(client, experiment_id)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "LANDING_GENERATING"
    assert len(fake_landing_page_dispatcher.dispatched) == 1


def test_generate_landing_page_idempotent_when_already_generating(
    client: TestClient,
    mock_firebase: None,
    fake_landing_page_dispatcher: _FakeLandingPageDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _set_experiment_status(experiment_id, ExperimentStatus.LANDING_GENERATING)
    monkeypatch.setattr(
        "app.routers.experiments.landing_generation_in_progress",
        lambda _experiment_id: True,
    )

    resp = _post_generate(client, experiment_id)
    assert resp.status_code == 202
    assert resp.json()["status"] == "LANDING_GENERATING"
    assert len(fake_landing_page_dispatcher.dispatched) == 0


def test_generate_landing_page_redispatches_when_stuck_generating(
    client: TestClient,
    mock_firebase: None,
    fake_landing_page_dispatcher: _FakeLandingPageDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _set_experiment_status(experiment_id, ExperimentStatus.LANDING_GENERATING)
    monkeypatch.setattr(
        "app.routers.experiments.landing_generation_in_progress",
        lambda _experiment_id: False,
    )

    resp = _post_generate(client, experiment_id)
    assert resp.status_code == 202
    assert resp.json()["status"] == "LANDING_GENERATING"
    assert len(fake_landing_page_dispatcher.dispatched) == 1


def test_generate_landing_page_wrong_status_returns_409(
    client: TestClient,
    mock_firebase: None,
    fake_landing_page_dispatcher: _FakeLandingPageDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _set_experiment_status(experiment_id, ExperimentStatus.INSIGHT_READY)

    resp = _post_generate(client, experiment_id)
    assert resp.status_code == 409
    assert "RESEARCH_READY" in resp.json()["detail"]
