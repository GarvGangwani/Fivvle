"""Router tests for admin coupon management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from uuid import uuid4

import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models.coupon import Coupon
from tests.routers.test_admin_chat_quality import _create_admin_user
from tests.routers.test_wallet_balance import _sync_user

_AUTH_HEADER = {"Authorization": "Bearer faketoken"}


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


def test_admin_coupons_requires_admin(
    client: TestClient,
    mock_firebase_non_admin: None,
) -> None:
    _sync_user(client)
    resp = client.get("/admin/coupons", headers=_AUTH_HEADER)
    assert resp.status_code == 403


def test_admin_create_and_list_coupons(
    client: TestClient,
    mock_firebase: None,
    db_session: AsyncSession,
) -> None:
    asyncio.get_event_loop().run_until_complete(_create_admin_user(db_session))
    _sync_user(client)

    code = f"LAUNCH50{uuid4().hex[:6].upper()}"
    create = client.post(
        "/admin/coupons",
        headers=_AUTH_HEADER,
        json={
            "code": code,
            "credits": 50,
            "enabled": True,
            "max_redemptions": 100,
            "limit_reached_message": "Launch promo is full.",
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["code"] == code
    assert body["credits"] == 50
    assert body["redemption_count"] == 0
    assert body["total_usd_gifted"] == "$0"

    listing = client.get("/admin/coupons", headers=_AUTH_HEADER)
    assert listing.status_code == 200
    listed = listing.json()
    assert any(item["code"] == code for item in listed["coupons"])


def test_admin_patch_coupon_enable_disable(
    client: TestClient,
    mock_firebase: None,
    db_session: AsyncSession,
) -> None:
    async def _seed() -> str:
        await _create_admin_user(db_session)
        coupon = Coupon(
            code=f"TOGGLE10{uuid4().hex[:6].upper()}",
            credits=10,
            enabled=True,
        )
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)
        return str(coupon.id)

    coupon_id = asyncio.get_event_loop().run_until_complete(_seed())
    _sync_user(client)

    patch = client.patch(
        f"/admin/coupons/{coupon_id}",
        headers=_AUTH_HEADER,
        json={"enabled": False, "disabled_message": "Paused for now."},
    )
    assert patch.status_code == 200
    assert patch.json()["enabled"] is False


def test_admin_archive_restore_and_delete_coupon(
    client: TestClient,
    mock_firebase: None,
    db_session: AsyncSession,
) -> None:
    from app.db.models.coupon_redemption import CouponRedemption
    from tests.services.test_wallet_service import _make_user

    async def _seed() -> tuple[str, str]:
        await _create_admin_user(db_session)
        redeemer = await _make_user(db_session)
        unused = Coupon(
            code=f"DELME{uuid4().hex[:6].upper()}",
            credits=5,
            enabled=True,
        )
        used = Coupon(
            code=f"USED{uuid4().hex[:6].upper()}",
            credits=5,
            enabled=True,
        )
        db_session.add_all([unused, used])
        await db_session.flush()
        db_session.add(
            CouponRedemption(
                coupon_id=used.id,
                user_id=redeemer.id,
                credits=used.credits,
            )
        )
        await db_session.commit()
        await db_session.refresh(unused)
        await db_session.refresh(used)
        return str(unused.id), str(used.id)

    unused_id, used_id = asyncio.get_event_loop().run_until_complete(_seed())
    _sync_user(client)

    archive = client.post(
        f"/admin/coupons/{used_id}/archive",
        headers=_AUTH_HEADER,
    )
    assert archive.status_code == 200
    assert archive.json()["archived_at"] is not None
    assert archive.json()["enabled"] is False

    listing = client.get("/admin/coupons", headers=_AUTH_HEADER)
    assert all(item["id"] != used_id for item in listing.json()["coupons"])

    archived_listing = client.get(
        "/admin/coupons?include_archived=true",
        headers=_AUTH_HEADER,
    )
    assert any(item["id"] == used_id for item in archived_listing.json()["coupons"])

    delete_used = client.delete(
        f"/admin/coupons/{used_id}",
        headers=_AUTH_HEADER,
    )
    assert delete_used.status_code == 409

    restore = client.post(
        f"/admin/coupons/{used_id}/restore",
        headers=_AUTH_HEADER,
    )
    assert restore.status_code == 200
    assert restore.json()["archived_at"] is None

    delete_unused = client.delete(
        f"/admin/coupons/{unused_id}",
        headers=_AUTH_HEADER,
    )
    assert delete_unused.status_code == 204
