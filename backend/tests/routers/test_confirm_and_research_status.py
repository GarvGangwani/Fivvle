"""Tests for POST /experiments/{id}/confirm and GET /experiments/{id}/research-status.

Split into two sections:

1. Pure-logic unit tests (no DB) — phase mapping, sanitization.
2. DB-fixture regression tests (real Postgres via TestClient + conftest) — these are
   regression tests for the two bugs fixed in B2.4:
     Bug A: /confirm rejected RESEARCH_FAILED experiments with 409 (re-dispatch blocked).
     Bug B: research_error_detail was not cleared on re-dispatch, so the stale error
            appeared in /research-status during the new run.

DB fixture strategy:
   - Create experiment via POST /experiments (LLM mocked → REFINED status).
   - Force the status (and optionally research_error_detail) directly via an async
     DB write so we can test from any status without running the pipeline.
   - Use FakeDispatcher (dependency override) so /confirm returns 202 immediately
     without scheduling a real asyncio task.
   - Verify DB state after the call using a second direct DB read.

Cleanup: the autouse _cleanup_test_users fixture in conftest.py deletes the test
user after each test (CASCADE removes experiments).
"""

from __future__ import annotations

import asyncio
from typing import Generator
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.enums import ExperimentStatus
from app.dispatchers.dependencies import get_dispatcher_dep
from app.main import app
from tests.conftest import FAKE_FIREBASE_UID

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_VALID_RAW_IDEA = "A slack bot that answers HR policy questions so ops managers don't have to."


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
        "subheadline": "An AI trained on your handbook handles every 'what's the policy on X?' question.",
        "cta_text": "Join the waitlist",
    }


def _fake_refined_idea() -> object:
    from app.schemas.refinement import RefinedIdea  # noqa: PLC0415
    return RefinedIdea(**_make_valid_refined_idea_dict())


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _create_refined_experiment(client: TestClient) -> str:
    """Create an experiment via the API (LLM mocked) and return its UUID string."""
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
    assert resp.json()["status"] == "REFINED"
    return resp.json()["id"]


def _force_experiment_status(
    experiment_id: str,
    new_status: ExperimentStatus,
    *,
    research_error_detail: str | None = None,
) -> None:
    """Directly update an experiment row in Postgres to any status.

    Uses a standalone async engine (same pattern as conftest._cleanup_test_users)
    so it works after the TestClient lifespan has already spun up the app engine.
    """
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        updates: dict = {"status": new_status}
        if research_error_detail is not None:
            updates["research_error_detail"] = research_error_detail
        try:
            async with sm() as session:
                await session.execute(
                    update(Experiment)
                    .where(Experiment.id == UUID(experiment_id))
                    .values(**updates)
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _read_experiment_fields(experiment_id: str) -> dict:
    """Return {status, research_error_detail} for an experiment row."""
    from sqlalchemy import select  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    result: dict = {}

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
                result["research_error_detail"] = row.research_error_detail
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())
    return result


# ---------------------------------------------------------------------------
# Fake dispatcher implementations for testing
# ---------------------------------------------------------------------------


class FakeDispatcher:
    """Records dispatch calls without running the pipeline."""

    def __init__(self) -> None:
        self.dispatched: list[str] = []

    async def dispatch(self, experiment_id: object) -> None:
        self.dispatched.append(str(experiment_id))


# ---------------------------------------------------------------------------
# research_phase_mapping unit tests (pure logic, no DB needed)
# ---------------------------------------------------------------------------

from app.services.research_phase_mapping import get_phase_label, get_phases_completed  # noqa: E402


class TestGetPhaseLabel:
    def test_researching_returns_label(self) -> None:
        assert get_phase_label(ExperimentStatus.RESEARCHING) == "Starting research..."

    def test_planning_returns_label(self) -> None:
        assert get_phase_label(ExperimentStatus.RESEARCH_PLANNING) is not None

    def test_ready_returns_none(self) -> None:
        assert get_phase_label(ExperimentStatus.RESEARCH_READY) is None

    def test_failed_returns_none(self) -> None:
        assert get_phase_label(ExperimentStatus.RESEARCH_FAILED) is None

    def test_reading_returns_label_unreachable_in_b2(self) -> None:
        # RESEARCH_READING is in the map (B3 placeholder) — must not KeyError.
        label = get_phase_label(ExperimentStatus.RESEARCH_READING)
        assert label is not None

    def test_non_research_status_returns_none(self) -> None:
        assert get_phase_label(ExperimentStatus.DRAFT) is None


class TestGetPhasesCompleted:
    def test_researching_returns_empty(self) -> None:
        # RESEARCHING is the first step — nothing completed yet.
        assert get_phases_completed(ExperimentStatus.RESEARCHING) == []

    def test_planning_returns_researching(self) -> None:
        assert get_phases_completed(ExperimentStatus.RESEARCH_PLANNING) == [
            ExperimentStatus.RESEARCHING,
        ]

    def test_searching_returns_two_phases(self) -> None:
        completed = get_phases_completed(ExperimentStatus.RESEARCH_SEARCHING)
        assert ExperimentStatus.RESEARCHING in completed
        assert ExperimentStatus.RESEARCH_PLANNING in completed
        assert len(completed) == 2

    def test_reading_returns_three_prior_phases(self) -> None:
        completed = get_phases_completed(ExperimentStatus.RESEARCH_READING)
        assert ExperimentStatus.RESEARCHING in completed
        assert ExperimentStatus.RESEARCH_PLANNING in completed
        assert ExperimentStatus.RESEARCH_SEARCHING in completed
        assert len(completed) == 3

    def test_synthesizing_returns_four_prior_phases(self) -> None:
        completed = get_phases_completed(ExperimentStatus.RESEARCH_SYNTHESIZING)
        assert len(completed) == 4

    def test_ready_returns_five_prior_phases(self) -> None:
        completed = get_phases_completed(ExperimentStatus.RESEARCH_READY)
        assert len(completed) == 5

    def test_failed_returns_empty(self) -> None:
        # Can't determine where failure occurred from status alone.
        assert get_phases_completed(ExperimentStatus.RESEARCH_FAILED) == []

    def test_non_research_status_returns_empty(self) -> None:
        assert get_phases_completed(ExperimentStatus.DRAFT) == []
        assert get_phases_completed(ExperimentStatus.REFINED) == []


# ---------------------------------------------------------------------------
# sanitize_error_detail unit tests
# ---------------------------------------------------------------------------

from app.services.research_engine_service import _sanitize_error_detail  # noqa: E402


class TestSanitizeErrorDetail:
    def test_format_prefix(self) -> None:
        exc = ValueError("something broke")
        detail = _sanitize_error_detail("planner", exc)
        assert detail.startswith("planner:ValueError:")

    def test_redacts_long_token(self) -> None:
        # 40-char string that looks like an API key should be redacted.
        fake_key = "sk-ant-" + "a" * 40
        exc = RuntimeError(f"bad key {fake_key}")
        detail = _sanitize_error_detail("synthesizer", exc)
        assert fake_key not in detail
        assert "[REDACTED]" in detail

    def test_truncates_to_max_length(self) -> None:
        exc = ValueError("x" * 1000)
        detail = _sanitize_error_detail("searcher", exc)
        assert len(detail) <= 500

    def test_phase_included(self) -> None:
        exc = RuntimeError("oops")
        for phase in ("planner", "searcher", "synthesizer", "pipeline"):
            assert _sanitize_error_detail(phase, exc).startswith(f"{phase}:")


# ---------------------------------------------------------------------------
# Auth-guard smoke tests (no DB needed — auth fires before ownership check)
# ---------------------------------------------------------------------------


def test_confirm_unauthenticated_returns_401(client: TestClient) -> None:
    """No Authorization header → 401 before any DB lookup."""
    resp = client.post(f"/experiments/{uuid4()}/confirm")
    assert resp.status_code == 401


def test_research_status_unauthenticated_returns_401(client: TestClient) -> None:
    """No Authorization header → 401 before any DB lookup."""
    resp = client.get(f"/experiments/{uuid4()}/research-status")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Fixtures for DB-backed tests
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_dispatcher() -> Generator[FakeDispatcher, None, None]:
    """Install FakeDispatcher as the app dependency and clean up after the test."""
    fd = FakeDispatcher()
    app.dependency_overrides[get_dispatcher_dep] = lambda: fd
    yield fd
    app.dependency_overrides.pop(get_dispatcher_dep, None)


# ---------------------------------------------------------------------------
# Regression test: Bug A — confirm on RESEARCH_FAILED must return 202
# ---------------------------------------------------------------------------


def test_confirm_on_research_failed_returns_202_and_transitions_to_researching(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Bug A regression: /confirm on RESEARCH_FAILED must accept and return 202.

    Before the fix, _CONFIRM_ALLOWED_STATUSES = {REFINED} so a RESEARCH_FAILED
    experiment returned 409 and founders could not retry a failed run.

    Asserts:
    - HTTP 202 returned.
    - Response body status field is "RESEARCHING" (SCREAMING_SNAKE_CASE).
    - DB row status is RESEARCHING after the call.
    - FakeDispatcher was called exactly once with the correct experiment_id.
    """
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)

    # Seed the experiment into RESEARCH_FAILED state (simulates a prior failed run).
    _force_experiment_status(experiment_id, ExperimentStatus.RESEARCH_FAILED)

    # Verify the seed worked.
    pre = _read_experiment_fields(experiment_id)
    assert pre["status"] == ExperimentStatus.RESEARCH_FAILED

    # Call /confirm — must return 202, not 409.
    resp = client.post(f"/experiments/{experiment_id}/confirm", headers=_AUTH_HEADER)

    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.json()}"
    body = resp.json()

    # Status field must be SCREAMING_SNAKE_CASE string per serialization convention.
    assert body["status"] == "RESEARCHING"
    assert body["experiment_id"] == experiment_id
    assert "research-status" in body["status_url"]

    # DB must reflect the transition.
    post = _read_experiment_fields(experiment_id)
    assert post["status"] == ExperimentStatus.RESEARCHING

    # Dispatcher must have been called exactly once.
    assert fake_dispatcher.dispatched == [experiment_id]


# ---------------------------------------------------------------------------
# Regression test: Bug B — research_error_detail cleared on re-dispatch
# ---------------------------------------------------------------------------


def test_confirm_on_research_failed_clears_error_detail(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Bug B regression: research_error_detail must be NULL after re-dispatch.

    Before the fix, the transition block only set status = RESEARCHING and did
    not clear research_error_detail. The next /research-status poll would return
    the old error message even though a new run was in progress.

    Asserts:
    - DB research_error_detail is None after /confirm.
    - /research-status endpoint does NOT include error_detail in its response
      (error_detail is only populated when status == RESEARCH_FAILED).
    """
    _sync_user(client)
    experiment_id = _create_refined_experiment(client)

    # Seed RESEARCH_FAILED with a populated error detail.
    _force_experiment_status(
        experiment_id,
        ExperimentStatus.RESEARCH_FAILED,
        research_error_detail="planner:TimeoutError: upstream timed out",
    )

    # Verify the seed: error detail is present before re-dispatch.
    pre = _read_experiment_fields(experiment_id)
    assert pre["research_error_detail"] == "planner:TimeoutError: upstream timed out"

    # Re-dispatch.
    resp = client.post(f"/experiments/{experiment_id}/confirm", headers=_AUTH_HEADER)
    assert resp.status_code == 202, resp.json()

    # DB: research_error_detail must be NULL.
    post = _read_experiment_fields(experiment_id)
    assert post["research_error_detail"] is None, (
        f"Expected research_error_detail=None after re-dispatch, got: {post['research_error_detail']!r}"
    )

    # /research-status must NOT surface the old error (status is RESEARCHING, not FAILED).
    status_resp = client.get(f"/experiments/{experiment_id}/research-status", headers=_AUTH_HEADER)
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == "RESEARCHING"
    assert status_body["error_detail"] is None


# ===========================================================================
# Batch 3 — Router failure-mode matrix
# ===========================================================================

# A second Firebase UID used in wrong-owner tests.
_FAKE_OTHER_UID = "test-firebase-uid-other-b3-456"
_FAKE_OTHER_TOKEN = {
    "uid": _FAKE_OTHER_UID,
    "email": "other-b3@example.com",
    "email_verified": True,
}


def _delete_user_by_uid(firebase_uid: str) -> None:
    """Hard-delete a user row by firebase_uid for wrong-owner test cleanup."""
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


# ---------------------------------------------------------------------------
# /confirm — 404 tests
# ---------------------------------------------------------------------------


def test_confirm_nonexistent_experiment_returns_404(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Random UUID that has no row → 404 'Experiment not found'."""
    _sync_user(client)
    resp = client.post(f"/experiments/{uuid4()}/confirm", headers=_AUTH_HEADER)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Experiment not found"
    assert fake_dispatcher.dispatched == []


def test_confirm_wrong_owner_returns_404_matching_nonexistent_response(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Experiment exists but belongs to a different user → same 404 as non-existent.

    Verifies that ownership failure does NOT reveal experiment existence
    (AGENTS.md 'Authentication and authorization').
    """
    # Create owner's experiment.
    _sync_user(client)
    exp_id = _create_refined_experiment(client)

    # Switch to a different authenticated user.
    try:
        with (
            patch("app.auth.firebase.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.auth.dependencies.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.routers.users.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
        ):
            client.post("/users/sync", json={"name": "Other User B3"}, headers=_AUTH_HEADER)
            resp = client.post(f"/experiments/{exp_id}/confirm", headers=_AUTH_HEADER)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Experiment not found"
        assert fake_dispatcher.dispatched == []
    finally:
        _delete_user_by_uid(_FAKE_OTHER_UID)


# ---------------------------------------------------------------------------
# /confirm — 409 matrix (7 statuses, parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_status",
    [
        ExperimentStatus.DRAFT,
        ExperimentStatus.REFINING,
        ExperimentStatus.RESEARCHING,
        ExperimentStatus.RESEARCH_PLANNING,
        ExperimentStatus.RESEARCH_SEARCHING,
        ExperimentStatus.RESEARCH_SYNTHESIZING,
        ExperimentStatus.RESEARCH_READY,
    ],
    ids=lambda s: s.value,
)
def test_confirm_invalid_status_returns_409_and_dispatcher_not_called(
    bad_status: ExperimentStatus,
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Statuses outside {REFINED, RESEARCH_FAILED} must return 409.

    Verifies both the HTTP status code and that the dispatcher is never
    invoked on an invalid transition (no phantom pipeline tasks).
    """
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, bad_status)

    resp = client.post(f"/experiments/{exp_id}/confirm", headers=_AUTH_HEADER)

    assert resp.status_code == 409, (
        f"Expected 409 for status={bad_status!r}, got {resp.status_code}: {resp.json()}"
    )
    assert fake_dispatcher.dispatched == [], (
        f"Dispatcher must NOT be called on 409 (was called for {bad_status!r})"
    )


# ---------------------------------------------------------------------------
# /confirm — 202 happy path on REFINED (no prior failure state)
# ---------------------------------------------------------------------------


def test_confirm_on_refined_returns_202_with_status_url(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Fresh REFINED experiment → 202 with correct body and status_url."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)

    resp = client.post(f"/experiments/{exp_id}/confirm", headers=_AUTH_HEADER)

    assert resp.status_code == 202, resp.json()
    body = resp.json()
    assert body["status"] == "RESEARCHING"
    assert body["experiment_id"] == exp_id
    assert "research-status" in body["status_url"]
    # Dispatcher called exactly once.
    assert fake_dispatcher.dispatched == [exp_id]


# ---------------------------------------------------------------------------
# /research-status — 404 tests
# ---------------------------------------------------------------------------


def test_research_status_nonexistent_experiment_returns_404(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Random UUID that has no row → 404 'Experiment not found'."""
    _sync_user(client)
    resp = client.get(f"/experiments/{uuid4()}/research-status", headers=_AUTH_HEADER)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Experiment not found"


def test_research_status_wrong_owner_returns_404_matching_nonexistent_response(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Experiment exists but belongs to a different user → same 404 as non-existent."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    try:
        with (
            patch("app.auth.firebase.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.auth.dependencies.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
            patch("app.routers.users.verify_id_token", return_value=_FAKE_OTHER_TOKEN),
        ):
            client.post("/users/sync", json={"name": "Other User B3"}, headers=_AUTH_HEADER)
            resp = client.get(f"/experiments/{exp_id}/research-status", headers=_AUTH_HEADER)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Experiment not found"
    finally:
        _delete_user_by_uid(_FAKE_OTHER_UID)


# ---------------------------------------------------------------------------
# /research-status — lifecycle status matrix (5 statuses, parametrized)
# ---------------------------------------------------------------------------

from app.services.research_phase_mapping import get_phase_label  # noqa: E402


@pytest.mark.parametrize(
    "status,expected_phases_count",
    [
        (ExperimentStatus.RESEARCHING, 0),
        (ExperimentStatus.RESEARCH_PLANNING, 1),
        (ExperimentStatus.RESEARCH_SEARCHING, 2),
        (ExperimentStatus.RESEARCH_READING, 3),
        (ExperimentStatus.RESEARCH_SYNTHESIZING, 4),
        (ExperimentStatus.RESEARCH_READY, 5),
    ],
    ids=lambda x: x.value if isinstance(x, ExperimentStatus) else str(x),
)
def test_research_status_phase_info_matches_status(
    status: ExperimentStatus,
    expected_phases_count: int,
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """Each research lifecycle status returns the correct phase_label and phases_completed.

    phase_label is sourced from research_phase_mapping — we assert it matches
    get_phase_label(status) rather than hardcoding strings, so this test stays
    valid if label copy changes.
    """
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, status)

    resp = client.get(f"/experiments/{exp_id}/research-status", headers=_AUTH_HEADER)

    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["status"] == status.value
    assert body["phase_label"] == get_phase_label(status)
    assert len(body["phases_completed"]) == expected_phases_count, (
        f"phases_completed for {status!r}: expected {expected_phases_count}, got {body['phases_completed']}"
    )
    # error_detail must be absent for non-FAILED statuses.
    assert body["error_detail"] is None


# ---------------------------------------------------------------------------
# /research-status — RESEARCH_FAILED includes error_detail, no phase_label
# ---------------------------------------------------------------------------


def test_research_status_failed_includes_error_detail_and_no_phase_label(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """RESEARCH_FAILED status → error_detail populated, phase_label=None."""
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(
        exp_id,
        ExperimentStatus.RESEARCH_FAILED,
        research_error_detail="planner:TimeoutError: upstream timed out after 360s",
    )

    resp = client.get(f"/experiments/{exp_id}/research-status", headers=_AUTH_HEADER)

    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["status"] == "RESEARCH_FAILED"
    assert body["phase_label"] is None
    assert body["error_detail"] == "planner:TimeoutError: upstream timed out after 360s"
    assert body["phases_completed"] == []


# ---------------------------------------------------------------------------
# /research-status — rate limit: 31st request returns 429
# ---------------------------------------------------------------------------


def test_research_status_rate_limit_returns_429_after_30_requests(
    client: TestClient,
    mock_firebase: None,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """GET /research-status is limited to 30/min/user; the 31st request returns 429.

    Each test creates a fresh user (new UUID) so the rate-limit counter starts
    at 0 — no bleed from other tests that share the same in-process limiter.
    """
    _sync_user(client)
    exp_id = _create_refined_experiment(client)
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCHING)

    url = f"/experiments/{exp_id}/research-status"

    # First 30 requests must all succeed.
    for i in range(30):
        resp = client.get(url, headers=_AUTH_HEADER)
        assert resp.status_code == 200, f"Request {i + 1}/30 unexpectedly returned {resp.status_code}"

    # 31st request must be rate-limited.
    resp_31 = client.get(url, headers=_AUTH_HEADER)
    assert resp_31.status_code == 429, (
        f"Expected 429 on 31st request, got {resp_31.status_code}: {resp_31.json()}"
    )
    body = resp_31.json()
    assert "retry_after_seconds" in body
    assert "error" in body
