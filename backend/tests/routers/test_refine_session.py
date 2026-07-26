"""Tests for refine finalize + session reset endpoints."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ChatRole, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from tests.conftest import FAKE_FIREBASE_UID

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}

_REFINED = {
    "refined_one_liner": "A Slack bot that answers HR policy questions instantly.",
    "target_audience": (
        "Operations managers at 50-500 person companies who answer "
        "20-30 repeated policy questions per week in Slack."
    ),
    "value_proposition": (
        "Cuts time spent answering the same policy questions from hours "
        "per week to near-zero by answering from the handbook in Slack."
    ),
    "risks": [
        "Do ops teams already use Notion AI or Guru for the same job?",
        "Will legal block a bot that quotes policy without review?",
        "Is Slack the primary channel for policy questions in mid-market?",
    ],
    "headline": "Policy answers in Slack, not another ticket",
    "subheadline": "Point the bot at your handbook; ops stops repeating themselves.",
    "cta_text": "Join the waitlist",
}


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
        json={"name": "Refine Session Tester"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.text


def _create_spark(client: TestClient) -> str:
    create = client.post(
        "/experiments",
        headers=_AUTH_HEADER,
        json={"name": "Refine Session Test"},
    )
    assert create.status_code == 201, create.text
    return create.json()["id"]


def _seed_refined(experiment_id: str, *, status: ExperimentStatus) -> None:
    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            result = await db.execute(
                select(Experiment).where(Experiment.id == UUID(experiment_id))
            )
            exp = result.scalar_one()
            # Finalize copies refined_idea_current → refined_idea.
            exp.refined_idea_current = _REFINED
            exp.status = status
            exp.raw_idea = (
                "A slack bot that answers HR policy questions so ops managers "
                "don't have to keep repeating themselves in channels."
            )
            await db.commit()

    _run_db(_work)


def _seed_thread_with_messages(experiment_id: str) -> None:
    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            user = (
                await db.execute(
                    select(User).where(User.firebase_uid == FAKE_FIREBASE_UID)
                )
            ).scalar_one()
            exp = (
                await db.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id))
                )
            ).scalar_one()
            thread = ChatThread(user_id=user.id, title="refine")
            db.add(thread)
            await db.flush()
            exp.thread_id = thread.id
            exp.refined_idea = _REFINED
            exp.refined_idea_current = _REFINED
            exp.status = ExperimentStatus.REFINED
            db.add(
                ChatMessage(
                    thread_id=thread.id,
                    role=ChatRole.USER,
                    content="hello",
                    experiment_id=exp.id,
                )
            )
            db.add(
                ChatMessage(
                    thread_id=thread.id,
                    role=ChatRole.ASSISTANT,
                    content="hi",
                    experiment_id=exp.id,
                )
            )
            await db.commit()

    _run_db(_work)


def _message_count(experiment_id: str) -> int:
    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            exp = (
                await db.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id))
                )
            ).scalar_one()
            assert exp.thread_id is not None
            result = await db.execute(
                select(func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.thread_id == exp.thread_id)
            )
            return int(result.scalar_one())

    return int(_run_db(_work))


def test_finalize_returns_400_when_no_refined_idea(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_spark(client)

    resp = client.post(
        f"/experiments/{experiment_id}/refine/finalize",
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 400, resp.text
    assert "refined idea" in resp.json()["detail"].lower()


def test_finalize_transitions_to_refined_when_idea_present(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_spark(client)
    _seed_refined(experiment_id, status=ExperimentStatus.REFINING)

    resp = client.post(
        f"/experiments/{experiment_id}/refine/finalize",
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REFINED"
    assert resp.json()["refined_idea"] is not None
    assert _refined_idea_version(experiment_id) == 1

    # Re-finalize bumps again.
    resp2 = client.post(
        f"/experiments/{experiment_id}/refine/finalize",
        headers=_AUTH_HEADER,
    )
    assert resp2.status_code == 200, resp2.text
    assert _refined_idea_version(experiment_id) == 2


def _refined_idea_version(experiment_id: str) -> int:
    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            exp = (
                await db.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id))
                )
            ).scalar_one()
            return int(exp.refined_idea_version)

    return int(_run_db(_work))


def test_reset_session_clears_messages_and_refined_idea(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_spark(client)
    _seed_thread_with_messages(experiment_id)

    resp = client.delete(
        f"/experiments/{experiment_id}/refine/session",
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "SPARK"
    assert body["refined_idea"] is None
    assert body.get("refined_idea_current") is None
    assert _message_count(experiment_id) == 0


def _seed_raw_idea(experiment_id: str) -> None:
    async def _work(sm):  # type: ignore[no-untyped-def]
        async with sm() as db:
            exp = (
                await db.execute(
                    select(Experiment).where(Experiment.id == UUID(experiment_id))
                )
            ).scalar_one()
            exp.raw_idea = (
                "A slack bot that answers HR policy questions so ops managers "
                "don't have to keep repeating themselves in channels."
            )
            await db.commit()

    _run_db(_work)


def test_opener_requires_raw_idea(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_spark(client)

    resp = client.post(
        f"/experiments/{experiment_id}/refine/opener",
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 400, resp.text
    assert "spark" in resp.json()["detail"].lower()


def test_opener_generates_and_is_idempotent(
    client: TestClient,
    mock_firebase: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.llm.client import LLMResult
    from decimal import Decimal

    async def _fake_complete(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return LLMResult(
            text=(
                "An HR policy bot in Slack — the ops-manager angle is sharp. "
                "Before we dig in, are you solving for mid-market teams first, "
                "or enterprise with heavier compliance needs?"
            ),
            provider="kimi",
            model="kimi-k2.6",
            prompt_tokens=10,
            completion_tokens=40,
            cost_usd=Decimal("0.001"),
            latency_ms=12,
        )

    monkeypatch.setattr(
        "app.services.refiner_opener_service.llm_client.complete",
        _fake_complete,
    )

    _sync_user(client)
    experiment_id = _create_spark(client)
    _seed_raw_idea(experiment_id)

    first = client.post(
        f"/experiments/{experiment_id}/refine/opener",
        headers=_AUTH_HEADER,
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["role"] == "assistant"
    assert "HR policy" in body["content"] or "ops" in body["content"].lower()
    assert _message_count(experiment_id) == 1

    second = client.post(
        f"/experiments/{experiment_id}/refine/opener",
        headers=_AUTH_HEADER,
    )
    assert second.status_code == 400, second.text
    assert "already" in second.json()["detail"].lower()
    assert _message_count(experiment_id) == 1
