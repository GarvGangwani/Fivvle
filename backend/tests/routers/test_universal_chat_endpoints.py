"""Integration tests for universal-chat endpoints on the experiments router.

Endpoints:
- POST /experiments/{id}/chat/universal
- GET  /experiments/{id}/chat/universal/messages

Uses the real Postgres DB (TestClient + conftest fixtures). LLM is mocked.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_LLM_PATCH_TARGET = "app.services.universal_chat_service.llm_client.complete"


def _sync_user(client: TestClient) -> None:
    resp = client.post(
        "/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER
    )
    assert resp.status_code == 200


def _create_experiment(client: TestClient) -> str:
    resp = client.post(
        "/experiments",
        json={"name": "Universal Chat Test Project"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


def test_universal_chat_requires_auth(client: TestClient) -> None:
    exp_id = uuid4()
    assert (
        client.post(
            f"/experiments/{exp_id}/chat/universal",
            json={"message": "hi"},
        ).status_code
        == 401
    )
    assert (
        client.get(f"/experiments/{exp_id}/chat/universal/messages").status_code
        == 401
    )


def test_universal_chat_post_get_happy_path(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)

    with patch(_LLM_PATCH_TARGET, new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = SimpleNamespace(
            text="You're in Spark. Next up is Refine — clarify your idea."
        )
        post = client.post(
            f"/experiments/{exp_id}/chat/universal",
            json={"message": "Where should I focus?"},
            headers=_AUTH_HEADER,
        )
    assert post.status_code == 200, post.json()
    body = post.json()
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "Where should I focus?"
    assert body["assistant_message"]["role"] == "assistant"
    assert "Spark" in body["assistant_message"]["content"]
    assert body["user_message"]["turn_kind"] == "universal_chat"
    assert body["thread_id"]

    get = client.get(
        f"/experiments/{exp_id}/chat/universal/messages",
        headers=_AUTH_HEADER,
    )
    assert get.status_code == 200
    listed = get.json()
    assert listed["thread_id"] == body["thread_id"]
    assert len(listed["messages"]) == 2
    assert listed["messages"][0]["content"] == "Where should I focus?"
    assert listed["active_leaf_message_id"] == body["assistant_message"]["id"]


def test_universal_chat_get_empty_before_send(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    get = client.get(
        f"/experiments/{exp_id}/chat/universal/messages",
        headers=_AUTH_HEADER,
    )
    assert get.status_code == 200
    body = get.json()
    assert body["thread_id"] is None
    assert body["messages"] == []


def test_universal_chat_wrong_owner_404(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    missing = uuid4()
    assert (
        client.post(
            f"/experiments/{missing}/chat/universal",
            json={"message": "hi"},
            headers=_AUTH_HEADER,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/experiments/{missing}/chat/universal/messages",
            headers=_AUTH_HEADER,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/experiments/{exp_id}/chat/universal/messages",
            headers=_AUTH_HEADER,
        ).status_code
        == 200
    )


def test_universal_chat_empty_message_422(
    client: TestClient, mock_firebase: None
) -> None:
    _sync_user(client)
    exp_id = _create_experiment(client)
    resp = client.post(
        f"/experiments/{exp_id}/chat/universal",
        json={"message": "   "},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 422
