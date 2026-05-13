"""Tests for admin cost rollup endpoints and get_current_admin_user dependency.

Coverage:
- Unauthenticated requests → 401 on admin endpoints
- Non-admin authenticated requests → 403 on every admin endpoint
- Admin user happy-path: experiment cost, user cost, daily, per-phase
- Seed data inserted directly so cost math can be asserted exactly
"""

from collections.abc import AsyncGenerator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.experiment import Experiment
from app.db.models.external_api_call import ExternalAPICall
from app.db.models.llm_call import LLMCall
from app.db.models.user import User
from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID


# ---------------------------------------------------------------------------
# Standalone DB session fixture (same pattern as test_llm_client.py)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_admin_user(db_session: AsyncSession) -> User:
    """Insert the canonical fake user with is_admin=True.

    Uses the same FAKE_FIREBASE_UID as mock_firebase so the TestClient's
    auth token resolves to this user.
    """
    user = User(
        firebase_uid=FAKE_FIREBASE_UID,
        email=FAKE_EMAIL,
        name="Admin User",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_plain_user(db_session: AsyncSession) -> User:
    """Insert the canonical fake user with is_admin=False (default)."""
    user = User(
        firebase_uid=FAKE_FIREBASE_UID,
        email=FAKE_EMAIL,
        name="Plain User",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _seed_experiment_calls(
    db_session: AsyncSession,
    experiment_id,
    *,
    llm_cost: Decimal = Decimal("0.05"),
    ext_cost: Decimal = Decimal("0.008"),
    phase: str = "planner",
) -> None:
    """Insert one LLMCall and one ExternalAPICall for the given experiment."""
    db_session.add(LLMCall(
        experiment_id=experiment_id,
        provider="anthropic",
        model="claude-sonnet-4-5",
        prompt_name="test",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=llm_cost,
        latency_ms=500,
        phase=phase,
    ))
    db_session.add(ExternalAPICall(
        experiment_id=experiment_id,
        provider="tavily",
        operation="search",
        latency_ms=300,
        cost_usd=ext_cost,
        success=True,
    ))
    await db_session.commit()


# ---------------------------------------------------------------------------
# 1. Unauthenticated → 401
# ---------------------------------------------------------------------------


def test_unauthenticated_experiment_cost_returns_401(client: TestClient) -> None:
    """No Authorization header → 401."""
    exp_id = uuid4()
    response = client.get(f"/admin/cost/experiment/{exp_id}")
    assert response.status_code == 401


def test_unauthenticated_daily_cost_returns_401(client: TestClient) -> None:
    """No Authorization header → 401."""
    response = client.get("/admin/cost/daily")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 2. Non-admin authenticated → 403 on every endpoint
# ---------------------------------------------------------------------------


def test_non_admin_experiment_cost_returns_403(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Authenticated non-admin user → 403 on experiment cost endpoint."""
    # /users/sync creates the user with is_admin=False by default
    client.post("/users/sync", json={}, headers={"Authorization": "Bearer faketoken"})

    exp_id = uuid4()
    response = client.get(
        f"/admin/cost/experiment/{exp_id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_non_admin_user_cost_returns_403(
    client: TestClient, mock_firebase: None
) -> None:
    client.post("/users/sync", json={}, headers={"Authorization": "Bearer faketoken"})
    response = client.get(
        f"/admin/cost/user/{uuid4()}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 403


def test_non_admin_daily_cost_returns_403(
    client: TestClient, mock_firebase: None
) -> None:
    client.post("/users/sync", json={}, headers={"Authorization": "Bearer faketoken"})
    response = client.get(
        "/admin/cost/daily",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 403


def test_non_admin_per_phase_cost_returns_403(
    client: TestClient, mock_firebase: None
) -> None:
    client.post("/users/sync", json={}, headers={"Authorization": "Bearer faketoken"})
    response = client.get(
        "/admin/cost/per-phase",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 3. Admin happy paths — seed data then check the math
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_experiment_cost_sums_correctly(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Admin can retrieve per-experiment cost; sums match seeded rows."""
    user = await _create_admin_user(db_session)

    # Create an experiment owned by this user
    exp = Experiment(
        user_id=user.id,
        raw_idea="test idea",
        slug="test-slug-exp-cost",
    )
    db_session.add(exp)
    await db_session.commit()
    await db_session.refresh(exp)

    await _seed_experiment_calls(
        db_session, exp.id, llm_cost=Decimal("0.05"), ext_cost=Decimal("0.008")
    )

    response = client.get(
        f"/admin/cost/experiment/{exp.id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["experiment_id"] == str(exp.id)
    assert Decimal(body["llm_cost_usd"]) == Decimal("0.05")
    assert Decimal(body["external_api_cost_usd"]) == Decimal("0.008")
    assert Decimal(body["total_cost_usd"]) == Decimal("0.058")
    assert body["llm_call_count"] == 1
    assert body["external_api_call_count"] == 1

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp.id))
    await db_session.execute(
        delete(ExternalAPICall).where(ExternalAPICall.experiment_id == exp.id)
    )
    await db_session.delete(exp)
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_user_cost_aggregates_across_experiments(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Admin can retrieve per-user cost; aggregates across multiple experiments."""
    user = await _create_admin_user(db_session)

    exp1 = Experiment(user_id=user.id, raw_idea="idea 1", slug="test-slug-user-1")
    exp2 = Experiment(user_id=user.id, raw_idea="idea 2", slug="test-slug-user-2")
    db_session.add_all([exp1, exp2])
    await db_session.commit()
    await db_session.refresh(exp1)
    await db_session.refresh(exp2)

    await _seed_experiment_calls(
        db_session, exp1.id, llm_cost=Decimal("0.10"), ext_cost=Decimal("0.008")
    )
    await _seed_experiment_calls(
        db_session, exp2.id, llm_cost=Decimal("0.20"), ext_cost=Decimal("0.016")
    )

    response = client.get(
        f"/admin/cost/user/{user.id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert Decimal(body["llm_cost_usd"]) == Decimal("0.30")
    assert Decimal(body["external_api_cost_usd"]) == Decimal("0.024")
    assert Decimal(body["total_cost_usd"]) == Decimal("0.324")
    assert body["llm_call_count"] == 2
    assert body["external_api_call_count"] == 2

    # Cleanup
    for exp in [exp1, exp2]:
        await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp.id))
        await db_session.execute(
            delete(ExternalAPICall).where(ExternalAPICall.experiment_id == exp.id)
        )
        await db_session.delete(exp)
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_daily_cost_returns_expected_shape(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Admin can call the daily endpoint; response has correct schema."""
    user = await _create_admin_user(db_session)

    exp = Experiment(user_id=user.id, raw_idea="daily idea", slug="test-slug-daily")
    db_session.add(exp)
    await db_session.commit()
    await db_session.refresh(exp)

    await _seed_experiment_calls(db_session, exp.id)

    response = client.get(
        "/admin/cost/daily?days=7",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["days_back"] == 7
    assert isinstance(body["rows"], list)
    # There should be at least 1 row for today's seeded data
    assert len(body["rows"]) >= 1
    row = body["rows"][0]
    assert "day" in row
    assert "llm_cost_usd" in row
    assert "external_api_cost_usd" in row
    assert "total_cost_usd" in row
    assert "llm_call_count" in row
    assert "external_api_call_count" in row

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp.id))
    await db_session.execute(
        delete(ExternalAPICall).where(ExternalAPICall.experiment_id == exp.id)
    )
    await db_session.delete(exp)
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_per_phase_groups_by_phase(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Admin can call per-phase endpoint; phases are grouped and summed correctly."""
    user = await _create_admin_user(db_session)

    exp = Experiment(user_id=user.id, raw_idea="phase idea", slug="test-slug-phase")
    db_session.add(exp)
    await db_session.commit()
    await db_session.refresh(exp)

    # Two planner calls + one reader call
    for _ in range(2):
        db_session.add(LLMCall(
            experiment_id=exp.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="planner",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.05"),
            latency_ms=400,
            phase="planner",
        ))
    db_session.add(LLMCall(
        experiment_id=exp.id,
        provider="groq",
        model="llama-3.3-70b-versatile",
        prompt_name="reader",
        prompt_tokens=200,
        completion_tokens=100,
        cost_usd=Decimal("0.02"),
        latency_ms=300,
        phase="reader",
    ))
    await db_session.commit()

    response = client.get(
        f"/admin/cost/per-phase?days=1&user_id={user.id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["days_back"] == 1
    rows_by_phase = {r["phase"]: r for r in body["rows"]}

    assert "planner" in rows_by_phase
    assert rows_by_phase["planner"]["call_count"] == 2
    assert Decimal(rows_by_phase["planner"]["llm_cost_usd"]) == Decimal("0.10")

    assert "reader" in rows_by_phase
    assert rows_by_phase["reader"]["call_count"] == 1
    assert Decimal(rows_by_phase["reader"]["llm_cost_usd"]) == Decimal("0.02")

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp.id))
    await db_session.delete(exp)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 4. Zero-result experiments return zeros, not 404
# ---------------------------------------------------------------------------


def test_admin_experiment_cost_returns_zeros_for_unknown_id(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Experiment with no calls returns zeros (not 404)."""
    # /users/sync creates the user, then we manually flip is_admin
    client.post("/users/sync", json={}, headers={"Authorization": "Bearer faketoken"})


# ---------------------------------------------------------------------------
# 5. user_id filter on /per-phase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_per_phase_with_user_id_scopes_results(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """When user_id is provided, only that user's phase rows are included."""
    admin = await _create_admin_user(db_session)
    user2 = User(
        firebase_uid="other-firebase-uid-phase-scope",
        email="phase-scope@example.com",
        name="Phase Scope User",
        is_admin=False,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    exp1 = Experiment(user_id=admin.id, raw_idea="phase scope 1", slug="test-slug-phase-scope-1")
    exp2 = Experiment(user_id=user2.id, raw_idea="phase scope 2", slug="test-slug-phase-scope-2")
    db_session.add_all([exp1, exp2])
    await db_session.commit()
    await db_session.refresh(exp1)
    await db_session.refresh(exp2)

    # 2 planner calls for admin's experiment, 3 for user2's
    for _ in range(2):
        db_session.add(LLMCall(
            experiment_id=exp1.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="planner",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.05"),
            latency_ms=400,
            phase="planner",
        ))
    for _ in range(3):
        db_session.add(LLMCall(
            experiment_id=exp2.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="planner",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.05"),
            latency_ms=400,
            phase="planner",
        ))
    await db_session.commit()

    response = client.get(
        f"/admin/cost/per-phase?days=1&user_id={admin.id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    rows_by_phase = {r["phase"]: r for r in body["rows"]}
    assert "planner" in rows_by_phase
    # Only admin's 2 rows — user2's 3 rows are excluded
    assert rows_by_phase["planner"]["call_count"] == 2
    assert Decimal(rows_by_phase["planner"]["llm_cost_usd"]) == Decimal("0.10")

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp1.id))
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp2.id))
    await db_session.delete(exp1)
    await db_session.delete(exp2)
    await db_session.execute(delete(User).where(User.id == user2.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_per_phase_without_user_id_is_global(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Without user_id, the per-phase endpoint aggregates across all users."""
    admin = await _create_admin_user(db_session)
    user2 = User(
        firebase_uid="other-firebase-uid-phase-global",
        email="phase-global@example.com",
        name="Phase Global User",
        is_admin=False,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    exp1 = Experiment(user_id=admin.id, raw_idea="phase global 1", slug="test-slug-phase-global-1")
    exp2 = Experiment(user_id=user2.id, raw_idea="phase global 2", slug="test-slug-phase-global-2")
    db_session.add_all([exp1, exp2])
    await db_session.commit()
    await db_session.refresh(exp1)
    await db_session.refresh(exp2)

    # One call per user under a unique phase name that won't collide with dev data
    unique_phase = "test-global-phase-marker"
    for exp in [exp1, exp2]:
        db_session.add(LLMCall(
            experiment_id=exp.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="global-test",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.01"),
            latency_ms=400,
            phase=unique_phase,
        ))
    await db_session.commit()

    response = client.get(
        "/admin/cost/per-phase?days=1",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    rows_by_phase = {r["phase"]: r for r in body["rows"]}
    # Both users' rows appear under the unique phase in the global result
    assert unique_phase in rows_by_phase
    assert rows_by_phase[unique_phase]["call_count"] == 2

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp1.id))
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp2.id))
    await db_session.delete(exp1)
    await db_session.delete(exp2)
    await db_session.execute(delete(User).where(User.id == user2.id))
    await db_session.commit()


# ---------------------------------------------------------------------------
# 6. user_id filter on /daily
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_daily_with_user_id_scopes_results(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """When user_id is provided, daily endpoint only includes that user's rows."""
    admin = await _create_admin_user(db_session)
    user2 = User(
        firebase_uid="other-firebase-uid-daily-scope",
        email="daily-scope@example.com",
        name="Daily Scope User",
        is_admin=False,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    exp1 = Experiment(user_id=admin.id, raw_idea="daily scope 1", slug="test-slug-daily-scope-1")
    exp2 = Experiment(user_id=user2.id, raw_idea="daily scope 2", slug="test-slug-daily-scope-2")
    db_session.add_all([exp1, exp2])
    await db_session.commit()
    await db_session.refresh(exp1)
    await db_session.refresh(exp2)

    # 1 LLM call for admin, 1 for user2
    for exp in [exp1, exp2]:
        db_session.add(LLMCall(
            experiment_id=exp.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="daily-scope-test",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.07"),
            latency_ms=400,
            phase="daily-scope-test",
        ))
    await db_session.commit()

    # Filter to admin only — should see exactly 1 call
    response = client.get(
        f"/admin/cost/daily?days=1&user_id={admin.id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["days_back"] == 1
    total_llm_calls = sum(r["llm_call_count"] for r in body["rows"])
    assert total_llm_calls == 1

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp1.id))
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp2.id))
    await db_session.delete(exp1)
    await db_session.delete(exp2)
    await db_session.execute(delete(User).where(User.id == user2.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_daily_without_user_id_is_global(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Without user_id, the daily endpoint aggregates across all users."""
    admin = await _create_admin_user(db_session)
    user2 = User(
        firebase_uid="other-firebase-uid-daily-global",
        email="daily-global@example.com",
        name="Daily Global User",
        is_admin=False,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    exp1 = Experiment(user_id=admin.id, raw_idea="daily global 1", slug="test-slug-daily-global-1")
    exp2 = Experiment(user_id=user2.id, raw_idea="daily global 2", slug="test-slug-daily-global-2")
    db_session.add_all([exp1, exp2])
    await db_session.commit()
    await db_session.refresh(exp1)
    await db_session.refresh(exp2)

    # 1 LLM call per user today
    for exp in [exp1, exp2]:
        db_session.add(LLMCall(
            experiment_id=exp.id,
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_name="daily-global-test",
            prompt_tokens=50,
            completion_tokens=25,
            cost_usd=Decimal("0.03"),
            latency_ms=200,
            phase="daily-global-test",
        ))
    await db_session.commit()

    response = client.get(
        "/admin/cost/daily?days=1",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["days_back"] == 1
    # Both users' calls are included — today's total is >= 2
    total_llm_calls = sum(r["llm_call_count"] for r in body["rows"])
    assert total_llm_calls >= 2

    # Cleanup
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp1.id))
    await db_session.execute(delete(LLMCall).where(LLMCall.experiment_id == exp2.id))
    await db_session.delete(exp1)
    await db_session.delete(exp2)
    await db_session.execute(delete(User).where(User.id == user2.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_experiment_cost_zeros_for_unknown_id(
    client: TestClient, mock_firebase: None, db_session: AsyncSession
) -> None:
    """Experiment UUID with no recorded calls returns zeros, status 200."""
    await _create_admin_user(db_session)

    fake_exp_id = uuid4()
    response = client.get(
        f"/admin/cost/experiment/{fake_exp_id}",
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["total_cost_usd"]) == Decimal("0")
    assert body["llm_call_count"] == 0
    assert body["external_api_call_count"] == 0
