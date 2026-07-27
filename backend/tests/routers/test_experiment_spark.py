"""Integration tests for Spark version save / list endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _sync_user(client: TestClient) -> None:
    resp = client.post(
        "/users/sync",
        json={"name": "Spark Version Tester"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200


def test_spark_save_increments_and_short_circuits(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    create = client.post(
        "/experiments",
        headers=_AUTH_HEADER,
        json={"name": "Spark Version Test"},
    )
    assert create.status_code == 201, create.text
    experiment_id = create.json()["id"]

    first = client.post(
        f"/experiments/{experiment_id}/spark/save",
        headers=_AUTH_HEADER,
        json={"raw_idea": "First saved idea for versioning"},
    )
    assert first.status_code == 200, first.text
    body1 = first.json()
    assert body1["version_number"] == 1
    assert body1["raw_idea"] == "First saved idea for versioning"

    duplicate = client.post(
        f"/experiments/{experiment_id}/spark/save",
        headers=_AUTH_HEADER,
        json={"raw_idea": "First saved idea for versioning"},
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["id"] == body1["id"]
    assert duplicate.json()["version_number"] == 1

    second = client.post(
        f"/experiments/{experiment_id}/spark/save",
        headers=_AUTH_HEADER,
        json={"raw_idea": "Second saved idea for versioning"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["version_number"] == 2

    detail = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["current_spark_version"] == 2
    assert data["raw_idea"] == "Second saved idea for versioning"
    assert data["refine_is_stale"] is False
    assert data["evidence_is_stale"] is False

    versions = client.get(
        f"/experiments/{experiment_id}/spark/versions",
        headers=_AUTH_HEADER,
    )
    assert versions.status_code == 200, versions.text
    assert [v["version_number"] for v in versions.json()] == [2, 1]


def test_launch_stale_reasons_include_edited_doc_after_patch(
    client: TestClient,
    mock_firebase: None,
) -> None:
    """PATCH edited_doc after landing generation marks launch stale via edited_doc."""
    import asyncio
    from datetime import UTC, datetime
    from uuid import UUID

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
    from app.db.models.experiment import Experiment
    from app.db.models.landing_page import LandingPage
    from app.db.models.validation_report import ValidationReport
    from tests.routers.test_validation_report_edited_doc import _raw_report_dict

    _sync_user(client)
    create = client.post(
        "/experiments",
        headers=_AUTH_HEADER,
        json={"name": "Launch Edited Doc Stale"},
    )
    assert create.status_code == 201, create.text
    experiment_id = create.json()["id"]

    async def _seed() -> None:
        engine = create_async_engine(
            get_settings().database_url, pool_size=1, max_overflow=0
        )
        sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            async with sm() as session:
                exp = (
                    await session.execute(
                        select(Experiment).where(Experiment.id == UUID(experiment_id))
                    )
                ).scalar_one()
                exp.status = ExperimentStatus.LANDING_LIVE
                session.add(
                    ValidationReport(
                        experiment_id=exp.id,
                        raw_report=_raw_report_dict(),
                        edited_doc=None,
                        edited_doc_version=0,
                    )
                )
                session.add(
                    LandingPage(
                        experiment_id=exp.id,
                        template_id="minimal",
                        palette_id="default",
                        font_pair_id="sans",
                        density=LandingDensity.ROOMY,
                        headline="H",
                        problem_desc="P",
                        solution_desc="S",
                        cta_text="Join",
                        cta_type=LandingCtaType.WAITLIST,
                        slug=f"edv-{experiment_id.replace('-', '')[:12]}",
                        live_at=datetime.now(UTC),
                        edited_doc_version=0,
                        copy_json={},
                        page_json={},
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_seed())

    before = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert before.status_code == 200, before.text
    assert before.json()["launch_is_stale"] is False
    assert "edited_doc" not in before.json().get("launch_stale_reasons", [])

    patch = client.patch(
        f"/experiments/{experiment_id}/validation-report/edited-doc",
        headers=_AUTH_HEADER,
        json={
            "doc": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Founder edit"}],
                    }
                ],
            },
            "base_version": 0,
        },
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["version"] == 1

    after = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert after.status_code == 200, after.text
    body = after.json()
    assert body["current_edited_doc_version"] == 1
    assert body["launch_edited_doc_version"] == 0
    assert body["launch_is_stale"] is True
    assert "edited_doc" in body["launch_stale_reasons"]
