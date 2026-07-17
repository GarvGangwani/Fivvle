"""Tests for the LaunchKit router.

- POST /experiments/{id}/generate-launch-kit — gate + dispatch + 502/404.
- GET  /experiments/{id}/launch-kit          — 200 / 404.
- PATCH /experiments/{id}/launch-kit         — 200 / 409 (CAS) / 404 / 400.

Mirrors tests/routers/test_generate_insight_endpoint.py: real Docker Postgres via
TestClient, a FakeLaunchKitDispatcher injected through dependency_overrides, and
standalone-engine seed helpers.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.launch_kit import LaunchKit as LaunchKitRow
from app.dispatchers.dependencies import get_launch_kit_dispatcher_dep
from app.dispatchers.protocol import DispatchError
from app.main import app
from app.schemas.launch_kit import (
    LaunchChannel,
    LaunchKit,
    ShareCopyVariant,
    ShareSurface,
)
from app.services.launch_kit_service import default_readiness_checklist

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_VALID_RAW_IDEA = "A slack bot that answers HR policy questions so ops managers don't have to."

_FAKE_OTHER_UID = "test-firebase-uid-other-launchkit-321"
_FAKE_OTHER_TOKEN = {
    "uid": _FAKE_OTHER_UID,
    "email": "other-launchkit@example.com",
    "email_verified": True,
}


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


def _refined_idea_dict() -> dict[str, Any]:
    return {
        "refined_one_liner": "A Slack bot that answers HR policy questions instantly.",
        "target_audience": "B2B ops managers at 50-500 person SaaS companies.",
        "value_proposition": "Cuts repetitive policy questions so ops managers focus on real work.",
        "risks": [
            "Do existing enterprise tools already solve this for most buyers?",
            "Is the policy content fresh enough to trust without review?",
            "Can unit economics work at the target price point?",
        ],
        "headline": "Stop answering the same policy questions every week.",
        "subheadline": "An AI trained on your handbook handles every policy question.",
        "cta_text": "Join the waitlist",
    }


def _fake_refined_idea() -> object:
    from app.schemas.refinement import RefinedIdea  # noqa: PLC0415

    return RefinedIdea(**_refined_idea_dict())


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
            json={"name": "PolicyPal", "raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


def _set_status(experiment_id: str, status: ExperimentStatus) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    async def _do() -> None:
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

    _run(_do())


def _seed_landing_page(experiment_id: str) -> str:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    landing_page_id: dict[str, str] = {}

    async def _do() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                lp = LandingPage(
                    experiment_id=UUID(experiment_id),
                    template_id="minimal",
                    palette_id="default",
                    font_pair_id="sans",
                    density=LandingDensity.ROOMY,
                    headline="Launch kit route test headline",
                    problem_desc="Problem description for launch kit route tests.",
                    solution_desc="Solution description for launch kit route tests.",
                    cta_text="Join the waitlist",
                    cta_type=LandingCtaType.WAITLIST,
                    slug=f"lk-ep-{uuid4().hex[:12]}",
                )
                session.add(lp)
                await session.flush()
                landing_page_id["id"] = str(lp.id)
                await session.commit()
        finally:
            await engine.dispose()

    _run(_do())
    return landing_page_id["id"]


def _launch_kit(landing_page_id: str) -> LaunchKit:
    return LaunchKit(
        schema_version=1,
        landing_page_id=UUID(landing_page_id),
        first_channel=LaunchChannel.LINKEDIN,
        first_channel_rationale="Because that is where the audience gathers.",
        first_cohort_hint="Start with 10 ops managers you already know.",
        share_copy_variants=[
            ShareCopyVariant(surface=ShareSurface.TWEET, text="Tweet copy."),
            ShareCopyVariant(surface=ShareSurface.DM_OPENER, text="DM copy."),
            ShareCopyVariant(surface=ShareSurface.LINKEDIN_POST, text="LinkedIn copy."),
        ],
        readiness_checklist=default_readiness_checklist(),
        generated_at=datetime.now(UTC),
        founder_edited=False,
        raw_report={"first_channel_rationale": "x", "share_copy_variants": []},
    )


def _seed_launch_kit(experiment_id: str, landing_page_id: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    async def _do() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                session.add(
                    LaunchKitRow(
                        experiment_id=UUID(experiment_id),
                        landing_page_id=UUID(landing_page_id),
                        raw_report=_launch_kit(landing_page_id).model_dump(mode="json"),
                        version=1,
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()

    _run(_do())


def _delete_user_by_uid(firebase_uid: str) -> None:
    from sqlalchemy import delete  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.user import User  # noqa: PLC0415

    async def _do() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                await session.execute(delete(User).where(User.firebase_uid == firebase_uid))
                await session.commit()
        finally:
            await engine.dispose()

    _run(_do())


class FakeLaunchKitDispatcher:
    def __init__(self, *, raise_on_dispatch: Exception | None = None) -> None:
        self.dispatched: list[str] = []
        self.raise_on_dispatch = raise_on_dispatch

    async def dispatch(self, experiment_id: object) -> None:
        if self.raise_on_dispatch is not None:
            raise self.raise_on_dispatch
        self.dispatched.append(str(experiment_id))


@pytest.fixture
def fake_dispatcher() -> Generator[FakeLaunchKitDispatcher, None, None]:
    fd = FakeLaunchKitDispatcher()
    app.dependency_overrides[get_launch_kit_dispatcher_dep] = lambda: fd
    yield fd
    app.dependency_overrides.pop(get_launch_kit_dispatcher_dep, None)


# ---------------------------------------------------------------------------
# POST /generate-launch-kit
# ---------------------------------------------------------------------------


def test_generate_happy_path_from_landing_draft(
    client: TestClient, mock_firebase: None, fake_dispatcher: FakeLaunchKitDispatcher
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_landing_page(experiment_id)
    _set_status(experiment_id, ExperimentStatus.LANDING_DRAFT)

    resp = client.post(
        f"/experiments/{experiment_id}/generate-launch-kit", headers=_AUTH_HEADER
    )

    assert resp.status_code == 202, resp.json()
    body = resp.json()
    assert body["experiment_id"] == experiment_id
    assert body["generation_started"] is True
    assert fake_dispatcher.dispatched == [experiment_id]


def test_generate_rejects_research_ready_409(
    client: TestClient, mock_firebase: None, fake_dispatcher: FakeLaunchKitDispatcher
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _set_status(experiment_id, ExperimentStatus.RESEARCH_READY)

    resp = client.post(
        f"/experiments/{experiment_id}/generate-launch-kit", headers=_AUTH_HEADER
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == (
        "Landing page must be ready before generating a launch kit."
    )
    assert fake_dispatcher.dispatched == []


def test_generate_rejects_landing_generating_409(
    client: TestClient, mock_firebase: None, fake_dispatcher: FakeLaunchKitDispatcher
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _set_status(experiment_id, ExperimentStatus.LANDING_GENERATING)

    resp = client.post(
        f"/experiments/{experiment_id}/generate-launch-kit", headers=_AUTH_HEADER
    )

    assert resp.status_code == 409
    assert fake_dispatcher.dispatched == []


def test_generate_missing_landing_page_409(
    client: TestClient, mock_firebase: None, fake_dispatcher: FakeLaunchKitDispatcher
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    # Allowed status but no landing page row.
    _set_status(experiment_id, ExperimentStatus.COMPLETED)

    resp = client.post(
        f"/experiments/{experiment_id}/generate-launch-kit", headers=_AUTH_HEADER
    )

    assert resp.status_code == 409
    assert fake_dispatcher.dispatched == []


def test_generate_dispatch_error_returns_502(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_landing_page(experiment_id)
    _set_status(experiment_id, ExperimentStatus.LANDING_LIVE)

    fd = FakeLaunchKitDispatcher(raise_on_dispatch=DispatchError("boom"))
    app.dependency_overrides[get_launch_kit_dispatcher_dep] = lambda: fd
    try:
        resp = client.post(
            f"/experiments/{experiment_id}/generate-launch-kit", headers=_AUTH_HEADER
        )
    finally:
        app.dependency_overrides.pop(get_launch_kit_dispatcher_dep, None)

    assert resp.status_code == 502


def test_generate_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(f"/experiments/{uuid4()}/generate-launch-kit")
    assert resp.status_code == 401


def test_generate_wrong_owner_returns_404(
    client: TestClient, mock_firebase: None, fake_dispatcher: FakeLaunchKitDispatcher
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_landing_page(experiment_id)
    _set_status(experiment_id, ExperimentStatus.LANDING_DRAFT)

    try:
        with (
            patch("app.auth.firebase.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.auth.dependencies.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.routers.users.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
        ):
            client.post("/users/sync", json={"name": "Other User"}, headers=_AUTH_HEADER)
            resp = client.post(
                f"/experiments/{experiment_id}/generate-launch-kit", headers=_AUTH_HEADER
            )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Experiment not found"
        assert fake_dispatcher.dispatched == []
    finally:
        _delete_user_by_uid(_FAKE_OTHER_UID)


# ---------------------------------------------------------------------------
# GET /launch-kit
# ---------------------------------------------------------------------------


def test_get_launch_kit_404_when_absent(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)

    resp = client.get(f"/experiments/{experiment_id}/launch-kit", headers=_AUTH_HEADER)
    assert resp.status_code == 404


def test_get_launch_kit_200(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    landing_page_id = _seed_landing_page(experiment_id)
    _seed_launch_kit(experiment_id, landing_page_id)

    resp = client.get(f"/experiments/{experiment_id}/launch-kit", headers=_AUTH_HEADER)
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["version"] == 1
    assert body["launch_kit"]["first_channel"] == "linkedin"
    assert len(body["launch_kit"]["share_copy_variants"]) == 3


# ---------------------------------------------------------------------------
# PATCH /launch-kit
# ---------------------------------------------------------------------------


def test_patch_launch_kit_200(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    landing_page_id = _seed_landing_page(experiment_id)
    _seed_launch_kit(experiment_id, landing_page_id)

    resp = client.patch(
        f"/experiments/{experiment_id}/launch-kit",
        headers=_AUTH_HEADER,
        json={"version": 1, "patch": {"first_channel_rationale": "Edited rationale."}},
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["version"] == 2
    assert body["launch_kit"]["first_channel_rationale"] == "Edited rationale."
    assert body["launch_kit"]["founder_edited"] is True


def test_patch_version_conflict_409(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    landing_page_id = _seed_landing_page(experiment_id)
    _seed_launch_kit(experiment_id, landing_page_id)

    resp = client.patch(
        f"/experiments/{experiment_id}/launch-kit",
        headers=_AUTH_HEADER,
        json={"version": 99, "patch": {"first_cohort_hint": "stale write"}},
    )
    assert resp.status_code == 409


def test_patch_not_found_404(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)

    resp = client.patch(
        f"/experiments/{experiment_id}/launch-kit",
        headers=_AUTH_HEADER,
        json={"version": 1, "patch": {"first_cohort_hint": "no kit yet"}},
    )
    assert resp.status_code == 404


def test_patch_bad_variant_index_400(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    landing_page_id = _seed_landing_page(experiment_id)
    _seed_launch_kit(experiment_id, landing_page_id)

    resp = client.patch(
        f"/experiments/{experiment_id}/launch-kit",
        headers=_AUTH_HEADER,
        json={
            "version": 1,
            "patch": {"share_copy_variants": [{"index": 9, "text": "nope"}]},
        },
    )
    assert resp.status_code == 400
