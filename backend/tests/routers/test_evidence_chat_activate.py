"""Integration tests for the evidence-chat activate endpoint.

Endpoint:
- POST /experiments/{id}/evidence-chat/messages/{message_id}/activate

Activating a message switches the active branch. The target may be an interior
node; the backend walks forward to the branch's actual leaf (latest child at
each step) and sets THAT as the active leaf, then returns the resolved leaf id.

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


def _create_experiment(client: TestClient, name: str = "Evidence Activate Test") -> str:
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


def _mock_llm(text: str) -> Any:
    from unittest.mock import AsyncMock

    m = AsyncMock()
    m.return_value = SimpleNamespace(text=text)
    return m


def _send(client: TestClient, exp_id: str, message: str = "First question.") -> dict[str, Any]:
    with patch(_LLM_PATCH_TARGET, _mock_llm("First reply grounded in q2.")):
        resp = client.post(
            f"/experiments/{exp_id}/evidence-chat",
            json={"message": message},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _edit(client: TestClient, exp_id: str, user_message_id: str) -> dict[str, Any]:
    with patch(_LLM_PATCH_TARGET, _mock_llm("Edited reply.")):
        resp = client.post(
            f"/experiments/{exp_id}/evidence-chat/messages/{user_message_id}/edit",
            json={"content": "Edited question."},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _activate_url(exp_id: str, message_id: str) -> str:
    return f"/experiments/{exp_id}/evidence-chat/messages/{message_id}/activate"


# ---------------------------------------------------------------------------


def test_activate_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(_activate_url(str(uuid4()), str(uuid4())))
    assert resp.status_code == 401


def test_activate_resolves_to_branch_leaf(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    sent = _send(client, exp_id)
    original_user_id = sent["user_message"]["id"]
    original_assistant_id = sent["assistant_message"]["id"]

    # Edit branches away; active leaf is now the edited assistant.
    edited = _edit(client, exp_id, original_user_id)
    assert (
        client.get(
            f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
        ).json()["active_leaf_message_id"]
        == edited["new_assistant_message"]["id"]
    )

    # Activate the ORIGINAL user message (an interior node) → resolves forward to
    # its branch leaf (the original assistant reply).
    resp = client.post(_activate_url(exp_id, original_user_id), headers=_AUTH_HEADER)
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["active_leaf_message_id"] == original_assistant_id

    # GET now returns the original branch.
    msgs = client.get(
        f"/experiments/{exp_id}/evidence-chat/messages", headers=_AUTH_HEADER
    ).json()
    assert msgs["active_leaf_message_id"] == original_assistant_id
    assert [m["id"] for m in msgs["messages"]] == [
        original_user_id,
        original_assistant_id,
    ]


def test_activate_wrong_owner_returns_404(
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
        resp = client.post(_activate_url(exp_id, user_msg_id), headers=_AUTH_HEADER)
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 404


def test_activate_message_not_in_thread_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp1 = _create_experiment(client, "Exp One")
    _seed_validation_report(exp1, _raw_report_dict())
    msg_id = _send(client, exp1)["assistant_message"]["id"]

    exp2 = _create_experiment(client, "Exp Two")
    _seed_validation_report(exp2, _raw_report_dict())
    _send(client, exp2)

    resp = client.post(_activate_url(exp2, msg_id), headers=_AUTH_HEADER)
    assert resp.status_code == 404
