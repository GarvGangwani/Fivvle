"""Tests for landing page slug availability and patch."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.enums import ExperimentStatus, LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.user import User
from tests.conftest import FAKE_FIREBASE_UID

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


@pytest.fixture
def landing_page_fixture(client: TestClient, mock_firebase: None) -> tuple[str, str]:
    """Create user, experiment in LANDING_DRAFT, and landing page row."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings

    client.post("/users/sync", json={"name": "Slug Tester"}, headers=_AUTH_HEADER)

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    experiment_id = uuid4()
    landing_page_id = uuid4()
    slug = f"test-{uuid4().hex[:10]}"

    async def _seed() -> None:
        async with sm() as session:
            user = (
                await session.execute(
                    select(User).where(User.firebase_uid == FAKE_FIREBASE_UID)
                )
            ).scalar_one()
            experiment = Experiment(
                id=experiment_id,
                user_id=user.id,
                raw_idea="Test idea",
                name="My Startup",
                status=ExperimentStatus.LANDING_DRAFT,
            )
            session.add(experiment)
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
    return str(experiment_id), slug


def test_slug_availability_own_slug_is_available(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, slug = landing_page_fixture
    resp = client.get(
        f"/experiments/{experiment_id}/landing-page/slug-availability",
        params={"slug": slug},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["taken_by_live"] is False


def test_slug_availability_rejects_short_slug(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, _slug = landing_page_fixture
    resp = client.get(
        f"/experiments/{experiment_id}/landing-page/slug-availability",
        params={"slug": "abc"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False


def test_patch_landing_page_slug(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    experiment_id, _slug = landing_page_fixture
    new_slug = f"newco-{uuid4().hex[:8]}"
    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"slug": new_slug},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == new_slug


def test_patch_landing_page_slug_when_live(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    from uuid import UUID

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment

    experiment_id, _slug = landing_page_fixture
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _set_live() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.LANDING_LIVE)
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_set_live())

    new_slug = f"live-{uuid4().hex[:8]}"
    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"slug": new_slug},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == new_slug


def test_patch_live_landing_page_allows_copy_changes(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    from uuid import UUID

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment

    experiment_id, _slug = landing_page_fixture
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _set_live() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.LANDING_LIVE)
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_set_live())

    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"copy_json": {"hero": {"headline": "Updated live headline", "subheadline": "New sub", "cta": "Join"}}},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["copy_json"]["hero"]["headline"] == "Updated live headline"


def test_patch_live_landing_page_triggers_revalidate(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime
    from uuid import UUID

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment
    from app.db.models.landing_page import LandingPage

    experiment_id, slug = landing_page_fixture
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    now = datetime.now(UTC)

    async def _set_live() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.LANDING_LIVE)
            )
            await session.execute(
                update(LandingPage)
                .where(LandingPage.experiment_id == UUID(experiment_id))
                .values(live_at=now)
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_set_live())

    calls: list[list[str]] = []

    async def _fake_notify(
        _db: object,
        landing_page: object,
        *,
        previous_slug: str | None = None,
    ) -> None:
        slugs = [getattr(landing_page, "slug")]
        if previous_slug and previous_slug != getattr(landing_page, "slug"):
            slugs.append(previous_slug)
        calls.append(slugs)

    monkeypatch.setattr(
        "app.routers.experiments.notify_live_landing_page_changed",
        _fake_notify,
    )

    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"template_id": "bold-v1"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert calls == [[slug]]


def test_patch_draft_landing_page_does_not_revalidate(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiment_id, _slug = landing_page_fixture
    calls: list[list[str]] = []

    async def _fake_notify(
        _db: object,
        landing_page: object,
        *,
        previous_slug: str | None = None,
    ) -> None:
        slugs = [getattr(landing_page, "slug")]
        if previous_slug and previous_slug != getattr(landing_page, "slug"):
            slugs.append(previous_slug)
        calls.append(slugs)

    monkeypatch.setattr(
        "app.routers.experiments.notify_live_landing_page_changed",
        _fake_notify,
    )

    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"template_id": "bold-v1"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert calls == []


def test_patch_live_landing_page_allows_design_page_json(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    from uuid import UUID

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment

    experiment_id, _slug = landing_page_fixture
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _set_live() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.LANDING_LIVE)
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_set_live())

    design_patch = {
        "page_json": {
            "color_mode": "dark",
            "color_palette": {
                "preset": "custom",
                "accent": "#ff5500",
                "background": "#111111",
                "foreground": "#eeeeee",
            },
            "surface": {
                "texture": "grain",
                "hero_glow": "bold",
                "gradient_style": "mesh-warm",
            },
        }
    }
    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json=design_patch,
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page_json"]["surface"]["texture"] == "grain"
    assert body["page_json"]["color_palette"]["accent"] == "#ff5500"


def test_patch_insight_ready_allows_copy_changes(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    from datetime import UTC, datetime
    from uuid import UUID

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment
    from app.db.models.landing_page import LandingPage

    experiment_id, _slug = landing_page_fixture
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    now = datetime.now(UTC)

    async def _set_insight_ready_live() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.INSIGHT_READY)
            )
            await session.execute(
                update(LandingPage)
                .where(LandingPage.experiment_id == UUID(experiment_id))
                .values(live_at=now)
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_set_insight_ready_live())

    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"copy_json": {"hero": {"headline": "Still editable", "subheadline": "Sub", "cta": "Join"}}},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert resp.json()["copy_json"]["hero"]["headline"] == "Still editable"


def test_patch_archived_landing_page_returns_409(
    client: TestClient,
    landing_page_fixture: tuple[str, str],
) -> None:
    from uuid import UUID

    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.db.enums import ExperimentStatus
    from app.db.models.experiment import Experiment

    experiment_id, _slug = landing_page_fixture
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _set_archived() -> None:
        async with sm() as session:
            await session.execute(
                update(Experiment)
                .where(Experiment.id == UUID(experiment_id))
                .values(status=ExperimentStatus.ARCHIVED)
            )
            await session.commit()

    import asyncio

    asyncio.get_event_loop().run_until_complete(_set_archived())

    resp = client.patch(
        f"/experiments/{experiment_id}/landing-page",
        json={"template_id": "bold-v1"},
        headers=_AUTH_HEADER,
    )
    assert resp.status_code == 409
    assert "Archived" in resp.json()["detail"]
