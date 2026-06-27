"""Tests for DELETE /experiments/{id}."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


@pytest.fixture
def experiment_id(client: TestClient, mock_firebase: None) -> str:
    client.post("/users/sync", json={"name": "Delete Tester"}, headers=_AUTH_HEADER)
    resp = client.post(
        "/experiments",
        json={
            "raw_idea": "A" * 50,
            "name": "Delete Me",
        },
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_delete_experiment_requires_confirm(
    client: TestClient,
    experiment_id: str,
) -> None:
    resp = client.request(
        "DELETE",
        f"/experiments/{experiment_id}",
        json={"confirmation": "delete"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_delete_experiment_success(
    client: TestClient,
    experiment_id: str,
) -> None:
    resp = client.request(
        "DELETE",
        f"/experiments/{experiment_id}",
        json={"confirmation": "CONFIRM"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["experiment_id"] == experiment_id

    get_resp = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert get_resp.status_code == 404


def test_delete_experiment_not_found_after_delete(
    client: TestClient,
    experiment_id: str,
) -> None:
    client.request(
        "DELETE",
        f"/experiments/{experiment_id}",
        json={"confirmation": "CONFIRM"},
        headers=_AUTH_HEADER,
    )
    again = client.request(
        "DELETE",
        f"/experiments/{experiment_id}",
        json={"confirmation": "CONFIRM"},
        headers=_AUTH_HEADER,
    )
    assert again.status_code == 404


def test_delete_experiment_unknown_id_returns_404(
    client: TestClient,
    mock_firebase: None,
) -> None:
    client.post("/users/sync", json={"name": "Delete Tester"}, headers=_AUTH_HEADER)
    resp = client.request(
        "DELETE",
        f"/experiments/{uuid4()}",
        json={"confirmation": "CONFIRM"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 404
