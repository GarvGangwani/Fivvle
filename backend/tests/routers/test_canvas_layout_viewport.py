"""Tests for canvas layout viewport persistence."""

from __future__ import annotations

from fastapi.testclient import TestClient

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}

_DEFAULT_POSITIONS = {
    "spark": {"x": -250, "y": -430},
    "refine": {"x": 250, "y": -430},
    "evidence": {"x": 500, "y": 0},
    "launch": {"x": 250, "y": 430},
    "signal": {"x": -250, "y": 430},
    "resources": {"x": -500, "y": 0},
}


def _sync_user(client: TestClient) -> None:
    resp = client.post(
        "/users/sync",
        json={"name": "Canvas Viewport Tester"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200


def _create_experiment(client: TestClient) -> str:
    create = client.post(
        "/experiments",
        headers=_AUTH_HEADER,
        json={"name": "Canvas Persist Test"},
    )
    assert create.status_code == 201, create.text
    return create.json()["id"]


def test_canvas_layout_viewport_roundtrip(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_experiment(client)

    empty = client.get(
        f"/experiments/{experiment_id}/canvas-layout",
        headers=_AUTH_HEADER,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["viewport_x"] is None
    assert empty.json()["viewport_zoom"] is None

    put = client.put(
        f"/experiments/{experiment_id}/canvas-layout",
        headers=_AUTH_HEADER,
        json={
            "node_positions": _DEFAULT_POSITIONS,
            "viewport_x": 120.5,
            "viewport_y": -40.25,
            "viewport_zoom": 1.1,
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["viewport_x"] == 120.5
    assert body["viewport_y"] == -40.25
    assert body["viewport_zoom"] == 1.1

    got = client.get(
        f"/experiments/{experiment_id}/canvas-layout",
        headers=_AUTH_HEADER,
    )
    assert got.status_code == 200, got.text
    assert got.json()["viewport_x"] == 120.5
    assert got.json()["viewport_zoom"] == 1.1


def test_canvas_layout_invalid_zoom_returns_422(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_experiment(client)

    bad = client.put(
        f"/experiments/{experiment_id}/canvas-layout",
        headers=_AUTH_HEADER,
        json={
            "node_positions": _DEFAULT_POSITIONS,
            "viewport_x": 0,
            "viewport_y": 0,
            "viewport_zoom": 5.0,
        },
    )
    assert bad.status_code == 422


def test_canvas_layout_null_viewport_clears_saved(
    client: TestClient,
    mock_firebase: None,
) -> None:
    _sync_user(client)
    experiment_id = _create_experiment(client)

    client.put(
        f"/experiments/{experiment_id}/canvas-layout",
        headers=_AUTH_HEADER,
        json={
            "node_positions": _DEFAULT_POSITIONS,
            "viewport_x": 10,
            "viewport_y": 20,
            "viewport_zoom": 0.9,
        },
    )

    cleared = client.put(
        f"/experiments/{experiment_id}/canvas-layout",
        headers=_AUTH_HEADER,
        json={
            "node_positions": _DEFAULT_POSITIONS,
            "viewport_x": None,
            "viewport_y": None,
            "viewport_zoom": None,
        },
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["viewport_x"] is None
    assert cleared.json()["viewport_zoom"] is None
