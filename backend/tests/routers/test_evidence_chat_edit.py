"""Integration tests for the evidence-chat edit endpoint.

Endpoint:
- POST /experiments/{id}/evidence-chat/messages/{user_message_id}/edit

Editing a user message branches: a new user message is created as a SIBLING of
the original (same parent), re-answered, and the active leaf moves to the new
reply. The original message and its subtree are preserved.

Uses the real Postgres DB (TestClient + conftest fixtures); the LLM is mocked.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import get_settings

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_LLM_PATCH_TARGET = "app.services.evidence_chat_service.llm_client.complete"


def _sync_user(client: TestClient) -> str:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_experiment(client: TestClient, name: str = "Evidence Edit Test") -> str:
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


def _message_exists(message_id: str) -> bool:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.models.chat_message import ChatMessage

    async def _run() -> bool:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                result = await session.execute(
                    select(ChatMessage).where(ChatMessage.id == UUID(message_id))
                )
                return result.scalar_one_or_none() is not None
        finally:
            await engine.dispose()

    return asyncio.get_event_loop().run_until_complete(_run())


def _mock_llm(text: str) -> Any:
    from unittest.mock import AsyncMock

    m = AsyncMock()
    m.return_value = SimpleNamespace(text=text)
    return m


def _send(client: TestClient, exp_id: str, message: str = "Original question.") -> dict[str, Any]:
    with patch(_LLM_PATCH_TARGET, _mock_llm("Original reply grounded in q2.")):
        resp = client.post(
            f"/experiments/{exp_id}/evidence-chat",
            json={"message": message},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _edit_url(exp_id: str, message_id: str) -> str:
    return f"/experiments/{exp_id}/evidence-chat/messages/{message_id}/edit"


# ---------------------------------------------------------------------------


def test_edit_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(_edit_url(str(uuid4()), str(uuid4())), json={"content": "x"})
    assert resp.status_code == 401


def test_edit_creates_sibling_original_preserved(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    sent = _send(client, exp_id)
    original_user_id = sent["user_message"]["id"]
    original_assistant_id = sent["assistant_message"]["id"]

    with patch(_LLM_PATCH_TARGET, _mock_llm("Edited reply about pricing.")):
        resp = client.post(
            _edit_url(exp_id, original_user_id),
            json={"content": "Edited question about pricing."},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.json()
    body = resp.json()

    new_user_id = body["new_user_message"]["id"]
    new_assistant_id = body["new_assistant_message"]["id"]
    assert body["new_user_message"]["content"] == "Edited question about pricing."
    assert body["new_assistant_message"]["content"] == "Edited reply about pricing."
    assert new_user_id != original_user_id
    assert body["active_leaf_message_id"] == new_assistant_id
    assert body["sibling_info"][new_user_id]["sibling_count"] == 2

    # Original user message AND its assistant reply still exist in the DB.
    assert _message_exists(original_user_id) is True
    assert _message_exists(original_assistant_id) is True

    # Active branch is the edited path.
    msgs = client.get(
        f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
    ).json()
    assert [m["id"] for m in msgs["messages"]] == [new_user_id, new_assistant_id]
    assert msgs["active_leaf_message_id"] == new_assistant_id


def test_edit_wrong_role_returns_400(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    assistant_id = _send(client, exp_id)["assistant_message"]["id"]

    # Editing an assistant message is not allowed.
    resp = client.post(
        _edit_url(exp_id, assistant_id),
        json={"content": "nope"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_edit_wrong_owner_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    user_msg_id = _send(client, exp_id)["user_message"]["id"]

    from app.auth.dependencies import get_current_user
    from app.main import app

    other = SimpleNamespace(id=uuid4())

    async def _fake_other() -> object:
        return other

    app.dependency_overrides[get_current_user] = _fake_other
    try:
        resp = client.post(
            _edit_url(exp_id, user_msg_id),
            json={"content": "hijack"},
            headers=_AUTH_HEADER,
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 404


def test_edit_empty_content_returns_422(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    user_msg_id = _send(client, exp_id)["user_message"]["id"]

    resp = client.post(
        _edit_url(exp_id, user_msg_id),
        json={"content": "   "},
        headers=_AUTH_HEADER,
    )
    # Pydantic min_length=1 passes (3 spaces), service sanitizes to empty → 422.
    assert resp.status_code == 422
