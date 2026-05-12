"""Integration tests for POST /experiments and POST /experiments/{id}/refine.

These tests use a real Postgres DB (via the TestClient + conftest fixtures) and mock
only refine_idea — exercising the full service layer, state machine transitions,
schema validation, auth, rate-limit middleware, and error-to-HTTP mapping.

Mock target (same level as service tests):
    patch("app.services.experiment_service.refine_idea", ...)

Test DB cleanup relies on the autouse _cleanup_test_users fixture in conftest.py:
    deletes users with FAKE_FIREBASE_UID → CASCADE removes their experiments.

For ownership tests a dependency override is used so no second DB user is needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FAKE_EMAIL, FAKE_FIREBASE_UID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}
_VALID_RAW_IDEA = "A slack bot that answers HR policy questions so ops managers don't have to."


def _make_valid_refined_idea_dict() -> dict:
    return {
        "refined_one_liner": "A Slack bot that answers HR policy questions instantly.",
        "target_audience": (
            "Operations managers at 50-500 person companies who answer "
            "20-30 repeated policy questions per week in Slack."
        ),
        "value_proposition": (
            "Eliminates 30-minute weekly Slack interrupts so ops managers "
            "can focus on real operations work instead of being a walking FAQ."
        ),
        "risks": [
            "Is the market large enough to support a venture-scale business?",
            "Do existing enterprise tools already solve this for most buyers?",
            "Can unit economics work at target price point given CAC?",
        ],
        "headline": "Stop answering the same policy questions every week.",
        "subheadline": "An AI trained on your handbook handles every 'what's the policy on X?' question.",
        "cta_text": "Join the waitlist",
    }


def _fake_refined_idea() -> object:
    """Return a RefinedIdea instance for mocking refine_idea."""
    from app.schemas.refinement import RefinedIdea

    return RefinedIdea(**_make_valid_refined_idea_dict())


def _sync_user(client: TestClient) -> None:
    """Create the test user via /users/sync (idempotent)."""
    resp = client.post("/users/sync", json={"name": "Test Founder"}, headers=_AUTH_HEADER)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /experiments — authentication
# ---------------------------------------------------------------------------


def test_create_experiment_unauthenticated(client: TestClient) -> None:
    """No Authorization header → 401."""
    response = client.post("/experiments", json={"raw_idea": _VALID_RAW_IDEA})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /experiments — happy path
# ---------------------------------------------------------------------------


def test_create_experiment_happy_path(client: TestClient, mock_firebase: None) -> None:
    """Authenticated request with valid idea → 201 with REFINED experiment."""
    _sync_user(client)

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=_fake_refined_idea()),
    ):
        response = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "REFINED"
    assert body["refinement_count"] == 1
    assert body["refined_idea"] is not None
    assert body["refined_idea"]["refined_one_liner"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert body["slug"] is None  # slug assigned only at publish time


# ---------------------------------------------------------------------------
# POST /experiments — request validation
# ---------------------------------------------------------------------------


def test_create_experiment_raw_idea_too_short(client: TestClient, mock_firebase: None) -> None:
    """raw_idea below Pydantic min_length (50) → 422 from FastAPI schema validation."""
    _sync_user(client)
    response = client.post(
        "/experiments",
        json={"raw_idea": "A" * 49},
        headers=_AUTH_HEADER,
    )
    # FastAPI returns 422 for Pydantic field validation failures (min_length constraint).
    assert response.status_code == 422


def test_create_experiment_whitespace_only_idea_returns_400(
    client: TestClient, mock_firebase: None
) -> None:
    """50 spaces passes Pydantic min_length but is rejected by service strip-check → 400."""
    _sync_user(client)
    response = client.post(
        "/experiments",
        json={"raw_idea": " " * 50},
        headers=_AUTH_HEADER,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /experiments — LLM failure
# ---------------------------------------------------------------------------


def test_create_experiment_llm_failure_returns_502(
    client: TestClient, mock_firebase: None
) -> None:
    """LLM exception → 502; response body does NOT contain the internal error detail."""
    _sync_user(client)

    class _FakeLLMError(RuntimeError):
        pass

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(side_effect=_FakeLLMError("provider is down, secret_key=abc123")),
    ):
        response = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )

    assert response.status_code == 502
    body = response.json()
    # Internal details must NOT leak to the client (AGENTS.md "Error handling").
    assert "provider is down" not in str(body)
    assert "secret_key" not in str(body)
    assert body["detail"] == "Refinement failed, please try again"


# ---------------------------------------------------------------------------
# POST /experiments/{id}/refine — authentication
# ---------------------------------------------------------------------------


def test_refine_experiment_unauthenticated(client: TestClient) -> None:
    """No Authorization header → 401."""
    fake_id = str(uuid4())
    response = client.post(f"/experiments/{fake_id}/refine", json={})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /experiments/{id}/refine — not found
# ---------------------------------------------------------------------------


def test_refine_nonexistent_experiment_returns_404(
    client: TestClient, mock_firebase: None
) -> None:
    """Non-existent experiment_id → 404."""
    _sync_user(client)
    fake_id = str(uuid4())
    response = client.post(
        f"/experiments/{fake_id}/refine",
        json={},
        headers=_AUTH_HEADER,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /experiments/{id}/refine — ownership
# ---------------------------------------------------------------------------


def test_refine_wrong_owner_returns_404(client: TestClient, mock_firebase: None) -> None:
    """Another user's experiment_id → 404 (not 403 — don't reveal existence).

    Creates an experiment as the test user, then overrides get_current_user to
    return a different user with a distinct UUID, and verifies the refine endpoint
    returns 404 rather than 403 (per AGENTS.md spirit).
    """
    _sync_user(client)

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=_fake_refined_idea()),
    ):
        create_resp = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )
    assert create_resp.status_code == 201
    experiment_id = create_resp.json()["id"]

    # Override get_current_user to return a different user (different UUID, no DB row needed).
    from app.auth.dependencies import get_current_user
    from app.main import app

    other_user = MagicMock()
    other_user.id = uuid4()  # different from the experiment's user_id

    async def _fake_other_user() -> object:
        return other_user

    app.dependency_overrides[get_current_user] = _fake_other_user
    try:
        response = client.post(
            f"/experiments/{experiment_id}/refine",
            json={},
            headers=_AUTH_HEADER,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /experiments/{id}/refine — happy path
# ---------------------------------------------------------------------------


def test_refine_experiment_happy_path(client: TestClient, mock_firebase: None) -> None:
    """Authenticated owner refines → 200 with updated refinement_count."""
    _sync_user(client)

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=_fake_refined_idea()),
    ):
        # Create experiment
        create_resp = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )
        assert create_resp.status_code == 201
        experiment_id = create_resp.json()["id"]

        # Regenerate
        refine_resp = client.post(
            f"/experiments/{experiment_id}/refine",
            json={"feedback": "Make the target audience more specific."},
            headers=_AUTH_HEADER,
        )

    assert refine_resp.status_code == 200
    body = refine_resp.json()
    assert body["status"] == "REFINED"
    assert body["refinement_count"] == 2
    assert body["id"] == experiment_id


# ---------------------------------------------------------------------------
# POST /experiments/{id}/refine — regeneration limit
# ---------------------------------------------------------------------------


def test_refine_experiment_at_limit_returns_409(
    client: TestClient, mock_firebase: None
) -> None:
    """After 5 regenerations, the 6th attempt returns 409."""
    _sync_user(client)

    refined = _fake_refined_idea()

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=refined),
    ):
        # Create initial experiment (refinement_count=1)
        create_resp = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )
        assert create_resp.status_code == 201
        experiment_id = create_resp.json()["id"]

        # Regenerate 4 more times to reach the cap (count goes 1→2→3→4→5)
        for _ in range(4):
            r = client.post(
                f"/experiments/{experiment_id}/refine",
                json={},
                headers=_AUTH_HEADER,
            )
            assert r.status_code == 200

    # 6th attempt (count already at 5) must be rejected
    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=refined),
    ):
        response = client.post(
            f"/experiments/{experiment_id}/refine",
            json={},
            headers=_AUTH_HEADER,
        )

    assert response.status_code == 409
    assert "limit" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /experiments/{id}/refine — LLM failure
# ---------------------------------------------------------------------------


def test_refine_experiment_llm_failure_returns_502(
    client: TestClient, mock_firebase: None
) -> None:
    """LLM exception during regeneration → 502; no internal details in body."""
    _sync_user(client)

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(return_value=_fake_refined_idea()),
    ):
        create_resp = client.post(
            "/experiments",
            json={"raw_idea": _VALID_RAW_IDEA},
            headers=_AUTH_HEADER,
        )
    assert create_resp.status_code == 201
    experiment_id = create_resp.json()["id"]

    class _FakeLLMError(RuntimeError):
        pass

    with patch(
        "app.services.experiment_service.refine_idea",
        AsyncMock(side_effect=_FakeLLMError("anthropic_api_key=secret_value")),
    ):
        response = client.post(
            f"/experiments/{experiment_id}/refine",
            json={},
            headers=_AUTH_HEADER,
        )

    assert response.status_code == 502
    body = response.json()
    assert "anthropic_api_key" not in str(body)
    assert body["detail"] == "Refinement failed, please try again"
