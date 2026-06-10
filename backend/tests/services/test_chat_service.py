"""Unit tests for app.services.chat_service.

All LLM and dispatcher calls are mocked. Uses a real async DB session per test.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from instructor.core.exceptions import InstructorRetryException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind, DispatchTrigger, ExperimentStatus
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.refinement_idempotency import RefinementIdempotency
from app.db.models.user import User
from app.dispatchers.protocol import DispatchError
from app.schemas.refinement import RefinedIdea, RefinementTurnDecision
from app.services.chat_service import (
    ChatAuthorizationError,
    ChatTurnResult,
    handle_turn,
)
from app.services.experiment_service import InvalidExperimentState
from app.services.rollout import _hash_bucket
from tests.services.test_rollout import _find_uuid

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
        assistant_message="Who specifically feels this pain day to day?",
        clarifying_dimension="audience",
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


class _RecordingDispatcher:
    def __init__(self, *, raise_on_dispatch: Exception | None = None) -> None:
        self.dispatched: list[object] = []
        self._raise = raise_on_dispatch

    async def dispatch(self, experiment_id: object) -> None:
        if self._raise is not None:
            raise self._raise
        self.dispatched.append(experiment_id)


@pytest.fixture(autouse=True)
def _auto_fire_chat_on_by_default(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Most chat_service tests expect the pre-rollout dispatch path (mode=on)."""
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "on")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


async def _persist_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"chat-svc-{uuid4()}",
        email=f"chat-{uuid4()}@example.com",
        name="Chat Test User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _persist_thread(
    db: AsyncSession,
    user: User,
    *,
    title: str | None = "Existing thread",
) -> ChatThread:
    thread = ChatThread(user_id=user.id, title=title)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def _persist_refinement_experiment_with_id(
    db: AsyncSession,
    user: User,
    thread: ChatThread,
    experiment_id: UUID,
) -> Experiment:
    experiment = Experiment(
        id=experiment_id,
        user_id=user.id,
        thread_id=thread.id,
        raw_idea=_DR_MESSAGE,
        status=ExperimentStatus.REFINING,
        refinement_count=0,
        slug=f"chat-svc-{uuid4().hex[:12]}",
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


async def _persist_refinement_experiment(
    db: AsyncSession,
    user: User,
    thread: ChatThread,
    *,
    updated_at: datetime | None = None,
) -> Experiment:
    experiment = Experiment(
        user_id=user.id,
        thread_id=thread.id,
        raw_idea=_DR_MESSAGE,
        status=ExperimentStatus.REFINING,
        refinement_count=1,
    )
    db.add(experiment)
    await db.flush()
    if updated_at is not None:
        experiment.updated_at = updated_at
    await db.commit()
    await db.refresh(experiment)
    return experiment


# ---------------------------------------------------------------------------
# Deep research
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_new_thread_creates_thread_experiment_messages_idempotency(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)
    idem_key = str(uuid4())

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=idem_key,
        dispatcher=_RecordingDispatcher(),
    )

    assert result.turn_kind == ChatTurnKind.REFINEMENT_CLARIFY
    assert result.clarifying_dimension == "audience"
    assert result.pipeline_dispatched is False
    assert result.user_facing_error is None

    thread = await db_session.get(ChatThread, result.thread_id)
    assert thread is not None
    assert thread.title == _DR_MESSAGE[:40]

    exp = await db_session.get(Experiment, result.experiment_id)
    assert exp is not None
    assert exp.status == ExperimentStatus.REFINING
    assert exp.thread_id == thread.id

    msg_count = await db_session.scalar(
        select(func.count()).select_from(ChatMessage).where(
            ChatMessage.thread_id == thread.id
        )
    )
    assert msg_count == 2

    idem = await db_session.get(
        RefinementIdempotency, {"thread_id": thread.id, "idempotency_key": idem_key}
    )
    assert idem is not None
    mock_run_turn.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_reuses_in_flight_experiment_within_window(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    existing = await _persist_refinement_experiment(db_session, user, thread)

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=thread.id,
        experiment_id=None,
        idempotency_key=str(uuid4()),
        dispatcher=_RecordingDispatcher(),
    )

    assert result.experiment_id == existing.id
    exp_count = await db_session.scalar(
        select(func.count()).select_from(Experiment).where(Experiment.thread_id == thread.id)
    )
    assert exp_count == 1


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_creates_new_experiment_when_no_in_flight_within_window(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    stale_time = datetime.now(UTC) - timedelta(hours=2)
    await _persist_refinement_experiment(
        db_session, user, thread, updated_at=stale_time
    )

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=thread.id,
        experiment_id=None,
        idempotency_key=str(uuid4()),
        dispatcher=_RecordingDispatcher(),
    )

    exp_count = await db_session.scalar(
        select(func.count()).select_from(Experiment).where(Experiment.thread_id == thread.id)
    )
    assert exp_count == 2
    assert result.experiment_id is not None


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_idempotency_replay_skips_second_run_turn(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)
    idem_key = str(uuid4())

    first = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=idem_key,
        dispatcher=_RecordingDispatcher(),
    )
    second = await handle_turn(
        db_session,
        user,
        "Different message text that should be ignored on replay.",
        deep_research=True,
        thread_id=first.thread_id,
        experiment_id=None,
        idempotency_key=idem_key,
        dispatcher=_RecordingDispatcher(),
    )

    assert second.message_id == first.message_id
    assert second.assistant_message == first.assistant_message
    mock_run_turn.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_finalize_dispatches_with_auto_fire(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _finalize_decision()
    user = await _persist_user(db_session)
    dispatcher = _RecordingDispatcher()

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=str(uuid4()),
        dispatcher=dispatcher,
    )

    assert result.pipeline_dispatched is True
    assert result.dispatched_at is not None
    assert result.turn_kind == ChatTurnKind.REFINEMENT_FINALIZE
    assert result.experiment_status == ExperimentStatus.RESEARCHING
    assert dispatcher.dispatched == [result.experiment_id]


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_finalize_dispatch_error_sets_research_failed(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _finalize_decision()
    user = await _persist_user(db_session)
    dispatcher = _RecordingDispatcher(
        raise_on_dispatch=DispatchError("scheduler unavailable")
    )

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=str(uuid4()),
        dispatcher=dispatcher,
    )

    assert result.pipeline_dispatched is False
    assert result.experiment_status == ExperimentStatus.RESEARCH_FAILED
    assert result.research_error_detail is not None
    assert "DispatchError" in result.research_error_detail
    assert result.user_facing_error is not None
    assert result.user_facing_error.message.startswith("Research didn't complete")


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_finalize_shadow_gates_dispatch(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "shadow")
    get_settings.cache_clear()

    mock_run_turn.return_value = _finalize_decision()
    user = await _persist_user(db_session)
    dispatcher = _RecordingDispatcher()

    with patch("app.services.chat_service._logger.info") as mock_info:
        result = await handle_turn(
            db_session,
            user,
            _DR_MESSAGE,
            deep_research=True,
            thread_id=None,
            experiment_id=None,
            idempotency_key=str(uuid4()),
            dispatcher=dispatcher,
        )

    assert result.pipeline_dispatched is False
    assert result.experiment_status == ExperimentStatus.REFINED
    assert dispatcher.dispatched == []
    mock_info.assert_called_once()
    assert mock_info.call_args.args[0] == "auto_fire_gated"
    assert mock_info.call_args.kwargs["mode"] == "shadow"
    assert mock_info.call_args.kwargs["would_have_fired"] is True


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_finalize_cohort_10_in_bucket_dispatches(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "cohort_10")
    get_settings.cache_clear()

    experiment_id = _find_uuid(bucket_lt=10)
    assert _hash_bucket(experiment_id) < 10

    mock_run_turn.return_value = _finalize_decision()
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    await _persist_refinement_experiment_with_id(
        db_session, user, thread, experiment_id
    )
    dispatcher = _RecordingDispatcher()

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=thread.id,
        experiment_id=experiment_id,
        idempotency_key=str(uuid4()),
        dispatcher=dispatcher,
    )

    assert result.pipeline_dispatched is True
    assert result.experiment_status == ExperimentStatus.RESEARCHING
    assert dispatcher.dispatched == [experiment_id]


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_finalize_cohort_10_out_of_bucket_refined(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTO_FIRE_CHAT_ENABLED", "cohort_10")
    get_settings.cache_clear()

    experiment_id = _find_uuid(bucket_ge=10)
    assert _hash_bucket(experiment_id) >= 10

    mock_run_turn.return_value = _finalize_decision()
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    await _persist_refinement_experiment_with_id(
        db_session, user, thread, experiment_id
    )
    dispatcher = _RecordingDispatcher()

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=thread.id,
        experiment_id=experiment_id,
        idempotency_key=str(uuid4()),
        dispatcher=dispatcher,
    )

    assert result.pipeline_dispatched is False
    assert result.experiment_status == ExperimentStatus.REFINED
    assert dispatcher.dispatched == []


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_run_turn_failure_translates_error_no_idempotency(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.side_effect = InstructorRetryException(
        "failed to parse",
        n_attempts=2,
        total_usage=0,
    )
    user = await _persist_user(db_session)
    idem_key = str(uuid4())

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=idem_key,
        dispatcher=_RecordingDispatcher(),
    )

    assert result.user_facing_error is not None
    assert "parse" in result.user_facing_error.message.lower()
    assert result.turn_kind == ChatTurnKind.REFINEMENT_CLARIFY

    idem = await db_session.get(
        RefinementIdempotency,
        {"thread_id": result.thread_id, "idempotency_key": idem_key},
    )
    assert idem is None


@pytest.mark.asyncio
async def test_dr_requires_idempotency_key(db_session: AsyncSession) -> None:
    user = await _persist_user(db_session)
    with pytest.raises(ValueError, match="idempotency_key required"):
        await handle_turn(
            db_session,
            user,
            _DR_MESSAGE,
            deep_research=True,
            thread_id=None,
            experiment_id=None,
            idempotency_key=None,
            dispatcher=_RecordingDispatcher(),
        )


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_experiment_not_owned_raises_authorization(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    owner = await _persist_user(db_session)
    other = await _persist_user(db_session)
    thread = await _persist_thread(db_session, owner)
    experiment = await _persist_refinement_experiment(db_session, owner, thread)

    with pytest.raises(ChatAuthorizationError):
        await handle_turn(
            db_session,
            other,
            _DR_MESSAGE,
            deep_research=True,
            thread_id=thread.id,
            experiment_id=experiment.id,
            idempotency_key=str(uuid4()),
            dispatcher=_RecordingDispatcher(),
        )


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_experiment_wrong_status_raises_invalid_state(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    experiment = Experiment(
        user_id=user.id,
        thread_id=thread.id,
        raw_idea=_DR_MESSAGE,
        status=ExperimentStatus.REFINED,
        refinement_count=1,
        refined_idea=_make_refined_idea().model_dump(mode="json"),
    )
    db_session.add(experiment)
    await db_session.commit()

    with pytest.raises(InvalidExperimentState):
        await handle_turn(
            db_session,
            user,
            _DR_MESSAGE,
            deep_research=True,
            thread_id=thread.id,
            experiment_id=experiment.id,
            idempotency_key=str(uuid4()),
            dispatcher=_RecordingDispatcher(),
        )


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_dr_clarify_populates_turn_kind_and_dimension(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)

    result = await handle_turn(
        db_session,
        user,
        _DR_MESSAGE,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=str(uuid4()),
        dispatcher=_RecordingDispatcher(),
    )

    assert result.turn_kind == ChatTurnKind.REFINEMENT_CLARIFY
    assert result.clarifying_dimension == "audience"


@pytest.mark.asyncio
@patch("app.services.chat_service.refinement_service.run_turn", new_callable=AsyncMock)
async def test_new_thread_title_sanitizes_control_chars(
    mock_run_turn: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_run_turn.return_value = _clarify_decision()
    user = await _persist_user(db_session)
    messy = "Hello\x00world\nline2" + ("x" * 50)

    result = await handle_turn(
        db_session,
        user,
        messy,
        deep_research=True,
        thread_id=None,
        experiment_id=None,
        idempotency_key=str(uuid4()),
        dispatcher=_RecordingDispatcher(),
    )

    thread = await db_session.get(ChatThread, result.thread_id)
    assert thread is not None
    assert "\n" not in (thread.title or "")
    assert "\x00" not in (thread.title or "")
    assert len(thread.title or "") <= 40


# ---------------------------------------------------------------------------
# Plain chat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.chat_service.reply_plain", new_callable=AsyncMock)
async def test_plain_chat_new_thread_persists_normal_chat_messages(
    mock_reply_plain: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_reply_plain.return_value = "Fivvle runs structured market research on your idea."
    user = await _persist_user(db_session)

    result = await handle_turn(
        db_session,
        user,
        "How does Fivvle research work?",
        deep_research=False,
        thread_id=None,
        experiment_id=None,
        idempotency_key=None,
        dispatcher=_RecordingDispatcher(),
    )

    assert result.experiment_id is None
    assert result.turn_kind == ChatTurnKind.NORMAL_CHAT
    mock_reply_plain.assert_awaited_once()

    assistant_row = await db_session.get(ChatMessage, result.message_id)
    assert assistant_row is not None
    assert assistant_row.turn_kind == ChatTurnKind.NORMAL_CHAT


@pytest.mark.asyncio
@patch("app.services.chat_service.reply_plain", new_callable=AsyncMock)
async def test_plain_chat_allows_null_idempotency_key(
    mock_reply_plain: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_reply_plain.return_value = "Short answer."
    user = await _persist_user(db_session)

    result = await handle_turn(
        db_session,
        user,
        "What is a beachhead market?",
        deep_research=False,
        thread_id=None,
        experiment_id=None,
        idempotency_key=None,
        dispatcher=_RecordingDispatcher(),
    )

    assert isinstance(result, ChatTurnResult)


@pytest.mark.asyncio
@patch("app.services.chat_service.reply_plain", new_callable=AsyncMock)
async def test_plain_chat_excludes_pipeline_system_messages_from_history(
    mock_reply_plain: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_reply_plain.return_value = "Plain reply."
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)

    db_session.add(
        ChatMessage(
            thread_id=thread.id,
            role=ChatRole.ASSISTANT,
            content="Research is ready. → View report",
            turn_kind=ChatTurnKind.PIPELINE_COMPLETE,
        )
    )
    await db_session.commit()

    await handle_turn(
        db_session,
        user,
        "Follow-up question about positioning.",
        deep_research=False,
        thread_id=thread.id,
        experiment_id=None,
        idempotency_key=None,
        dispatcher=_RecordingDispatcher(),
    )

    history_arg = mock_reply_plain.await_args.args[1]
    assert all("Research is ready" not in content for _, content in history_arg)


@pytest.mark.asyncio
@patch("app.services.chat_service.reply_discussion", new_callable=AsyncMock)
async def test_post_refinement_plain_chat_uses_discuss_turn(
    mock_reply_discussion: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_reply_discussion.return_value = "Your report suggests iterating on distribution."
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)
    experiment = Experiment(
        user_id=user.id,
        thread_id=thread.id,
        raw_idea=_DR_MESSAGE,
        status=ExperimentStatus.RESEARCH_READY,
        refinement_count=1,
        refined_idea=_make_refined_idea().model_dump(mode="json"),
    )
    db_session.add(experiment)
    await db_session.commit()

    result = await handle_turn(
        db_session,
        user,
        "What should I focus on next?",
        deep_research=False,
        thread_id=thread.id,
        experiment_id=experiment.id,
        idempotency_key=None,
        dispatcher=_RecordingDispatcher(),
    )

    assert result.turn_kind == ChatTurnKind.DISCUSS
    assert result.experiment_id == experiment.id
    assert result.experiment_status == ExperimentStatus.RESEARCH_READY
    mock_reply_discussion.assert_awaited_once()

    assistant_row = await db_session.get(ChatMessage, result.message_id)
    assert assistant_row is not None
    assert assistant_row.turn_kind == ChatTurnKind.DISCUSS


@pytest.mark.asyncio
@patch("app.services.chat_service.reply_plain", new_callable=AsyncMock)
async def test_edit_user_message_truncates_downstream_and_replays(
    mock_reply_plain: AsyncMock,
    db_session: AsyncSession,
) -> None:
    mock_reply_plain.return_value = "Updated assistant reply."
    user = await _persist_user(db_session)
    thread = await _persist_thread(db_session, user)

    user_msg = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="Original question",
    )
    old_assistant = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.ASSISTANT,
        content="Old answer",
        turn_kind=ChatTurnKind.NORMAL_CHAT,
    )
    later_user = ChatMessage(
        thread_id=thread.id,
        role=ChatRole.USER,
        content="Follow-up",
    )
    db_session.add_all([user_msg, old_assistant, later_user])
    await db_session.commit()
    await db_session.refresh(user_msg)

    from app.services.chat_service import handle_edit_turn

    result = await handle_edit_turn(
        db_session,
        user,
        thread.id,
        user_msg.id,
        "Edited question",
        _RecordingDispatcher(),
    )

    assert result.edited_message_id == user_msg.id
    assert result.assistant_message == "Updated assistant reply."

    debug_lines = [
        f"{m.role.value}: {m.content!r}" for m in result.messages
    ]
    assert len(result.messages) == 2, (
        "expected edited user + new assistant; got:\n  "
        + "\n  ".join(debug_lines)
    )
    assert result.messages[0].content == "Edited question"
    assert result.messages[1].content == "Updated assistant reply."

    remaining = await db_session.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread.id)
    )
    rows = list(remaining.scalars().all())
    assert len(rows) == 2
    assert all(row.content != "Follow-up" for row in rows)
    assert all(row.content != "Old answer" for row in rows)
