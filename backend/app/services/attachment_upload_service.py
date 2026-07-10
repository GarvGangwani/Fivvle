"""Signed upload URLs for experiment Spark attachments (Firebase Storage / local)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

from firebase_admin import storage

from app.config import Settings, get_settings
from app.logging_config import get_logger
from app.schemas.experiment_attachments import (
    ALLOWED_UPLOAD_MIMES,
    MAX_ATTACHMENT_BYTES,
    UploadUrlResponse,
)

_logger = get_logger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_LOCAL_ATTACHMENT_ROOT = _BACKEND_ROOT / "var" / "uploads" / "experiment-attachments"

UPLOAD_URL_TTL = timedelta(minutes=5)

# Public path prefix served by FastAPI (mirrors landing-logo local URLs).
_LOCAL_PUBLIC_PREFIX = "/uploads/experiment-attachments"
_LEGACY_PUBLIC_PREFIX = "/media/experiment-attachments"


class AttachmentUploadError(ValueError):
    """User-facing validation failure for attachment uploads."""


def _bucket_name(settings: Settings) -> str:
    explicit = settings.firebase_storage_bucket.strip()
    if explicit:
        return explicit
    return f"{settings.firebase_project_id}.appspot.com"


def _use_local_storage(settings: Settings) -> bool:
    if settings.logo_upload_backend == "local":
        return True
    if settings.logo_upload_backend == "firebase":
        return False
    return settings.environment in ("development", "test")


def build_public_firebase_url(storage_path: str, *, bucket_name: str | None = None) -> str:
    """Permanent public media URL. Requires public-read Storage rules on the path."""
    settings = get_settings()
    bucket = bucket_name or _bucket_name(settings)
    encoded = quote(storage_path, safe="")
    return (
        f"https://firebasestorage.googleapis.com/v0/b/{bucket}"
        f"/o/{encoded}?alt=media"
    )


def absolutize_attachment_file_url(file_url: str | None, api_base_url: str) -> str | None:
    """Ensure local relative attachment URLs are absolute against the API origin.

    Relative paths like ``/uploads/experiment-attachments/...`` resolve against the
    Next.js origin in ``<img src>`` and 404 — they must point at FastAPI.
    """
    if not file_url:
        return None
    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url

    path = file_url
    if path.startswith(_LEGACY_PUBLIC_PREFIX):
        path = _LOCAL_PUBLIC_PREFIX + path[len(_LEGACY_PUBLIC_PREFIX) :]
    if not path.startswith("/"):
        return file_url
    return f"{api_base_url.rstrip('/')}{path}"


def _sanitize_filename(filename: str) -> str:
    name = filename.strip().replace("\\", "/").split("/")[-1]
    if not name or ".." in name:
        raise AttachmentUploadError("Invalid filename")
    if any(sep in name for sep in ("/", "\\")):
        raise AttachmentUploadError("Filename must not contain path separators")
    return name[:200]


def validate_upload_request(*, filename: str, mime_type: str, size_bytes: int) -> str:
    if mime_type not in ALLOWED_UPLOAD_MIMES:
        raise AttachmentUploadError("MIME type is not allowed")
    if size_bytes < 1 or size_bytes > MAX_ATTACHMENT_BYTES:
        raise AttachmentUploadError("File must be between 1 byte and 25 MB")
    return _sanitize_filename(filename)


def create_attachment_upload_url(
    *,
    experiment_id: UUID,
    filename: str,
    mime_type: str,
    size_bytes: int,
    api_base_url: str,
) -> UploadUrlResponse:
    safe_name = validate_upload_request(
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    object_name = f"{uuid4()}-{safe_name}"
    object_path = f"experiments/{experiment_id}/{object_name}"
    expires_at = datetime.now(timezone.utc) + UPLOAD_URL_TTL
    settings = get_settings()
    api_base = api_base_url.rstrip("/")

    if _use_local_storage(settings):
        upload_url = (
            f"{api_base}/experiments/{experiment_id}"
            f"/attachments/local-upload/{object_name}"
        )
        # Absolute API URL so <img src> hits FastAPI, not the Next.js origin.
        file_url = f"{api_base}{_LOCAL_PUBLIC_PREFIX}/{experiment_id}/{object_name}"
        return UploadUrlResponse(
            upload_url=upload_url,
            file_url=file_url,
            expires_at=expires_at,
        )

    bucket_name = _bucket_name(settings)
    bucket = storage.bucket(bucket_name)
    blob = bucket.blob(object_path)
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=UPLOAD_URL_TTL,
        method="PUT",
        content_type=mime_type,
    )
    file_url = build_public_firebase_url(object_path, bucket_name=bucket_name)
    _logger.info(
        "attachment upload URL issued",
        experiment_id=str(experiment_id),
        object_path=object_path,
    )
    return UploadUrlResponse(
        upload_url=upload_url,
        file_url=file_url,
        expires_at=expires_at,
    )


def store_local_attachment_bytes(
    *,
    experiment_id: UUID,
    object_name: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    if not file_bytes:
        raise AttachmentUploadError("Uploaded file is empty")
    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        raise AttachmentUploadError("File must be 25 MB or smaller")
    if "/" in object_name or "\\" in object_name or ".." in object_name:
        raise AttachmentUploadError("Invalid object name")

    dest = _LOCAL_ATTACHMENT_ROOT / str(experiment_id) / object_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_bytes)
    _logger.info(
        "attachment stored locally",
        experiment_id=str(experiment_id),
        object_name=object_name,
        content_type=content_type,
        size_bytes=len(file_bytes),
    )
    return f"{_LOCAL_PUBLIC_PREFIX}/{experiment_id}/{object_name}"


def resolve_local_attachment_path(experiment_id: str, filename: str) -> Path:
    return _LOCAL_ATTACHMENT_ROOT / experiment_id / filename


def local_attachment_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".doc": "application/msword",
        ".docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    }.get(suffix, "application/octet-stream")
