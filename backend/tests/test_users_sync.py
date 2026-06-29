"""Tests for POST /users/sync."""

from fastapi.testclient import TestClient

from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID


def test_sync_creates_new_user(client: TestClient, mock_firebase: None) -> None:
    response = client.post(
        "/users/sync",
        json={"name": "Test Founder"},
        headers={"Authorization": "Bearer faketoken"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == FAKE_EMAIL
    assert body["name"] == "Test Founder"
    assert "id" in body
    assert "created_at" in body
    assert body["is_admin"] is True
    assert "firebase_uid" not in body


def test_sync_is_idempotent(client: TestClient, mock_firebase: None) -> None:
    response1 = client.post(
        "/users/sync",
        json={"name": "First Name"},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response1.status_code == 200
    first_id = response1.json()["id"]

    response2 = client.post(
        "/users/sync",
        json={"name": "Different Name — should not update"},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response2.status_code == 200
    second_id = response2.json()["id"]

    assert first_id == second_id


def test_sync_rejects_extra_fields(client: TestClient, mock_firebase: None) -> None:
    response = client.post(
        "/users/sync",
        json={"name": "Test", "is_admin": True},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 422


def test_sync_allows_null_name(client: TestClient, mock_firebase: None) -> None:
    response = client.post(
        "/users/sync",
        json={"name": None},
        headers={"Authorization": "Bearer faketoken"},
    )
    assert response.status_code == 200
    assert response.json()["name"] is None
