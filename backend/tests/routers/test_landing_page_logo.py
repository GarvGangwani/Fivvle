"""Tests for landing page logo upload."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.user import User
from app.services.logo_upload_service import LogoUploadResult
from tests.conftest import FAKE_FIREBASE_UID

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}

_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def landing_page_fixture(client: TestClient, mock_firebase: None) -> str:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings

    client.post("/users/sync", json={"name": "Logo Tester"}, headers=_AUTH_HEADER)

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    experiment_id = uuid4()
    landing_page_id = uuid4()
    slug = f"logo-{uuid4().hex[:10]}"

    async def _seed() -> None:
        async with sm() as session:
            user = (
                await session.execute(
                    select(User).where(User.firebase_uid == FAKE_FIREBASE_UID)
                )
            ).scalar_one()
            session.add(
                Experiment(
                    id=experiment_id,
                    user_id=user.id,
                    raw_idea="Test idea",
                    name="Logo Startup",
                    status=ExperimentStatus.LANDING_DRAFT,
                )
            )
            session.add(
                LandingPage(
                    id=landing_page_id,
                    experiment_id=experiment_id,
                    slug=slug,
                    template_id="minimal-v3",
                    palette_id="default",
                    font_pair_id="sans",
                    density=LandingDensity.ROOMY,
                    headline="Test",
                    subheadline="Sub",
                    problem_desc="Problem",
                    solution_desc="Solution",
                    cta_text="Join",
                    cta_type=LandingCtaType.WAITLIST,
                    copy_json={},
                    page_json={},
                )
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_seed())
    return str(experiment_id)


@patch("app.routers.experiments.upload_landing_page_logo")
def test_upload_landing_page_logo(
    mock_upload: MagicMock,
    client: TestClient,
    landing_page_fixture: str,
) -> None:
    mock_upload.return_value = LogoUploadResult(
        logo_url="https://storage.example/logo.png",
        filename="logo.png",
    )

    experiment_id = landing_page_fixture
    resp = client.post(
        f"/experiments/{experiment_id}/landing-page/logo",
        headers=_AUTH_HEADER,
        files={"file": ("logo.png", BytesIO(_PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["logo_url"] == "https://storage.example/logo.png"
    assert body["filename"] == "logo.png"
    mock_upload.assert_called_once()


def test_upload_landing_page_logo_local_storage(
    client: TestClient,
    landing_page_fixture: str,
) -> None:
    experiment_id = landing_page_fixture
    resp = client.post(
        f"/experiments/{experiment_id}/landing-page/logo",
        headers=_AUTH_HEADER,
        files={"file": ("logo.png", BytesIO(_PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["logo_url"].startswith("http://testserver/uploads/landing-logos/")
    assert body["filename"].endswith(".png")

    logo_resp = client.get(body["logo_url"].replace("http://testserver", ""))
    assert logo_resp.status_code == 200
    assert logo_resp.content == _PNG_BYTES


def test_upload_landing_page_logo_rejects_invalid_type(
    client: TestClient,
    landing_page_fixture: str,
) -> None:
    experiment_id = landing_page_fixture
    resp = client.post(
        f"/experiments/{experiment_id}/landing-page/logo",
        headers=_AUTH_HEADER,
        files={"file": ("bad.txt", BytesIO(b"not an image"), "text/plain")},
    )
    assert resp.status_code == 400
