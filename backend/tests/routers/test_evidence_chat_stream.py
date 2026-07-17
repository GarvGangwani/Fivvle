"""Tests for the evidence-chat streaming (SSE) endpoint + generator.

Endpoint:
- POST /experiments/{id}/evidence-chat/stream  (text/event-stream)

Happy + error paths go through the TestClient (real DB, lifespan-managed engine,
LLM streaming mocked). The client-disconnect path is exercised at the service
level by driving the async generator and throwing CancelledError into it — the
DB session lifecycle (own session in the generator) is verified there.

DB session lifecycle under test:
- the HTTP handler persists + commits the USER message on the request session
  BEFORE the generator starts (survives disconnect);
- the generator opens its OWN session and owns the assistant persist + active
  leaf + LLMCall accounting on every terminal path.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_STREAM_PATCH_TARGET = "app.llm.client.complete_stream"


def _sync_user(client: TestClient) -> str:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_experiment(client: TestClient, name: str = "Evidence Stream Test") -> str:
    resp = client.post("/experiments", json={"name": name}, headers=_AUTH_HEADER)
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def _raw_report_dict() -> dict[str, Any]:
    from app.schemas.validation_report import (
        Citation,
        CompetitorMention,
        Finding,
        QuestionFindings,
        SectionScore,
        ValidationReport,
    )

    now = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)

    def citation(domain: str) -> Citation:
        return Citation(
            url=f"https://{domain}/x", title="t", source_domain=domain, accessed_at=now
        )

    def finding(qid: str) -> Finding:
        return Finding(
            question_id=qid,
            claim=f"Claim for {qid} with enough length to pass validation.",
            evidence_summary=f"Evidence summary for {qid} paraphrasing sources.",
            citations=[citation("reddit.com")],
            confidence="medium",
            confidence_rationale="One corroborating source.",
        )

    report = ValidationReport(
        executive_summary=(
            "Executive summary long enough to satisfy the fifty character minimum "
            "constraint for this field."
        ),
        questions_and_findings=[
            QuestionFindings(
                question_id=qid,
                question=f"Question text {qid}?",
                findings=[finding(qid)],
                evidence_gap=None,
            )
            for qid in [f"q{i}" for i in range(1, 6)]
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
        risks_assessment="Competitor risk confirmed by q2; staleness risk confirmed by q1.",
        overall_recommendation="iterate",
        recommendation_rationale=(
            "q2 confirms core coverage; iterate on the always-current handbook wedge."
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
            )
        ],
        overall_score=62,
    )
    return report.model_dump(mode="json")


def _seed_validation_report(experiment_id: str, raw_report: dict[str, Any]) -> None:
    from app.db.models.validation_report import ValidationReport as ValidationReportRow

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                session.add(
                    ValidationReportRow(
                        experiment_id=UUID(experiment_id),
                        raw_report=raw_report,
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


def _count_llm_calls(experiment_id: str) -> int:
    from app.db.models.llm_call import LLMCall

    async def _run() -> int:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                return await session.scalar(
                    select(func.count())
                    .select_from(LLMCall)
                    .where(LLMCall.experiment_id == UUID(experiment_id))
                )
        finally:
            await engine.dispose()

    return asyncio.get_event_loop().run_until_complete(_run())


def _fake_stream_ok(*, provider, model, system, user, usage, max_tokens, temperature):
    async def _gen():
        usage.provider = provider
        usage.model = model
        for tok in ["Per ", "q2, ", "pricing ", "varies by seat."]:
            usage.text_parts.append(tok)
            yield tok
        usage.prompt_tokens = 120
        usage.completion_tokens = 18

    return _gen()


def _fake_stream_error(*, provider, model, system, user, usage, max_tokens, temperature):
    async def _gen():
        usage.provider = provider
        usage.model = model
        usage.text_parts.append("partial")
        yield "partial"
        raise RuntimeError("boom")

    return _gen()


def _parse_sse(text: str) -> list[tuple[str | None, dict | None]]:
    events: list[tuple[str | None, dict | None]] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event: str | None = None
        data: dict | None = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
        events.append((event, data))
    return events


def _stream_url(exp_id: str) -> str:
    return f"/experiments/{exp_id}/evidence-chat/stream"


# ---------------------------------------------------------------------------


def test_stream_unauthenticated_returns_401(client: TestClient) -> None:
    with client.stream(
        "POST", _stream_url(str(uuid4())), json={"message": "hi"}
    ) as resp:
        assert resp.status_code == 401
        resp.read()


def test_stream_happy_path(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    with patch(_STREAM_PATCH_TARGET, _fake_stream_ok):
        with client.stream(
            "POST",
            _stream_url(exp_id),
            json={"message": "What is the pricing situation?"},
            headers=_AUTH_HEADER,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = "".join(resp.iter_text())

    events = _parse_sse(body)
    token_events = [d for e, d in events if e == "token"]
    done_events = [d for e, d in events if e == "done"]
    assert len(token_events) >= 3
    assert len(done_events) == 1

    done = done_events[0]
    assert done["assistant_message_id"]
    assert done["user_message_id"]
    assert done["thread_id"]

    # Both messages persisted; active branch is [user, assistant].
    msgs = client.get(
        f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
    ).json()
    assert [m["role"] for m in msgs["messages"]] == ["user", "assistant"]
    assert msgs["active_leaf_message_id"] == done["assistant_message_id"]
    assert msgs["messages"][1]["content"] == "Per q2, pricing varies by seat."


def test_stream_mid_error_persists_user_not_assistant(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    with patch(_STREAM_PATCH_TARGET, _fake_stream_error):
        with client.stream(
            "POST",
            _stream_url(exp_id),
            json={"message": "Tell me about competition."},
            headers=_AUTH_HEADER,
        ) as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())

    events = _parse_sse(body)
    error_events = [d for e, d in events if e == "error"]
    done_events = [d for e, d in events if e == "done"]
    assert len(error_events) == 1
    assert len(done_events) == 0

    # User message persisted (active leaf points at it); NO assistant message.
    msgs = client.get(
        f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
    ).json()
    assert [m["role"] for m in msgs["messages"]] == ["user"]
    assert msgs["active_leaf_message_id"] == msgs["messages"][0]["id"]

    # LLMCall accounting written despite the failure (success=false → 0 tokens).
    assert _count_llm_calls(exp_id) >= 1


@pytest.mark.asyncio
async def test_stream_client_disconnect_persists_llmcall_no_assistant() -> None:
    """Client disconnect (CancelledError) → LLMCall written, no assistant row.

    Drives the service generator directly with its own session (patched
    sessionmaker) so the disconnect path is deterministic.
    """
    from app.db.enums import ChatRole, ChatTurnKind
    from app.db.models.chat_message import ChatMessage
    from app.db.models.chat_thread import ChatThread
    from app.db.models.experiment import Experiment
    from app.db.models.llm_call import LLMCall
    from app.db.models.user import User
    from app.services.evidence_chat_service import (
        EvidenceStreamPrep,
        stream_evidence_reply,
    )

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _seed() -> tuple[UUID, UUID, UUID]:
        async with sm() as session:
            user = User(
                firebase_uid="other-firebase-uid-stream-cancel",
                email="cancel@example.com",
                name="Cancel Tester",
            )
            session.add(user)
            await session.flush()
            exp = Experiment(user_id=user.id, raw_idea="idea", name="Cancel Exp")
            session.add(exp)
            await session.flush()
            thread = ChatThread(user_id=user.id, title="Evidence chat: Cancel")
            session.add(thread)
            await session.flush()
            exp.evidence_thread_id = thread.id
            user_msg = ChatMessage(
                thread_id=thread.id,
                role=ChatRole.USER,
                content="Question that never gets answered.",
                experiment_id=exp.id,
                turn_kind=ChatTurnKind.EVIDENCE_CHAT,
                parent_message_id=None,
            )
            session.add(user_msg)
            await session.flush()
            thread.active_leaf_message_id = user_msg.id
            await session.commit()
            return exp.id, thread.id, user_msg.id

    def _fake_stream(*, provider, model, system, user, usage, max_tokens, temperature):
        async def _gen():
            usage.provider = provider
            usage.model = model
            usage.text_parts.append("partial")
            yield "partial"
            yield "more"  # generator gets CancelledError thrown here

        return _gen()

    try:
        exp_id, thread_id, user_msg_id = await _seed()

        prep = EvidenceStreamPrep(
            experiment_id=exp_id,
            thread_id=thread_id,
            user_message_id=user_msg_id,
            user_prompt="irrelevant — llm is faked",
            provider="kimi",
            model="kimi-k2.6",
        )

        with patch(
            "app.services.evidence_chat_service.get_sessionmaker", return_value=sm
        ), patch(_STREAM_PATCH_TARGET, _fake_stream):
            agen = stream_evidence_reply(prep)
            first_frame = await agen.__anext__()
            assert "event: token" in first_frame
            with pytest.raises(asyncio.CancelledError):
                await agen.athrow(asyncio.CancelledError())

        async with sm() as session:
            assistant_count = await session.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(
                    ChatMessage.thread_id == thread_id,
                    ChatMessage.role == ChatRole.ASSISTANT,
                )
            )
            assert assistant_count == 0

            llm_count = await session.scalar(
                select(func.count())
                .select_from(LLMCall)
                .where(LLMCall.experiment_id == exp_id)
            )
            assert llm_count >= 1

            thread = await session.get(ChatThread, thread_id)
            assert thread is not None
            assert thread.active_leaf_message_id == user_msg_id
    finally:
        await engine.dispose()
