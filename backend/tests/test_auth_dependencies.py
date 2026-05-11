"""Tests for the get_current_user FastAPI dependency.

These tests exercise the dependency through the /users/sync endpoint
(the only authenticated endpoint in this build step). We don't need real
Firebase tokens because mock_firebase patches the verification layer.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

from tests.conftest import FAKE_FIREBASE_UID


def test_missing_authorization_header_returns_401(client: TestClient, mock_firebase: None) -> None:
    response = client.post("/users/sync", json={"name": "Test"})
    assert response.status_code == 401


def test_malformed_authorization_header_returns_401(client: TestClient, mock_firebase: None) -> None:
    response = client.post(
        "/users/sync",
        json={"name": "Test"},
        headers={"Authorization": "NotBearer something"},
    )
    assert response.status_code == 401


def test_invalid_token_returns_401(client: TestClient) -> None:
    with patch(
        "app.routers.users.verify_id_token",
        side_effect=firebase_auth.InvalidIdTokenError("bad token"),
    ):
        response = client.post(
            "/users/sync",
            json={"name": "Test"},
            headers={"Authorization": "Bearer faketoken"},
        )
        assert response.status_code == 401


def test_expired_token_returns_401(client: TestClient) -> None:
    with patch(
        "app.routers.users.verify_id_token",
        side_effect=firebase_auth.ExpiredIdTokenError("expired", cause=None),
    ):
        response = client.post(
            "/users/sync",
            json={"name": "Test"},
            headers={"Authorization": "Bearer expiredtoken"},
        )
        assert response.status_code == 401
