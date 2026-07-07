"""
Firebase Admin SDK initialization and token verification.

Design decisions:
- Idempotent: safe to import or call init_firebase() multiple times.
- Module-level flag avoids the SDK's own ValueError for re-initialization.
- No credentials or paths are ever logged (AGENTS.md "Logging hygiene").
- verify_id_token is a thin wrapper so tests can patch one location.
"""

import json
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.config import Settings
from app.logging_config import get_logger

_logger = get_logger(__name__)

# Module-level flag so init is idempotent across multiple callers.
_initialized: bool = False

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_service_account_path(settings: Settings) -> Path:
    """Resolve FIREBASE_SERVICE_ACCOUNT_PATH to an absolute filesystem path."""
    raw = settings.firebase_service_account_path.strip()
    path = Path(raw)
    if not path.is_absolute():
        path = (_BACKEND_ROOT / path).resolve()
    return path


def init_firebase(settings: Settings) -> None:
    """Initialize the Firebase Admin SDK.

    Idempotent — calling this function more than once (e.g., in tests or
    during a hot-reload) is safe.  The service account file path is read
    from ``settings.firebase_service_account_path``; the value itself is
    never logged.

    Args:
        settings: Application settings instance.
    """
    global _initialized  # noqa: PLW0603

    if _initialized:
        return

    json_raw = settings.firebase_service_account_json.strip()
    if json_raw:
        cred = credentials.Certificate(json.loads(json_raw))
    else:
        cred_path = _resolve_service_account_path(settings)
        if not cred_path.is_file():
            raise FileNotFoundError(
                f"Firebase service account file not found: {cred_path}. "
                "Set FIREBASE_SERVICE_ACCOUNT_PATH in backend/.env "
                "(e.g. ./service-account.json) or FIREBASE_SERVICE_ACCOUNT_JSON "
                "for container deployments. "
                "If you use a Windows GOOGLE_APPLICATION_CREDENTIALS variable, "
                "it no longer overrides Fivvle — use FIREBASE_SERVICE_ACCOUNT_PATH."
            )
        cred = credentials.Certificate(str(cred_path))
    bucket = settings.firebase_storage_bucket.strip() or f"{settings.firebase_project_id}.appspot.com"
    try:
        firebase_admin.initialize_app(cred, {"storageBucket": bucket})
    except ValueError:
        # Firebase Admin raises ValueError when the default app already exists.
        # Treat this as success — the SDK is already initialized.
        pass

    _initialized = True
    _logger.info("firebase admin initialized")


def is_initialized() -> bool:
    """Return True if the Firebase Admin SDK has been initialized."""
    return _initialized


def verify_id_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return the decoded claims.

    Raises:
        firebase_admin.auth.InvalidIdTokenError: token signature is invalid,
            expired, or malformed.
        firebase_admin.auth.ExpiredIdTokenError: token expired.
        firebase_admin.auth.RevokedIdTokenError: token revoked server-side.

    These exceptions are caught and converted to HTTP 401 in the
    get_current_user dependency.

    Args:
        token: the raw token string from the Authorization: Bearer header
            (without the "Bearer " prefix — the dependency strips that).

    Returns:
        Decoded token claims. The "uid" key is the Firebase user ID.
    """
    return firebase_auth.verify_id_token(token)
