"""Smoke test for DB connectivity.

Requires the local Postgres container to be running:
    docker compose up -d

This test is intentionally NOT a unit test — it exercises the real
async engine against the real Postgres. If you're refactoring DB code,
this is the test that catches "the connection string is wrong" or "the
engine doesn't actually work."
"""

import pytest
from sqlalchemy import text

import app.db.session as db_session_module
from app.config import get_settings
from app.db.session import dispose_engine, init_engine


@pytest.mark.asyncio
async def test_engine_can_connect_to_postgres() -> None:
    settings = get_settings()
    init_engine(settings)

    # Access via module attribute at runtime — the module-level variable is
    # set by init_engine(); a direct import would capture the pre-init None.
    assert db_session_module._sessionmaker is not None  # type: ignore[attr-defined]

    async with db_session_module._sessionmaker() as session:  # type: ignore[attr-defined]
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    await dispose_engine()
