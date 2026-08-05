"""Integration tests for PATCH /experiments/{id}/theme."""

from __future__ import annotations

from fastapi.testclient import TestClient

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


def _sync_user(client: TestClient) -> None:
    resp = client.post("/users/sync", json={"name": "Theme Tester"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


def _create_experiment(client: TestClient, name: str = "Theme Endpoint") -> dict:
    resp = client.post("/experiments", json={"name": name}, headers=_AUTH_HEADER)
    assert resp.status_code == 201, resp.json()
    return resp.json()


def test_set_theme_persists_and_reverts(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_experiment(client)["id"]

    detail = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert detail.status_code == 200
    assert detail.json()["theme_palette"] is None

    applied = client.patch(
        f"/experiments/{experiment_id}/theme",
        headers=_AUTH_HEADER,
        json={"palette_name": "emerald"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["theme_palette"] == "emerald"

    reread = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert reread.json()["theme_palette"] == "emerald"

    reverted = client.patch(
        f"/experiments/{experiment_id}/theme",
        headers=_AUTH_HEADER,
        json={"palette_name": None},
    )
    assert reverted.status_code == 200
    assert reverted.json()["theme_palette"] is None


def test_set_theme_rejects_palette_outside_curated_set(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_experiment(client, name="Theme Reject")["id"]

    resp = client.patch(
        f"/experiments/{experiment_id}/theme",
        headers=_AUTH_HEADER,
        json={"palette_name": "chartreuse"},
    )
    assert resp.status_code == 422

    detail = client.get(f"/experiments/{experiment_id}", headers=_AUTH_HEADER)
    assert detail.json()["theme_palette"] is None


def test_set_theme_unknown_experiment_returns_404(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    resp = client.patch(
        "/experiments/00000000-0000-0000-0000-000000000001/theme",
        headers=_AUTH_HEADER,
        json={"palette_name": "sky"},
    )
    assert resp.status_code == 404


def test_set_theme_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.patch(
        "/experiments/00000000-0000-0000-0000-000000000001/theme",
        json={"palette_name": "sky"},
    )
    assert resp.status_code == 401
