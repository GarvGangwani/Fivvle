"""Upload landing-page media: brand logos and section images (local dev, Firebase prod)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

from firebase_admin import storage

from app.config import Settings, get_settings
from app.logging_config import get_logger
from app.utils.image_upload import (
    MAX_LOGO_BYTES,
    MAX_SECTION_IMAGE_BYTES,
    extension_for_content_type,
    sniff_image_content_type,
)

_logger = get_logger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_LOCAL_LOGO_ROOT = _BACKEND_ROOT / "var" / "uploads" / "landing-logos"
_LOCAL_SECTION_IMAGE_ROOT = _BACKEND_ROOT / "var" / "uploads" / "landing-section-images"


class LogoUploadError(ValueError):
    """User-facing validation failure."""


class LogoUploadResult:
    __slots__ = ("logo_url", "filename")

    def __init__(self, logo_url: str, filename: str) -> None:
        self.logo_url = logo_url
        self.filename = filename


class SectionImageUploadResult:
    __slots__ = ("image_url", "filename")

    def __init__(self, image_url: str, filename: str) -> None:
        self.image_url = image_url
        self.filename = filename


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


def _validate_image_bytes(file_bytes: bytes, *, max_bytes: int, size_label: str) -> tuple[str, str]:
    if not file_bytes:
        raise LogoUploadError("Uploaded file is empty.")
    if len(file_bytes) > max_bytes:
        raise LogoUploadError(f"Image must be {size_label} or smaller.")

    content_type = sniff_image_content_type(file_bytes)
    if content_type is None:
        raise LogoUploadError("Use a PNG, JPEG, or WebP image.")

    ext = extension_for_content_type(content_type)
    return content_type, ext


def _validate_logo_bytes(file_bytes: bytes) -> tuple[str, str]:
    return _validate_image_bytes(file_bytes, max_bytes=MAX_LOGO_BYTES, size_label="2 MB")


def _validate_section_image_bytes(file_bytes: bytes) -> tuple[str, str]:
    return _validate_image_bytes(
        file_bytes,
        max_bytes=MAX_SECTION_IMAGE_BYTES,
        size_label="5 MB",
    )


def _upload_local(
    *,
    experiment_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
    content_type: str,
    ext: str,
) -> LogoUploadResult:
    filename = f"{uuid4()}.{ext}"
    rel_path = f"{user_id}/{experiment_id}/{filename}"
    dest = _LOCAL_LOGO_ROOT / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_bytes)

    _logger.info(
        "landing page logo stored locally",
        experiment_id=str(experiment_id),
        user_id=str(user_id),
        path=rel_path,
        content_type=content_type,
    )
    return LogoUploadResult(
        logo_url=f"/uploads/landing-logos/{rel_path}",
        filename=filename,
    )


def _upload_firebase(
    *,
    experiment_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
    content_type: str,
    ext: str,
    settings: Settings,
) -> LogoUploadResult:
    filename = f"{uuid4()}.{ext}"
    object_path = f"landing-logos/{user_id}/{experiment_id}/{filename}"
    bucket_name = _bucket_name(settings)

    bucket = storage.bucket(bucket_name)
    blob = bucket.blob(object_path)
    blob.upload_from_string(file_bytes, content_type=content_type)
    blob.cache_control = "public, max-age=31536000, immutable"
    blob.patch()

    try:
        blob.make_public()
        logo_url = blob.public_url
    except Exception:
        logo_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=3650),
            method="GET",
        )
        if not logo_url:
            encoded = quote(object_path, safe="")
            logo_url = (
                f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}"
                f"/o/{encoded}?alt=media"
            )

    _logger.info(
        "landing page logo uploaded to firebase",
        experiment_id=str(experiment_id),
        user_id=str(user_id),
        object_path=object_path,
    )
    return LogoUploadResult(logo_url=logo_url, filename=filename)


def upload_landing_page_logo(
    *,
    experiment_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
) -> LogoUploadResult:
    content_type, ext = _validate_logo_bytes(file_bytes)
    settings = get_settings()

    if _use_local_storage(settings):
        return _upload_local(
            experiment_id=experiment_id,
            user_id=user_id,
            file_bytes=file_bytes,
            content_type=content_type,
            ext=ext,
        )

    try:
        return _upload_firebase(
            experiment_id=experiment_id,
            user_id=user_id,
            file_bytes=file_bytes,
            content_type=content_type,
            ext=ext,
            settings=settings,
        )
    except Exception as exc:
        if settings.environment in ("development", "test"):
            _logger.warning(
                "firebase logo upload failed; falling back to local storage",
                experiment_id=str(experiment_id),
                error=str(exc),
            )
            return _upload_local(
                experiment_id=experiment_id,
                user_id=user_id,
                file_bytes=file_bytes,
                content_type=content_type,
                ext=ext,
            )
        raise


def _upload_section_image_local(
    *,
    experiment_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
    content_type: str,
    ext: str,
) -> SectionImageUploadResult:
    filename = f"{uuid4()}.{ext}"
    rel_path = f"{user_id}/{experiment_id}/{filename}"
    dest = _LOCAL_SECTION_IMAGE_ROOT / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_bytes)

    _logger.info(
        "landing page section image stored locally",
        experiment_id=str(experiment_id),
        user_id=str(user_id),
        path=rel_path,
        content_type=content_type,
    )
    return SectionImageUploadResult(
        image_url=f"/uploads/landing-section-images/{rel_path}",
        filename=filename,
    )


def _upload_section_image_firebase(
    *,
    experiment_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
    content_type: str,
    ext: str,
    settings: Settings,
) -> SectionImageUploadResult:
    filename = f"{uuid4()}.{ext}"
    object_path = f"landing-section-images/{user_id}/{experiment_id}/{filename}"
    bucket_name = _bucket_name(settings)

    bucket = storage.bucket(bucket_name)
    blob = bucket.blob(object_path)
    blob.upload_from_string(file_bytes, content_type=content_type)
    blob.cache_control = "public, max-age=31536000, immutable"
    blob.patch()

    try:
        blob.make_public()
        image_url = blob.public_url
    except Exception:
        image_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=3650),
            method="GET",
        )
        if not image_url:
            encoded = quote(object_path, safe="")
            image_url = (
                f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}"
                f"/o/{encoded}?alt=media"
            )

    _logger.info(
        "landing page section image uploaded to firebase",
        experiment_id=str(experiment_id),
        user_id=str(user_id),
        object_path=object_path,
    )
    return SectionImageUploadResult(image_url=image_url, filename=filename)


def upload_landing_page_section_image(
    *,
    experiment_id: UUID,
    user_id: UUID,
    file_bytes: bytes,
) -> SectionImageUploadResult:
    content_type, ext = _validate_section_image_bytes(file_bytes)
    settings = get_settings()

    if _use_local_storage(settings):
        return _upload_section_image_local(
            experiment_id=experiment_id,
            user_id=user_id,
            file_bytes=file_bytes,
            content_type=content_type,
            ext=ext,
        )

    try:
        return _upload_section_image_firebase(
            experiment_id=experiment_id,
            user_id=user_id,
            file_bytes=file_bytes,
            content_type=content_type,
            ext=ext,
            settings=settings,
        )
    except Exception as exc:
        if settings.environment in ("development", "test"):
            _logger.warning(
                "firebase section image upload failed; falling back to local storage",
                experiment_id=str(experiment_id),
                error=str(exc),
            )
            return _upload_section_image_local(
                experiment_id=experiment_id,
                user_id=user_id,
                file_bytes=file_bytes,
                content_type=content_type,
                ext=ext,
            )
        raise


def resolve_local_logo_path(user_id: str, experiment_id: str, filename: str) -> Path:
    """Resolve a validated relative logo path to an on-disk file."""
    safe_name = Path(filename).name
    return _LOCAL_LOGO_ROOT / user_id / experiment_id / safe_name


def resolve_local_section_image_path(user_id: str, experiment_id: str, filename: str) -> Path:
    """Resolve a validated relative section-image path to an on-disk file."""
    safe_name = Path(filename).name
    return _LOCAL_SECTION_IMAGE_ROOT / user_id / experiment_id / safe_name


def local_logo_content_type(path: Path) -> str:
    data = path.read_bytes()[:16]
    return sniff_image_content_type(data) or "application/octet-stream"


def local_section_image_content_type(path: Path) -> str:
    return local_logo_content_type(path)
