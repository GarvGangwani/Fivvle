"""Unit tests for image upload validation."""

from app.utils.image_upload import MAX_LOGO_BYTES, sniff_image_content_type

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"

_WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 "


def test_sniff_png() -> None:
    assert sniff_image_content_type(_PNG) == "image/png"


def test_sniff_jpeg() -> None:
    assert sniff_image_content_type(_JPEG) == "image/jpeg"


def test_sniff_webp() -> None:
    assert sniff_image_content_type(_WEBP) == "image/webp"


def test_sniff_rejects_unknown() -> None:
    assert sniff_image_content_type(b"hello") is None


def test_max_logo_bytes_is_two_mb() -> None:
    assert MAX_LOGO_BYTES == 2 * 1024 * 1024
