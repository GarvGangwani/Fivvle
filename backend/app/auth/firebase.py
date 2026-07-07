"""
Firebase Admin SDK initialization and token verification.

Design decisions:
- Idempotent: safe to import or call init_firebase() multiple times.
- Module-level flag avoids the SDK's own ValueError for re-initialization.
- No credentials or paths are ever logged (AGENTS.md "Logging hygiene").
- verify_id_token is a thin wrapper so tests can patch one location.
"""

import base64
import json
import os
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


def _service_account_json_raw(settings: Settings) -> str:
    """Load inline service account JSON from settings or process env."""
    raw = settings.firebase_service_account_json.strip()
    if raw:
        return raw
    return os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()


def _service_account_json_b64_raw() -> str:
    """Optional base64-encoded JSON — safer to paste in some host env UIs."""
    return os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON_B64", "").strip()


def _parse_service_account_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "FIREBASE_SERVICE_ACCOUNT_JSON is set but is not valid JSON. "
            "Paste minified single-line JSON from Firebase Console, or set "
            "FIREBASE_SERVICE_ACCOUNT_JSON_B64 to the base64-encoded file."
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON must decode to a JSON object.")
    return parsed


def _materialize_service_account_file(json_raw: str, cred_path: Path) -> None:
    cred_path.parent.mkdir(parents=True, exist_ok=True)
    cred_path.write_text(json_raw, encoding="utf-8")


def _load_firebase_certificate(settings: Settings) -> credentials.Certificate:
    json_raw = _service_account_json_raw(settings)
    if not json_raw:
        b64_raw = _service_account_json_b64_raw()
        if b64_raw:
            try:
                json_raw = base64.b64decode(b64_raw).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(
                    "FIREBASE_SERVICE_ACCOUNT_JSON_B64 is set but is not valid base64 UTF-8 JSON."
                ) from exc

    cred_path = _resolve_service_account_path(settings)

    if json_raw:
        _materialize_service_account_file(json_raw, cred_path)
        return credentials.Certificate(_parse_service_account_json(json_raw))

    if cred_path.is_file():
        return credentials.Certificate(str(cred_path))

    raise FileNotFoundError(
        f"Firebase service account file not found: {cred_path}. "
        "Set FIREBASE_SERVICE_ACCOUNT_JSON (minified JSON), "
        "FIREBASE_SERVICE_ACCOUNT_JSON_B64 (base64 of the JSON file), "
        "or FIREBASE_SERVICE_ACCOUNT_PATH to a readable file path."
    )


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

    json_raw = _service_account_json_raw(settings)
    b64_set = bool(_service_account_json_b64_raw())
    cred_path = _resolve_service_account_path(settings)
    _logger.info(
        "firebase credential sources",
        json_env_set=bool(json_raw),
        json_b64_env_set=b64_set,
        credential_path=str(cred_path),
        credential_file_exists=cred_path.is_file(),
    )

    cred = _load_firebase_certificate(settings)
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
