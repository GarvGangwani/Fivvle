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
