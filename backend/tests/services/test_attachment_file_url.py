"""Tests for attachment file_url absolutization (local thumbnail fix)."""

from __future__ import annotations

from app.services.attachment_upload_service import absolutize_attachment_file_url


def test_absolutize_relative_uploads_path() -> None:
    assert (
        absolutize_attachment_file_url(
            "/uploads/experiment-attachments/aaa/bbb.png",
            "http://localhost:8000/",
        )
        == "http://localhost:8000/uploads/experiment-attachments/aaa/bbb.png"
    )


def test_absolutize_legacy_media_path() -> None:
    assert (
        absolutize_attachment_file_url(
            "/media/experiment-attachments/aaa/bbb.png",
            "http://localhost:8000",
        )
        == "http://localhost:8000/uploads/experiment-attachments/aaa/bbb.png"
    )


def test_absolutize_leaves_https_alone() -> None:
    url = "https://firebasestorage.googleapis.com/v0/b/x/o/y?alt=media"
    assert absolutize_attachment_file_url(url, "http://localhost:8000") == url
