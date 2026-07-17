"""Unit tests for app.services.evidence_chat_service.

The LLM call is mocked; a real async DB session is used per test (mirrors
tests/services/test_chat_service.py). Covers: happy path, ownership 404,
selection vs keyword-match context, thread-creation-on-first-message, and
second-turn thread reuse with history.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.enums import ChatRole, ChatTurnKind
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.services.evidence_chat_service import (
    EvidenceChatNotFound,
    _build_report_skeleton,
    list_evidence_chat_messages,
    send_evidence_chat_message,
)

_LLM_PATCH_TARGET = "app.services.evidence_chat_service.llm_client.complete"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def _fake_llm_result(text: str) -> SimpleNamespace:
    return SimpleNamespace(text=text)


def _refined_idea_dict() -> dict[str, Any]:
    return {
        "refined_one_liner": "A Slack app that answers HR policy questions for employees.",
        "target_audience": "HR teams at 200-person startups fielding repetitive policy questions.",
        "value_proposition": "Cuts repetitive HR question volume so teams focus on real cases.",
        "risks": [
            "Do existing Slack HR bots already own this workflow for most buyers?",
            "Is the policy content fresh enough to trust without manual review?",
            "Can pricing support a venture-scale business at SMB seat counts?",
        ],
        "project_name": "PolicyPal",
    }


def _raw_report_dict() -> dict[str, Any]:
    """Valid ValidationReport payload; q2 finding carries a distinctive token."""
    from app.schemas.validation_report import (
        Citation,
        CompetitorMention,
        Finding,
        QuestionFindings,
        SectionScore,
        ValidationReport as ValidationReportSchema,
    )

    now = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)

    def citation(domain: str) -> Citation:
        return Citation(
            url=f"https://{domain}/x", title="t", source_domain=domain, accessed_at=now
        )

    def finding(qid: str, claim: str) -> Finding:
        return Finding(
            question_id=qid,
            claim=claim,
            evidence_summary=f"Evidence summary for {qid} paraphrasing sources.",
            citations=[citation("reddit.com")],
            confidence="medium",
            confidence_rationale="One corroborating source.",
        )

    claims = {
        "q1": "Buyers actively search for a Slack knowledge assistant tool today.",
        "q2": "Competing tools charge a per-seat pricing model that frustrates buyers.",
        "q3": "Handbook content goes stale quickly without an owner assigned.",
        "q4": "Procurement complexity slows adoption at larger organizations.",
        "q5": "Integration with existing HR systems is a common feature request.",
    }

    report = ValidationReportSchema(
        executive_summary=(
            "Executive summary long enough to satisfy the fifty character minimum "
            "constraint for this field."
        ),
        questions_and_findings=[
            QuestionFindings(
                question_id=qid,
                question=f"Question text for {qid}?",
                findings=[finding(qid, claims[qid])],
                evidence_gap=None,
            )
            for qid in ["q1", "q2", "q3", "q4", "q5"]
        ],
        competitors=[
            CompetitorMention(
                name="Guru",
                description="A knowledge tool with Slack integration.",
                positioning_vs_idea="Overlaps with the core Slack Q&A function of the idea.",
                citations=[citation("g2.com")],
            )
        ],
        market_signals="Active buyer demand; no reliable TAM figure in results.",
        distribution_signals="Slack App Directory listing is the primary channel.",
        regulatory_signals=None,
        risks_assessment=(
            "Competitor risk confirmed by q2; staleness risk confirmed by q3; "
            "procurement complexity partially confirmed."
        ),
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms core coverage; iterate on the always-current handbook wedge "
            "before proceeding to build."
        ),
        research_limitations="Market size data was not found in the search results.",
        voices=None,
        rubric_version_used="v1",
        section_scores=[
            SectionScore(
                section_id="market",
                label="Market demand",
                score=70,
                rationale="Buyer demand evidenced by review counts.",
            ),
            SectionScore(
                section_id="competition",
                label="Competitive moat",
                score=45,
                rationale="Crowded field.",
            ),
        ],
        overall_score=62,
    )
    return report.model_dump(mode="json")


async def _persist_user(db: AsyncSession) -> User:
    user = User(
        firebase_uid=f"evi-svc-{uuid4()}",
        email=f"evi-{uuid4()}@example.com",
        name="Evidence Test User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _persist_experiment_with_report(db: AsyncSession, user: User) -> Experiment:
    experiment = Experiment(
        user_id=user.id,
        raw_idea="A Slack app that answers HR policy questions.",
        name="PolicyPal",
        refined_idea=_refined_idea_dict(),
    )
    db.add(experiment)
    await db.flush()
    db.add(
        ValidationReport(
            experiment_id=experiment.id,
            raw_report=_raw_report_dict(),
        )
    )
    await db.commit()
    await db.refresh(experiment)
    return experiment


# ---------------------------------------------------------------------------
# Happy path + persistence shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_send_happy_path_persists_turn_and_creates_thread(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    mock_complete.return_value = _fake_llm_result("Per q2, competitors use per-seat pricing.")
    user = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, user)

    result = await send_evidence_chat_message(
        db_session, user, experiment.id, "Tell me about the competition."
    )

    assert result.user_message.role == ChatRole.USER
    assert result.assistant_message.role == ChatRole.ASSISTANT
    assert result.assistant_message.content == "Per q2, competitors use per-seat pricing."
    assert result.user_message.turn_kind == ChatTurnKind.EVIDENCE_CHAT
    assert result.assistant_message.turn_kind == ChatTurnKind.EVIDENCE_CHAT
    assert result.user_message.parent_message_id is None
    assert result.assistant_message.parent_message_id is None

    # Thread created + linked on the experiment.
    await db_session.refresh(experiment)
    assert experiment.evidence_thread_id == result.thread_id
    thread = await db_session.get(ChatThread, result.thread_id)
    assert thread is not None
    assert thread.title == "Evidence chat: PolicyPal"

    # LLM call used the evidence-chat prompt name + phase.
    assert mock_complete.await_count == 1
    kwargs = mock_complete.call_args.kwargs
    assert kwargs["prompt_name"] == "evidence_chat_v1"
    assert kwargs["phase"] == "evidence_chat"
    assert kwargs["max_tokens"] == 1024


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_send_empty_message_raises_valueerror(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    user = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, user)
    with pytest.raises(ValueError):
        await send_evidence_chat_message(db_session, user, experiment.id, "   ")
    mock_complete.assert_not_awaited()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_send_other_user_raises_not_found(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    owner = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, owner)
    other = await _persist_user(db_session)

    with pytest.raises(EvidenceChatNotFound):
        await send_evidence_chat_message(db_session, other, experiment.id, "Hi")
    mock_complete.assert_not_awaited()


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_send_missing_report_raises_not_found(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    user = await _persist_user(db_session)
    experiment = Experiment(
        user_id=user.id, raw_idea="idea", name="No Report"
    )
    db_session.add(experiment)
    await db_session.commit()
    await db_session.refresh(experiment)

    with pytest.raises(EvidenceChatNotFound):
        await send_evidence_chat_message(db_session, user, experiment.id, "Hi")
    mock_complete.assert_not_awaited()


# ---------------------------------------------------------------------------
# Selection vs keyword-match context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_selection_path_includes_selection_and_enclosing_question(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    mock_complete.return_value = _fake_llm_result("ok")
    user = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, user)

    await send_evidence_chat_message(
        db_session,
        user,
        experiment.id,
        "Explain this part.",
        selection_text="Buyers actively search for a Slack knowledge assistant",
        selection_question_id="q1",
    )

    user_prompt = mock_complete.call_args.kwargs["user"]
    assert "<selection>" in user_prompt
    assert "Buyers actively search for a Slack knowledge assistant" in user_prompt
    assert "Enclosing question q1" in user_prompt


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_keyword_match_path_surfaces_relevant_finding(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    mock_complete.return_value = _fake_llm_result("ok")
    user = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, user)

    # "pricing" overlaps only the q2 finding claim.
    await send_evidence_chat_message(
        db_session, user, experiment.id, "What is the pricing situation?"
    )

    user_prompt = mock_complete.call_args.kwargs["user"]
    assert "per-seat pricing model" in user_prompt
    assert "<selection>" not in user_prompt


# ---------------------------------------------------------------------------
# Thread reuse + history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch(_LLM_PATCH_TARGET, new_callable=AsyncMock)
async def test_second_turn_reuses_thread_and_includes_history(
    mock_complete: AsyncMock, db_session: AsyncSession
) -> None:
    mock_complete.return_value = _fake_llm_result("first reply")
    user = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, user)

    first = await send_evidence_chat_message(
        db_session, user, experiment.id, "My first evidence question."
    )

    mock_complete.return_value = _fake_llm_result("second reply")
    second = await send_evidence_chat_message(
        db_session, user, experiment.id, "My second evidence question."
    )

    assert first.thread_id == second.thread_id

    # Exactly one evidence thread for this experiment.
    thread_count = await db_session.scalar(
        select(func.count())
        .select_from(ChatThread)
        .where(ChatThread.user_id == user.id)
    )
    assert thread_count == 1

    # Second prompt carries the first turn in <chat_history>.
    second_prompt = mock_complete.call_args.kwargs["user"]
    assert "My first evidence question." in second_prompt
    assert "first reply" in second_prompt

    # Four EVIDENCE_CHAT messages total (2 user + 2 assistant).
    msg_count = await db_session.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.thread_id == first.thread_id,
            ChatMessage.turn_kind == ChatTurnKind.EVIDENCE_CHAT,
        )
    )
    assert msg_count == 4


# ---------------------------------------------------------------------------
# list_evidence_chat_messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_messages_empty_before_first_turn(db_session: AsyncSession) -> None:
    user = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, user)

    thread_id, messages = await list_evidence_chat_messages(
        db_session, user, experiment.id
    )
    assert thread_id is None
    assert messages == []


@pytest.mark.asyncio
async def test_list_messages_other_user_raises_not_found(
    db_session: AsyncSession,
) -> None:
    owner = await _persist_user(db_session)
    experiment = await _persist_experiment_with_report(db_session, owner)
    other = await _persist_user(db_session)

    with pytest.raises(EvidenceChatNotFound):
        await list_evidence_chat_messages(db_session, other, experiment.id)


# ---------------------------------------------------------------------------
# Legacy-report skeleton (overall_score=None, section_scores=[])
# ---------------------------------------------------------------------------


def test_legacy_report_skeleton_omits_score_lines() -> None:
    """Legacy reports predate the scoring engine: no 'Overall score:' line and
    no 'Section scores:' block should appear in the skeleton."""
    from app.schemas.validation_report import ValidationReport as ValidationReportSchema

    report = ValidationReportSchema.model_validate(_raw_report_dict()).model_copy(
        update={"overall_score": None, "section_scores": []}
    )
    experiment = SimpleNamespace(
        refined_idea_current=None, refined_idea=None, name="Legacy Project"
    )

    skeleton = _build_report_skeleton(experiment, report)

    assert "Overall score:" not in skeleton
    assert "Section scores:" not in skeleton
    # Other sections still render.
    assert "Overall recommendation:" in skeleton
    assert "Research questions:" in skeleton
    assert "Research limitations:" in skeleton
