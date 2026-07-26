"""Tests for POST /experiments/{id}/generate-insight."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus, InsightRecommendation, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_publish import LandingPagePublish
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.dispatchers.dependencies import get_insight_dispatcher_dep
from app.dispatchers.protocol import DispatchError
from app.main import app

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_VALID_RAW_IDEA = "A slack bot that answers HR policy questions so ops managers don't have to."

_FAKE_OTHER_UID = "test-firebase-uid-other-insight-789"
_FAKE_OTHER_TOKEN = {
    "uid": _FAKE_OTHER_UID,
    "email": "other-insight@example.com",
    "email_verified": True,
}


def _make_valid_refined_idea_dict() -> dict:
    return {
        "refined_one_liner": "A Slack bot that answers HR policy questions instantly.",
        "target_audience": (
            "Operations managers at 50-500 person companies who answer "
            "20-30 repeated policy questions per week in Slack."
        ),
        "value_proposition": (
            "Eliminates 30-minute weekly Slack interrupts so ops managers "
            "can focus on real operations work instead of being a walking FAQ."
        ),
        "risks": [
            "Is the market large enough to support a venture-scale business?",
            "Do existing enterprise tools already solve this for most buyers?",
            "Can unit economics work at target price point given CAC?",
        ],
        "headline": "Stop answering the same policy questions every week.",
        "subheadline": (
            "An AI trained on your handbook handles every 'what's the policy on X?' question."
        ),
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


def _read_experiment_status(experiment_id: str) -> ExperimentStatus:
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    result: dict[str, ExperimentStatus] = {}

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                row = (
                    await session.execute(
                        select(Experiment).where(Experiment.id == UUID(experiment_id))
                    )
                ).scalar_one()
                result["status"] = row.status
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())
    return result["status"]


def _seed_insight_fixture(
    experiment_id: str,
    *,
    status: ExperimentStatus,
    page_view_count: int = 0,
    signup_count: int = 0,
    days_live: int = 0,
    with_insight_report: bool = False,
) -> None:
    """Seed landing page telemetry and optional prior InsightReport row."""
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

                live_at: datetime | None = None
                if days_live > 0:
                    live_at = datetime.now(timezone.utc) - timedelta(days=days_live)
                elif status in {
                    ExperimentStatus.LANDING_LIVE,
                    ExperimentStatus.INSIGHT_READY,
                    ExperimentStatus.INSIGHT_FAILED,
                }:
                    live_at = datetime.now(timezone.utc)

                landing_page = LandingPage(
                    experiment_id=UUID(experiment_id),
                    template_id="minimal",
                    palette_id="default",
                    font_pair_id="sans",
                    density=LandingDensity.ROOMY,
                    headline="Insight endpoint test headline",
                    problem_desc="Problem description for insight endpoint tests.",
                    solution_desc="Solution description for insight endpoint tests.",
                    cta_text="Join the waitlist",
                    cta_type=LandingCtaType.WAITLIST,
                    slug=f"insight-ep-{uuid4().hex[:12]}",
                    live_at=live_at,
                )
                session.add(landing_page)
                await session.flush()

                publish_id = None
                if live_at is not None:
                    cohort = LandingPagePublish(
                        landing_page_id=landing_page.id,
                        publish_number=1,
                        published_at=live_at,
                        ended_at=None,
                    )
                    session.add(cohort)
                    await session.flush()
                    publish_id = cohort.id

                now = datetime.now(timezone.utc)
                for i in range(page_view_count):
                    session.add(
                        PageView(
                            experiment_id=UUID(experiment_id),
                            publish_id=publish_id,
                            source_tag="twitter",
                            ts=now - timedelta(hours=i),
                            ip_address=f"10.0.0.{i % 250}",
                            time_on_page_sec=30,
                        )
                    )
                for i in range(signup_count):
                    session.add(
                        WaitlistSignup(
                            experiment_id=UUID(experiment_id),
                            publish_id=publish_id,
                            email=f"signup-{i}-{uuid4()}@example.com",
                            source_tag="twitter",
                            ts=now - timedelta(hours=i),
                        )
                    )

                if with_insight_report:
                    session.add(
                        InsightReport(
                            experiment_id=UUID(experiment_id),
                            traffic_summary={"schema_version": 1},
                            conversion_by_source={"schema_version": 1},
                            research_takeaways={"items": []},
                            recommendation="Prior insight recommendation text.",
                            recommendation_type=InsightRecommendation.PROCEED,
                            raw_output={"schema_version": 1},
                        )
                    )

                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _delete_user_by_uid(firebase_uid: str) -> None:
    from sqlalchemy import delete  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.user import User  # noqa: PLC0415

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                await session.execute(delete(User).where(User.firebase_uid == firebase_uid))
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _post_generate_insight(client: TestClient, experiment_id: str) -> object:
    return client.post(
        f"/experiments/{experiment_id}/generate-insight",
        headers=_AUTH_HEADER,
    )


class FakeInsightDispatcher:
    """Records dispatch calls; optionally raises or reads DB status at dispatch time."""

    def __init__(
        self,
        *,
        raise_on_dispatch: Exception | None = None,
        capture_status_at_dispatch: bool = False,
    ) -> None:
        self.dispatched: list[str] = []
        self.raise_on_dispatch = raise_on_dispatch
        self.capture_status_at_dispatch = capture_status_at_dispatch
        self.status_at_dispatch: ExperimentStatus | None = None

    async def _read_status_async(self, experiment_id: str) -> ExperimentStatus:
        from sqlalchemy import select  # noqa: PLC0415
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                row = (
                    await session.execute(
                        select(Experiment).where(Experiment.id == UUID(experiment_id))
                    )
                ).scalar_one()
                return row.status
        finally:
            await engine.dispose()

    async def dispatch(self, experiment_id: object) -> None:
        if self.capture_status_at_dispatch:
            self.status_at_dispatch = await self._read_status_async(str(experiment_id))
        if self.raise_on_dispatch is not None:
            raise self.raise_on_dispatch
        self.dispatched.append(str(experiment_id))


@pytest.fixture
def fake_insight_dispatcher() -> Generator[FakeInsightDispatcher, None, None]:
    fd = FakeInsightDispatcher()
    app.dependency_overrides[get_insight_dispatcher_dep] = lambda: fd
    yield fd
    app.dependency_overrides.pop(get_insight_dispatcher_dep, None)


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_generate_insight_happy_path_from_landing_live(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=15,
        days_live=3,
    )

    resp = _post_generate_insight(client, experiment_id)

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "INSIGHT_GENERATING"
    assert body["experiment_id"] == experiment_id
    assert _read_experiment_status(experiment_id) == ExperimentStatus.INSIGHT_GENERATING
    assert fake_insight_dispatcher.dispatched == [experiment_id]


def test_generate_insight_regen_from_insight_ready(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.INSIGHT_READY,
        page_view_count=50,
        days_live=10,
        with_insight_report=True,
    )

    resp = _post_generate_insight(client, experiment_id)

    assert resp.status_code == 202
    assert resp.json()["status"] == "INSIGHT_GENERATING"
    assert _read_experiment_status(experiment_id) == ExperimentStatus.INSIGHT_GENERATING


def test_generate_insight_regen_from_insight_failed(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.INSIGHT_FAILED,
        page_view_count=20,
        signup_count=2,
        days_live=5,
    )

    resp = _post_generate_insight(client, experiment_id)

    assert resp.status_code == 202
    assert resp.json()["status"] == "INSIGHT_GENERATING"


# ---------------------------------------------------------------------------
# Status and min-data guards
# ---------------------------------------------------------------------------


def test_generate_insight_wrong_status_returns_409(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.REFINED,
        page_view_count=15,
        days_live=10,
    )

    resp = _post_generate_insight(client, experiment_id)

    assert resp.status_code == 409
    assert "must be in LANDING_LIVE" in resp.json()["detail"]
    assert fake_insight_dispatcher.dispatched == []


def test_generate_insight_insufficient_data_returns_409(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=5,
        signup_count=0,
        days_live=3,
    )

    resp = _post_generate_insight(client, experiment_id)

    assert resp.status_code == 409
    assert "Insufficient data" in resp.json()["detail"]
    assert fake_insight_dispatcher.dispatched == []


# ---------------------------------------------------------------------------
# Threshold edges
# ---------------------------------------------------------------------------


def test_generate_insight_exactly_10_views_passes(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=10,
        signup_count=0,
        days_live=0,
    )

    resp = _post_generate_insight(client, experiment_id)
    assert resp.status_code == 202


def test_generate_insight_one_signup_passes(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=0,
        signup_count=1,
        days_live=0,
    )

    resp = _post_generate_insight(client, experiment_id)
    assert resp.status_code == 202


def test_generate_insight_seven_days_live_passes(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=0,
        signup_count=0,
        days_live=7,
    )

    resp = _post_generate_insight(client, experiment_id)
    assert resp.status_code == 202


def test_generate_insight_nine_views_six_days_fails(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=9,
        signup_count=0,
        days_live=6,
    )

    resp = _post_generate_insight(client, experiment_id)
    assert resp.status_code == 409
    assert "Insufficient data" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Auth and ownership
# ---------------------------------------------------------------------------


def test_generate_insight_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(f"/experiments/{uuid4()}/generate-insight")
    assert resp.status_code == 401


def test_generate_insight_wrong_owner_returns_404(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)
    _seed_insight_fixture(
        experiment_id,
        status=ExperimentStatus.LANDING_LIVE,
        page_view_count=15,
        days_live=3,
    )

    try:
        with (
            patch("app.auth.firebase.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.auth.dependencies.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.routers.users.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
        ):
            client.post("/users/sync", json={"name": "Other User Insight"}, headers=_AUTH_HEADER)
            resp = _post_generate_insight(client, experiment_id)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Experiment not found"
        assert fake_insight_dispatcher.dispatched == []
    finally:
        _delete_user_by_uid(_FAKE_OTHER_UID)


def test_generate_insight_nonexistent_returns_404(
    client: TestClient,
    mock_firebase: None,
    fake_insight_dispatcher: FakeInsightDispatcher,
) -> None:
    _sync_user(client)
    resp = _post_generate_insight(client, str(uuid4()))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Experiment not found"
    assert fake_insight_dispatcher.dispatched == []


# ---------------------------------------------------------------------------
# Dispatch failure and ordering
# ---------------------------------------------------------------------------


def test_generate_insight_dispatch_error_returns_502_and_rolls_back_status(
    client: TestClient,
    mock_firebase: None,
) -> None:
    fd = FakeInsightDispatcher(raise_on_dispatch=DispatchError("simulated failure"))
    app.dependency_overrides[get_insight_dispatcher_dep] = lambda: fd
    try:
        _sync_user(client)
        experiment_id = _create_refined_experiment(client)
        _seed_insight_fixture(
            experiment_id,
            status=ExperimentStatus.LANDING_LIVE,
            page_view_count=15,
            days_live=3,
        )

        resp = _post_generate_insight(client, experiment_id)

        assert resp.status_code == 502
        assert resp.json()["detail"] == "Failed to start insight generation, please try again"
        assert _read_experiment_status(experiment_id) == ExperimentStatus.INSIGHT_FAILED
    finally:
        app.dependency_overrides.pop(get_insight_dispatcher_dep, None)


def test_generate_insight_status_committed_before_dispatch(
    client: TestClient,
    mock_firebase: None,
) -> None:
    fd = FakeInsightDispatcher(capture_status_at_dispatch=True)
    app.dependency_overrides[get_insight_dispatcher_dep] = lambda: fd
    try:
        _sync_user(client)
        experiment_id = _create_refined_experiment(client)
        _seed_insight_fixture(
            experiment_id,
            status=ExperimentStatus.LANDING_LIVE,
            page_view_count=15,
            days_live=3,
        )

        resp = _post_generate_insight(client, experiment_id)

        assert resp.status_code == 202
        assert fd.status_at_dispatch == ExperimentStatus.INSIGHT_GENERATING
    finally:
        app.dependency_overrides.pop(get_insight_dispatcher_dep, None)
