"""Integration tests for the evidence-chat regenerate endpoint.

Endpoint:
- POST /experiments/{id}/evidence-chat/messages/{assistant_message_id}/regenerate

Uses the real Postgres DB (TestClient + conftest fixtures). The LLM call is
mocked. Mirrors tests/routers/test_evidence_chat_endpoints.py.

Covered:
- 401 unauthenticated.
- 200 happy path — assistant reply replaced, no user_message in response.
- 404 wrong owner.
- 404 target message not in this experiment's evidence thread.
- 400 wrong role (target is a user message).
- 400 wrong turn_kind (assistant message that isn't evidence_chat).
- 400 no parent user message found.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import get_settings

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_LLM_PATCH_TARGET = "app.services.evidence_chat_service.llm_client.complete"


def _sync_user(client: TestClient) -> str:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_experiment(client: TestClient, name: str = "Evidence Regen Test") -> str:
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


def _seed_thread(
    experiment_id: str,
    user_id: str,
    messages: list[tuple[str, str | None]],
) -> list[str]:
    """Create an evidence thread, link it to the experiment, seed messages.

    `messages` is a list of (role, turn_kind) — turn_kind may be None. Messages
    are timestamped in list order (1s apart). Returns the created message ids.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.enums import ChatRole, ChatTurnKind
    from app.db.models.chat_message import ChatMessage
    from app.db.models.chat_thread import ChatThread
    from app.db.models.experiment import Experiment

    role_map = {"user": ChatRole.USER, "assistant": ChatRole.ASSISTANT}
    kind_map = {
        "evidence_chat": ChatTurnKind.EVIDENCE_CHAT,
        "normal_chat": ChatTurnKind.NORMAL_CHAT,
        None: None,
    }

    async def _run() -> list[str]:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                thread = ChatThread(user_id=UUID(user_id), title="Evidence chat: seeded")
                session.add(thread)
                await session.flush()
                experiment = await session.get(Experiment, UUID(experiment_id))
                assert experiment is not None
                experiment.evidence_thread_id = thread.id
                base = datetime.now(UTC)
                ids: list[str] = []
                for i, (role, kind) in enumerate(messages):
                    msg = ChatMessage(
                        thread_id=thread.id,
                        role=role_map[role],
                        content=f"seeded {role} {i}",
                        experiment_id=UUID(experiment_id),
                        turn_kind=kind_map[kind],
                        parent_message_id=None,
                        created_at=base + timedelta(seconds=i),
                    )
                    session.add(msg)
                    await session.flush()
                    ids.append(str(msg.id))
                await session.commit()
                return ids
        finally:
            await engine.dispose()

    return asyncio.get_event_loop().run_until_complete(_run())


def _mock_llm(text: str) -> Any:
    m = AsyncMock()
    m.return_value = SimpleNamespace(text=text)
    return m


def _send(client: TestClient, exp_id: str) -> dict[str, Any]:
    with patch(_LLM_PATCH_TARGET, _mock_llm("Original reply grounded in q2.")):
        resp = client.post(
            f"/experiments/{exp_id}/evidence-chat",
            json={"message": "Tell me about the competition."},
            headers=_AUTH_HEADER,
        )
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _regen_url(exp_id: str, message_id: str) -> str:
    return f"/experiments/{exp_id}/evidence-chat/messages/{message_id}/regenerate"


# ---------------------------------------------------------------------------


def test_regenerate_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(_regen_url(str(uuid4()), str(uuid4())), json={})
    assert resp.status_code == 401


def test_regenerate_happy_path_returns_200(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    sent = _send(client, exp_id)
    assistant_id = sent["assistant_message"]["id"]

    with patch(_LLM_PATCH_TARGET, _mock_llm("Fresh regenerated reply.")):
        resp = client.post(
            _regen_url(exp_id, assistant_id), json={}, headers=_AUTH_HEADER
        )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["assistant_message"]["content"] == "Fresh regenerated reply."
    assert body["assistant_message"]["turn_kind"] == "evidence_chat"
    assert body["thread_id"] == sent["thread_id"]
    assert "user_message" not in body
    # The old assistant row is gone; the new one has a different id.
    assert body["assistant_message"]["id"] != assistant_id


def test_regenerate_wrong_owner_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    assistant_id = _send(client, exp_id)["assistant_message"]["id"]

    from app.auth.dependencies import get_current_user
    from app.main import app

    other = MagicMock()
    other.id = uuid4()

    async def _fake_other() -> object:
        return other

    app.dependency_overrides[get_current_user] = _fake_other
    try:
        resp = client.post(
            _regen_url(exp_id, assistant_id), json={}, headers=_AUTH_HEADER
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 404


def test_regenerate_message_not_in_experiment_thread_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp1 = _create_experiment(client, "Exp One")
    _seed_validation_report(exp1, _raw_report_dict())
    assistant_id = _send(client, exp1)["assistant_message"]["id"]

    exp2 = _create_experiment(client, "Exp Two")
    _seed_validation_report(exp2, _raw_report_dict())
    _send(client, exp2)  # gives exp2 its own evidence thread

    # exp1's assistant id under exp2 → not in exp2's thread → 404.
    resp = client.post(
        _regen_url(exp2, assistant_id), json={}, headers=_AUTH_HEADER
    )
    assert resp.status_code == 404


def test_regenerate_wrong_role_returns_400(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    user_id = _send(client, exp_id)["user_message"]["id"]

    resp = client.post(_regen_url(exp_id, user_id), json={}, headers=_AUTH_HEADER)
    assert resp.status_code == 400


def test_regenerate_wrong_turn_kind_returns_400(
    client: TestClient, mock_firebase: None
) -> None:
    uid = _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    # Thread has a user message (parent exists) then an assistant NORMAL_CHAT.
    ids = _seed_thread(exp_id, uid, [("user", "evidence_chat"), ("assistant", "normal_chat")])

    resp = client.post(_regen_url(exp_id, ids[1]), json={}, headers=_AUTH_HEADER)
    assert resp.status_code == 400


def test_regenerate_no_parent_user_returns_400(
    client: TestClient, mock_firebase: None
) -> None:
    uid = _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    # Lone assistant evidence-chat message, no preceding user message.
    ids = _seed_thread(exp_id, uid, [("assistant", "evidence_chat")])

    resp = client.post(_regen_url(exp_id, ids[0]), json={}, headers=_AUTH_HEADER)
    assert resp.status_code == 400
