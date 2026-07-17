"""Integration tests for the evidence-chat endpoints on the experiments router.

Endpoints:
- POST /experiments/{id}/evidence-chat
- GET  /experiments/{id}/evidence-chat/messages

Uses the real Postgres DB (TestClient + conftest fixtures). The LLM call is
mocked (no live provider traffic). Mirrors tests/routers/test_validation_report_edited_doc.py.

Covered:
- 401 unauthenticated (both verbs).
- POST 200 send → persisted user + assistant messages + thread_id.
- GET 200 empty history before any message.
- GET 200 returns messages after a send.
- Wrong owner → 404 (both verbs).
- Invalid selection_question_id → 422.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import get_settings

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_LLM_PATCH_TARGET = "app.services.evidence_chat_service.llm_client.complete"


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _create_experiment(client: TestClient) -> str:
    resp = client.post(
        "/experiments", json={"name": "Evidence Chat Test Project"}, headers=_AUTH_HEADER
    )
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
        risks_assessment=(
            "Competitor risk confirmed by q2; staleness risk confirmed by q1; "
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
            )
        ],
        overall_score=62,
    )
    return report.model_dump(mode="json")


def _seed_validation_report(experiment_id: str, raw_report: dict[str, Any]) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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


def _mock_llm(text: str) -> Any:
    m = AsyncMock()
    m.return_value = SimpleNamespace(text=text)
    return m


# ---------------------------------------------------------------------------
# Auth-guard smoke tests
# ---------------------------------------------------------------------------


def test_send_evidence_chat_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(
        f"/experiments/{uuid4()}/evidence-chat", json={"message": "hi"}
    )
    assert resp.status_code == 401


def test_get_evidence_chat_messages_unauthenticated_returns_401(
    client: TestClient,
) -> None:
    resp = client.get(f"/experiments/{uuid4()}/evidence-chat/messages")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST — send
# ---------------------------------------------------------------------------


def test_send_evidence_chat_returns_200(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    with patch(_LLM_PATCH_TARGET, _mock_llm("Assistant reply grounded in q2.")):
        resp = client.post(
            f"/experiments/{exp_id}/evidence-chat",
            json={"message": "Tell me about the competition."},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["user_message"]["content"] == "Tell me about the competition."
    assert body["user_message"]["turn_kind"] == "evidence_chat"
    assert body["assistant_message"]["content"] == "Assistant reply grounded in q2."
    assert body["assistant_message"]["turn_kind"] == "evidence_chat"
    assert body["thread_id"]


def test_send_evidence_chat_invalid_selection_question_id_returns_422(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    resp = client.post(
        f"/experiments/{exp_id}/evidence-chat",
        json={"message": "hi", "selection_question_id": "q9"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 422


def test_send_evidence_chat_wrong_owner_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    from app.auth.dependencies import get_current_user
    from app.main import app

    other_user = MagicMock()
    other_user.id = uuid4()

    async def _fake_other_user() -> object:
        return other_user

    app.dependency_overrides[get_current_user] = _fake_other_user
    try:
        resp = client.post(
            f"/experiments/{exp_id}/evidence-chat",
            json={"message": "hi"},
            headers=_AUTH_HEADER,
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET — messages
# ---------------------------------------------------------------------------


def test_get_evidence_chat_messages_empty(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    resp = client.get(
        f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["thread_id"] is None
    assert body["experiment_id"] == exp_id
    assert body["messages"] == []


def test_get_evidence_chat_messages_after_send(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    with patch(_LLM_PATCH_TARGET, _mock_llm("Grounded reply.")):
        send = client.post(
            f"/experiments/{exp_id}/evidence-chat",
            json={"message": "First question?"},
            headers=_AUTH_HEADER,
        )
    assert send.status_code == 200, send.json()

    resp = client.get(
        f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["thread_id"] == send.json()["thread_id"]
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"


def test_get_evidence_chat_messages_wrong_owner_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    from app.auth.dependencies import get_current_user
    from app.main import app

    other_user = MagicMock()
    other_user.id = uuid4()

    async def _fake_other_user() -> object:
        return other_user

    app.dependency_overrides[get_current_user] = _fake_other_user
    try:
        resp = client.get(
            f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
