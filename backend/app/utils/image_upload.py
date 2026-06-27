"""Validate uploaded image bytes by magic number (not filename extension)."""

from __future__ import annotations

MAX_LOGO_BYTES = 2 * 1024 * 1024
MAX_SECTION_IMAGE_BYTES = 5 * 1024 * 1024

_CONTENT_TYPE_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


def sniff_image_content_type(data: bytes) -> str | None:
    if len(data) < 12:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def extension_for_content_type(content_type: str) -> str:
    ext = _CONTENT_TYPE_TO_EXT.get(content_type)
    if ext is None:
        raise ValueError("Unsupported image type")
    return ext
