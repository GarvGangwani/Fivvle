"""Integration tests for POST /experiments/{id}/capture-idea."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Capture Tester"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _create_experiment(client: TestClient, name: str = "Capture Endpoint") -> dict:
    resp = client.post("/experiments", json={"name": name}, headers=_AUTH_HEADER)
    assert resp.status_code == 201, resp.json()
    return resp.json()


def test_capture_idea_writes_and_second_returns_409(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    created = _create_experiment(client)
    experiment_id = created["id"]
    raw_idea = created["raw_idea"]

    with patch(
        "app.services.idea_capture_service.classify_idea_theme",
        AsyncMock(return_value="violet"),
    ):
        first = client.post(
            f"/experiments/{experiment_id}/capture-idea",
            headers=_AUTH_HEADER,
            json={
                "idea_text": "First capture of the original idea text.",
                "attachment_ids": [],
            },
        )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["original_idea"] == "First capture of the original idea text."
    assert body["idea_theme"] == "violet"
    assert body["original_idea_captured_at"] is not None
    assert body["frozen_attachments"] == []

    second = client.post(
        f"/experiments/{experiment_id}/capture-idea",
        headers=_AUTH_HEADER,
        json={"idea_text": "Second attempt", "attachment_ids": []},
    )
    assert second.status_code == 409
    assert "already captured" in second.json()["detail"].lower()

    detail = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert detail.status_code == 200
    assert detail.json()["raw_idea"] == raw_idea


def test_capture_idea_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.post(
        f"/experiments/00000000-0000-0000-0000-000000000001/capture-idea",
        json={"idea_text": "Nope", "attachment_ids": []},
    )
    assert resp.status_code == 401
