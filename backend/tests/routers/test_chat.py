"""Integration tests for POST /chat/turn."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from instructor.core.exceptions import InstructorRetryException

from app.config import get_settings
from app.db.enums import ChatTurnKind, ExperimentStatus
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.dispatchers.dependencies import get_dispatcher_dep
from app.dispatchers.protocol import DispatchError
from app.main import app
from app.schemas.refinement import ClarifyingQuestion, RefinedIdea, RefinementTurnDecision

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}

_DR_MESSAGE = (
    "I want to build a tool for CrossFit coaches who spend hours each week "
    "building client programs in Excel instead of coaching."
)

_VALID_RISKS = [
    "Is the market large enough to support a venture-scale business at current TAM?",
    "Do existing enterprise tools already solve this problem for most buyers?",
    "Can the unit economics work at the target price point given CAC estimates?",
]


def _make_refined_idea() -> RefinedIdea:
    return RefinedIdea(
        refined_one_liner="A tool for CrossFit coaches to build client programs faster.",
        target_audience=(
            "CrossFit coaches managing 10+ clients who currently use Excel for programming."
        ),
        value_proposition=(
            "Cuts weekly program design time so coaches can focus on in-gym coaching."
        ),
        risks=_VALID_RISKS,
        headline="Stop rebuilding the same Excel templates every week.",
        subheadline="Purpose-built programming for CrossFit coaches.",
        cta_text="Join the waitlist",
    )


def _clarify_decision() -> RefinementTurnDecision:
    return RefinementTurnDecision(
        decision="clarify",
        assistant_message="Got it — let's pin down who this is for.",
        clarifying_dimension="audience",
        clarifying_questions=[
            ClarifyingQuestion(
                question="Who specifically feels this pain day to day?",
                selection_mode="multiple",
                options=["CrossFit coaches", "Personal trainers", "Gym owners"],
            ),
        ],
        reasoning_trace="Need a concrete audience before research.",
    )


def _finalize_decision() -> RefinementTurnDecision:
    return RefinementTurnDecision(
        decision="finalize",
        assistant_message=(
            "Researching: a programming tool for CrossFit coaches replacing Excel workflows."
        ),
        refined_idea=_make_refined_idea(),
        reasoning_trace="Audience and value prop are clear.",
    )


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Chat Router Test"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _chat_turn_payload(
    *,
    deep_research: bool = True,
    thread_id: str | None = None,
    experiment_id: str | None = None,
    idempotency_key: str | None = None,
    message: str = _DR_MESSAGE,
) -> dict:
    body: dict = {
        "message": message,
        "deep_research": deep_research,
        "thread_id": thread_id,
        "experiment_id": experiment_id,
        "idempotency_key": idempotency_key,
    }
    return body


def _force_experiment_status(
    experiment_id: str,
    new_status: ExperimentStatus,
) -> None:
    from sqlalchemy import update  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.experiment import Experiment  # noqa: PLC0415

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                await session.execute(
                    update(Experiment)
                    .where(Experiment.id == UUID(experiment_id))
                    .values(status=new_status)
                )
                await session.commit()
        finally:
            await engine.dispose()

    import asyncio  # noqa: PLC0415

    asyncio.run(_run())


async def _persist_other_user_refinement_experiment() -> tuple[str, str]:
    """Return (other_user_experiment_id, thread_id) owned by a different user."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            other = User(
                firebase_uid=f"other-firebase-uid-{uuid4()}",
                email=f"other-{uuid4()}@example.com",
                name="Other User",
            )
            session.add(other)
            await session.flush()
            thread = ChatThread(user_id=other.id, title="Other thread")
            session.add(thread)
            await session.flush()
            experiment = Experiment(
                user_id=other.id,
                thread_id=thread.id,
                raw_idea=_DR_MESSAGE,
                status=ExperimentStatus.REFINING,
                refinement_count=0,
            )
            session.add(experiment)
            await session.commit()
            return str(experiment.id), str(thread.id)
    finally:
        await engine.dispose()


class FakeDispatcher:
    def __init__(self, *, raise_on_dispatch: Exception | None = None) -> None:
        self.dispatched: list[str] = []
        self._raise = raise_on_dispatch

    async def dispatch(self, experiment_id: object) -> None:
        if self._raise is not None:
            raise self._raise
        self.dispatched.append(str(experiment_id))


@pytest.fixture
def fake_dispatcher() -> Generator[FakeDispatcher, None, None]:
    fd = FakeDispatcher()
    app.dependency_overrides[get_dispatcher_dep] = lambda: fd
    yield fd
    app.dependency_overrides.pop(get_dispatcher_dep, None)


@pytest.fixture(autouse=True)
def _auto_fire_chat_on_by_default(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Router tests expect /chat/turn enabled unless a test overrides mode=off."""
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "on")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_run_turn() -> Generator[AsyncMock, None, None]:
    with patch(
        "app.services.chat_service.refinement_service.run_turn",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = _clarify_decision()
        yield mock


@pytest.fixture
def mock_reply_plain() -> Generator[AsyncMock, None, None]:
    with patch(
        "app.services.chat_service.reply_plain",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = (
            "Product-market fit means customers pull value from your product repeatedly."
        )
        yield mock


# ---------------------------------------------------------------------------
# Deep research — happy paths
# ---------------------------------------------------------------------------


def test_chat_turn_dr_new_thread_200(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    _sync_user(client)
    idem = str(uuid4())

    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=idem),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["thread_id"]
    assert data["message_id"]
    assert data["experiment_id"]
    assert data["turn_kind"] in (
        ChatTurnKind.REFINEMENT_CLARIFY.value,
        ChatTurnKind.REFINEMENT_FINALIZE.value,
    )
    assert data["pipeline_dispatched"] is False
    mock_run_turn.assert_awaited_once()


def test_chat_turn_dr_idempotency_replay_byte_identical(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    _sync_user(client)
    idem = str(uuid4())

    first = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=idem),
        headers=_AUTH_HEADER,
    )
    assert first.status_code == 200
    second = client.post(
        "/chat/turn",
        json=_chat_turn_payload(
            idempotency_key=idem,
            thread_id=first.json()["thread_id"],
            message="Ignored on replay.",
        ),
        headers=_AUTH_HEADER,
    )
    assert second.status_code == 200
    assert second.json() == first.json()
    mock_run_turn.assert_awaited_once()


def test_chat_turn_dr_missing_idempotency_key_422(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=None),
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 422
    body = resp.json()
    detail_str = str(body.get("detail", body))
    assert "idempotency_key" in detail_str


def test_chat_turn_dr_other_users_experiment_403(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    import asyncio  # noqa: PLC0415

    _sync_user(client)
    other_exp_id, other_thread_id = asyncio.run(
        _persist_other_user_refinement_experiment()
    )

    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(
            experiment_id=other_exp_id,
            thread_id=other_thread_id,
            idempotency_key=str(uuid4()),
        ),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden"


def test_chat_turn_dr_experiment_wrong_status_409(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    _sync_user(client)
    first = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=str(uuid4())),
        headers=_AUTH_HEADER,
    )
    assert first.status_code == 200
    exp_id = first.json()["experiment_id"]
    thread_id = first.json()["thread_id"]
    _force_experiment_status(exp_id, ExperimentStatus.RESEARCH_READY)

    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(
            experiment_id=exp_id,
            thread_id=thread_id,
            idempotency_key=str(uuid4()),
        ),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 409
    assert "REFINING" in resp.json()["detail"]


def test_chat_turn_dr_finalize_refined_no_dispatch(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    mock_run_turn.return_value = _finalize_decision()
    _sync_user(client)

    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=str(uuid4())),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_dispatched"] is False
    assert data["experiment_status"] == ExperimentStatus.REFINED.value
    assert data["dispatched_at"] is None
    assert data["turn_kind"] == ChatTurnKind.REFINEMENT_FINALIZE.value
    assert fake_dispatcher.dispatched == []


def test_chat_turn_dr_finalize_deferred_even_if_dispatcher_would_fail(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
) -> None:
    mock_run_turn.return_value = _finalize_decision()
    fd = FakeDispatcher(raise_on_dispatch=DispatchError("scheduler unavailable"))
    app.dependency_overrides[get_dispatcher_dep] = lambda: fd
    try:
        _sync_user(client)
        resp = client.post(
            "/chat/turn",
            json=_chat_turn_payload(idempotency_key=str(uuid4())),
            headers=_AUTH_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_dispatched"] is False
        assert data["experiment_status"] == ExperimentStatus.REFINED.value
        assert data["assistant_message"].lower().startswith("researching:")
        assert fd.dispatched == []
    finally:
        app.dependency_overrides.pop(get_dispatcher_dep, None)


def test_chat_turn_dr_run_turn_failure_returns_translated_message_200(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    mock_run_turn.side_effect = InstructorRetryException(
        "failed to parse",
        n_attempts=2,
        total_usage=0,
    )
    _sync_user(client)

    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=str(uuid4())),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_status"] == ExperimentStatus.REFINING.value
    assert "parse" in data["assistant_message"].lower()


# ---------------------------------------------------------------------------
# Plain chat
# ---------------------------------------------------------------------------


def test_chat_turn_plain_chat_200(
    client: TestClient,
    mock_firebase: None,
    mock_reply_plain: AsyncMock,
    fake_dispatcher: FakeDispatcher,
) -> None:
    _sync_user(client)
    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(
            deep_research=False,
            idempotency_key=None,
            message="What's a good way to think about product-market fit?",
        ),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["turn_kind"] == ChatTurnKind.NORMAL_CHAT.value
    assert data["experiment_id"] is None
    assert data["pipeline_dispatched"] is False
    assert data["assistant_message"] == mock_reply_plain.return_value
    mock_reply_plain.assert_awaited_once()


def test_chat_turn_missing_auth_401(
    client: TestClient,
    mock_firebase: None,
) -> None:
    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=str(uuid4())),
    )
    assert resp.status_code == 401


def test_chat_turn_empty_message_422(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(message="", idempotency_key=str(uuid4())),
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 422


def test_chat_turn_off_returns_404(
    client: TestClient,
    mock_firebase: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "off")
    get_settings.cache_clear()

    _sync_user(client)
    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=str(uuid4())),
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 404


def test_chat_turn_shadow_finalize_refined_no_dispatch(
    client: TestClient,
    mock_firebase: None,
    mock_run_turn: AsyncMock,
    fake_dispatcher: FakeDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "shadow")
    get_settings.cache_clear()

    mock_run_turn.return_value = _finalize_decision()
    _sync_user(client)

    resp = client.post(
        "/chat/turn",
        json=_chat_turn_payload(idempotency_key=str(uuid4())),
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["experiment_status"] == ExperimentStatus.REFINED.value
    assert data["pipeline_dispatched"] is False
    assert fake_dispatcher.dispatched == []
