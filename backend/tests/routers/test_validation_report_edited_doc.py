"""Integration tests for the editable-doc endpoints on the experiments router.

Endpoints:
- GET  /experiments/{id}/validation-report/edited-doc
- PATCH /experiments/{id}/validation-report/edited-doc

Uses the real Postgres DB (TestClient + conftest fixtures). Mocks only
refine_idea to create an experiment, then seeds a ValidationReport row directly.

Covered:
- 401 unauthenticated (both verbs).
- GET returns source="generated", version 0 for a never-edited report.
- PATCH first edit (base_version=0) → 200, version 1, source="persisted".
- PATCH stale base_version → 409 with {message, current_version}.
- Wrong owner → 404 (does not reveal existence).
- Staleness flag flips when generated_at advances past edited_at.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import get_settings

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _create_experiment(client: TestClient) -> str:
    """Create a Spark experiment (name-only) and return its UUID string.

    The edited-doc endpoints don't gate on status, so a plain Spark plus a
    directly-seeded ValidationReport row is sufficient — no refinement needed.
    """
    resp = client.post(
        "/experiments", json={"name": "Edited Doc Test Project"}, headers=_AUTH_HEADER
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def _raw_report_dict() -> dict[str, Any]:
    """A valid ValidationReport payload serialized to JSON (JSONB-ready)."""
    from app.schemas.validation_report import (
        Citation,
        CompetitorMention,
        Finding,
        QuestionFindings,
        SectionScore,
        ValidationReport,
    )

    now = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)

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
                pros=["847 G2 reviews signal demand"],
                cons=["No TAM figure available"],
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


def _advance_generated_at(experiment_id: str, when: datetime) -> None:
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.models.validation_report import ValidationReport as ValidationReportRow

    async def _run() -> None:
        engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                await session.execute(
                    update(ValidationReportRow)
                    .where(ValidationReportRow.experiment_id == UUID(experiment_id))
                    .values(generated_at=when)
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_run())


_EDITED_DOC = {"type": "doc", "content": [{"type": "paragraph", "content": []}]}


# ---------------------------------------------------------------------------
# Auth-guard smoke tests
# ---------------------------------------------------------------------------


def test_get_edited_doc_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.get(f"/experiments/{uuid4()}/validation-report/edited-doc")
    assert resp.status_code == 401


def test_patch_edited_doc_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.patch(
        f"/experiments/{uuid4()}/validation-report/edited-doc",
        json={"doc": _EDITED_DOC, "base_version": 0},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET — generated source
# ---------------------------------------------------------------------------


def test_get_edited_doc_returns_generated_render(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    resp = client.get(
        f"/experiments/{exp_id}/validation-report/edited-doc", headers=_AUTH_HEADER
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["source"] == "generated"
    assert body["version"] == 0
    assert body["edited_doc_behind_regeneration"] is False
    assert body["doc"]["type"] == "doc"
    assert len(body["doc"]["content"]) > 0


def test_get_edited_doc_404_when_no_report(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    resp = client.get(
        f"/experiments/{exp_id}/validation-report/edited-doc", headers=_AUTH_HEADER
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH — first edit + CAS conflict
# ---------------------------------------------------------------------------


def test_patch_first_edit_persists_and_bumps_version(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    resp = client.patch(
        f"/experiments/{exp_id}/validation-report/edited-doc",
        json={"doc": _EDITED_DOC, "base_version": 0},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["source"] == "persisted"
    assert body["version"] == 1
    assert body["doc"] == _EDITED_DOC

    # A subsequent GET reflects the persisted overlay.
    get_resp = client.get(
        f"/experiments/{exp_id}/validation-report/edited-doc", headers=_AUTH_HEADER
    )
    assert get_resp.json()["source"] == "persisted"
    assert get_resp.json()["version"] == 1


def test_patch_stale_base_version_returns_409(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    # First edit → version 1.
    first = client.patch(
        f"/experiments/{exp_id}/validation-report/edited-doc",
        json={"doc": _EDITED_DOC, "base_version": 0},
        headers=_AUTH_HEADER,
    )
    assert first.json()["version"] == 1

    # Second edit with the now-stale base_version=0 → 409.
    conflict = client.patch(
        f"/experiments/{exp_id}/validation-report/edited-doc",
        json={"doc": _EDITED_DOC, "base_version": 0},
        headers=_AUTH_HEADER,
    )
    assert conflict.status_code == 409
    detail = conflict.json()["detail"]
    assert detail["message"] == "edited_doc_version conflict"
    assert detail["current_version"] == 1


def test_patch_rejects_extra_fields(client: TestClient, mock_firebase: None) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())
    resp = client.patch(
        f"/experiments/{exp_id}/validation-report/edited-doc",
        json={"doc": _EDITED_DOC, "base_version": 0, "unexpected": True},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


def test_stale_flag_set_when_regeneration_after_edit(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    _seed_validation_report(exp_id, _raw_report_dict())

    # Persist an edit (edited_at = now).
    client.patch(
        f"/experiments/{exp_id}/validation-report/edited-doc",
        json={"doc": _EDITED_DOC, "base_version": 0},
        headers=_AUTH_HEADER,
    )

    # Simulate a regeneration that happens AFTER the edit.
    _advance_generated_at(exp_id, datetime.now(UTC) + timedelta(days=1))

    resp = client.get(
        f"/experiments/{exp_id}/validation-report/edited-doc", headers=_AUTH_HEADER
    )
    assert resp.json()["edited_doc_behind_regeneration"] is True


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


def test_get_edited_doc_wrong_owner_returns_404(
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
            f"/experiments/{exp_id}/validation-report/edited-doc", headers=_AUTH_HEADER
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
