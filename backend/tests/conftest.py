"""Shared pytest fixtures.

Includes:
- mock_firebase: patches verify_id_token to return a fake decoded token,
  avoiding real network calls to Firebase during tests.
- _skip_firebase_init: prevents real Firebase Admin SDK initialization when
  the TestClient lifespan runs (no service account file needed in tests).
- _init_db_engine: ensures the async DB engine is ready before any test.
- client: full async test client connected to live Docker Postgres,
  with test-user cleanup after each test.
"""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import init_engine

# A canonical fake decoded token used across most tests.
FAKE_FIREBASE_UID = "test-firebase-uid-abc123"
FAKE_EMAIL = "test@example.com"
FAKE_DECODED_TOKEN = {
    "uid": FAKE_FIREBASE_UID,
    "email": FAKE_EMAIL,
    "email_verified": True,
}

NON_ADMIN_FIREBASE_UID = "test-firebase-uid-non-admin"
NON_ADMIN_EMAIL = "founder@example.com"
NON_ADMIN_DECODED_TOKEN = {
    "uid": NON_ADMIN_FIREBASE_UID,
    "email": NON_ADMIN_EMAIL,
    "email_verified": True,
}


@pytest.fixture
def mock_firebase() -> Generator[None, None, None]:
    """Patch verify_id_token to return a fake decoded token.

    Any test using this fixture can pass any string as the Bearer token
    and the patched verify_id_token will return FAKE_DECODED_TOKEN.

    Patching is done in three places because `from app.auth.firebase import
    verify_id_token` in each module copies the function reference into that
    module's namespace. Patching only `app.auth.firebase.verify_id_token`
    would leave the copies in dependencies.py and routers/users.py unchanged.
    All three import sites must be patched.

    To simulate auth failures, override the patch inside the test:
        with patch("app.routers.users.verify_id_token", side_effect=...):
            ...
    """
    with patch(
        "app.auth.firebase.verify_id_token",
        return_value=FAKE_DECODED_TOKEN,
    ), patch(
        "app.auth.dependencies.verify_id_token",
        return_value=FAKE_DECODED_TOKEN,
    ), patch(
        "app.routers.users.verify_id_token",
        return_value=FAKE_DECODED_TOKEN,
    ):
        yield


@pytest.fixture
def mock_firebase_non_admin() -> Generator[None, None, None]:
    """Patch verify_id_token with a non-admin email (not on ADMIN_EMAILS allowlist)."""
    with patch(
        "app.auth.firebase.verify_id_token",
        return_value=NON_ADMIN_DECODED_TOKEN,
    ), patch(
        "app.auth.dependencies.verify_id_token",
        return_value=NON_ADMIN_DECODED_TOKEN,
    ), patch(
        "app.routers.users.verify_id_token",
        return_value=NON_ADMIN_DECODED_TOKEN,
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def _skip_firebase_init() -> Generator[None, None, None]:
    """Prevent real Firebase Admin SDK initialization during the test session.

    The TestClient context manager triggers the app lifespan, which calls
    init_firebase(settings). Without this fixture, that call would attempt to
    read a real service account JSON file — which doesn't exist in CI or local
    dev test environments. Patching init_firebase to a no-op is the cleanest
    approach: we don't need a real Firebase app to test auth endpoints because
    verify_id_token is patched separately via mock_firebase.
    """
    with patch("app.auth.firebase.init_firebase"):
        yield


@pytest.fixture(scope="session", autouse=True)
def _init_db_engine() -> Generator[None, None, None]:
    """Initialize the DB engine for the test session.

    Tests need the engine populated (so get_session works inside route handlers),
    but the FastAPI lifespan doesn't run during TestClient construction by default.
    This autouse session fixture solves that.
    """
    settings = get_settings()
    init_engine(settings)
    yield
    # dispose_engine is async; pytest's session teardown runs sync. We
    # rely on process exit to dispose; not ideal but acceptable for tests.


@pytest.fixture(scope="session", autouse=True)
def _configure_test_admin_emails() -> Generator[None, None, None]:
    """Let admin API tests use the canonical fake user email."""
    import os

    os.environ["ADMIN_EMAILS"] = FAKE_EMAIL
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _default_monetization_disabled(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Tests opt into billing via the monetization_enabled fixture."""
    monkeypatch.setenv("MONETIZATION_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_slowapi_limiter_storage_between_tests() -> Generator[None, None, None]:
    """Clear in-memory rate-limit counters after each test.

    The default slowapi backend is process-wide; POST /users/sync keys by IP
    when no User exists yet, so hundreds of tests sharing ``testclient`` would
    exhaust the 60/min bucket and cause unrelated tests to see 429.
    """
    yield
    from app.reliability.rate_limit import limiter  # noqa: PLC0415

    storage = getattr(limiter, "_storage", None)
    reset = getattr(storage, "reset", None)
    if callable(reset):
        reset()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """A TestClient that exercises the full FastAPI app, including dependencies.

    Each test gets its own client. Database state persists across tests within
    a session (we explicitly clean up users in test teardown to avoid bleed).
    """
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
async def _cleanup_test_users() -> AsyncGenerator[None, None]:
    """Delete the fake test user after each test to ensure idempotency.

    Without this, the second test run for /users/sync would hit the
    "already exists" branch unintentionally.

    We create a completely standalone engine here rather than reusing the
    module-level one from app.db.session. The `client` fixture runs the full
    FastAPI lifespan as a context manager — including shutdown, which calls
    dispose_engine() and sets the module-level engine to None. This fixture
    runs AFTER the client fixture tears down, so the module-level engine is
    already gone. A standalone engine created inside this async context uses
    the current event loop and is fully disposed before the fixture exits,
    avoiding cross-event-loop asyncpg contamination.
    """
    yield

    from sqlalchemy import delete  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

    from app.db.models.user import User  # noqa: PLC0415

    engine = create_async_engine(get_settings().database_url, pool_size=1, max_overflow=0)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with sm() as session:
            # Delete the canonical admin test user AND any secondary test users
            # created by tests (firebase_uid prefix "other-firebase-uid-" or email
            # ending @example.com). Test data only — production emails never use
            # @example.com.
            from sqlalchemy import or_  # noqa: PLC0415
            await session.execute(
                delete(User).where(
                    or_(
                        User.firebase_uid == FAKE_FIREBASE_UID,
                        User.firebase_uid.like("other-firebase-uid-%"),
                        User.email.like("%@example.com"),
                    )
                )
            )
            await session.commit()
    except OSError:
        # Postgres not reachable (Docker offline / CI flake) — skip cleanup for pure unit runs.
        pass
    finally:
        await engine.dispose()
