"""Tests for POST /experiments/{id}/refine/complete (progressive phase reveal)."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.experiment import Experiment
from app.db.models.user import User

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _run_db(coro_factory):  # type: ignore[no-untyped-def]
    """Run an async DB helper on a dedicated engine/loop (avoids TestClient loop clash)."""

    engine = create_async_engine(
        get_settings().database_url, pool_size=1, max_overflow=0
    )
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _go() -> object:
        try:
            return await coro_factory(sm)
        finally:
            await engine.dispose()

    return asyncio.get_event_loop().run_until_complete(_go())


def _sync_user(client: TestClient) -> None:
    resp = client.post(
        "/users/sync",
        json={"name": "Refine Complete Tester"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.text


def _create_spark(client: TestClient) -> str:
    create = client.post(
        "/experiments",
        headers=_AUTH_HEADER,
        json={"name": "Refine Complete Test"},
    )
    assert create.status_code == 201, create.text
    return create.json()["id"]


def _stamp(experiment_id: str) -> object:
    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            exp = (
                await db.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id))
                )
            ).scalar_one()
            return exp.refine_completed_at

    return _run_db(_work)


def _create_foreign_experiment() -> str:
    """An experiment owned by somebody else, for the ownership check."""

    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            other = User(
                firebase_uid=f"fb-{uuid4()}",
                email=f"{uuid4()}@example.com",
            )
            db.add(other)
            await db.flush()
            exp = Experiment(user_id=other.id, raw_idea="Someone else's idea")
            db.add(exp)
            await db.commit()
            return str(exp.id)

    return str(_run_db(_work))


def test_complete_is_idempotent(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_spark(client)
    assert _stamp(experiment_id) is None

    first = client.post(
        f"/experiments/{experiment_id}/refine/complete",
        headers=_AUTH_HEADER,
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["refine_completed_at"] is not None

    # Second call must not error and must not move the stamp.
    second = client.post(
        f"/experiments/{experiment_id}/refine/complete",
        headers=_AUTH_HEADER,
    )
    assert second.status_code == 200, second.text
    assert second.json()["refine_completed_at"] == body["refine_completed_at"]
    assert _stamp(experiment_id) is not None


def test_complete_does_not_require_a_refined_idea(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """Unlike finalize, completion is a pure founder declaration."""
    _sync_user(client)
    experiment_id = _create_spark(client)

    resp = client.post(
        f"/experiments/{experiment_id}/refine/complete",
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["refined_idea"] is None
    assert resp.json()["refine_completed_at"] is not None


def test_complete_rejects_unowned_experiment(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    foreign_id = _create_foreign_experiment()

    resp = client.post(
        f"/experiments/{foreign_id}/refine/complete",
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 404, resp.text
    assert _stamp(foreign_id) is None


def test_complete_requires_auth(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    experiment_id = _create_spark(client)

    resp = client.post(f"/experiments/{experiment_id}/refine/complete")
    assert resp.status_code == 401, resp.text
    assert _stamp(experiment_id) is None
