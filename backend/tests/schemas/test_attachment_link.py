"""Tests for Spark attachment schema validation (link type)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.experiment_attachments import AttachmentCreateIn


def test_link_attachment_accepts_https_url() -> None:
    row = AttachmentCreateIn(
        attachment_type="link",
        title="Competitor site",
        file_url="https://example.com",
    )
    assert row.file_url == "https://example.com"
    assert row.content_text is None
    assert row.file_mime is None
    assert row.file_size_bytes is None


def test_link_attachment_rejects_non_url() -> None:
    with pytest.raises(ValidationError):
        AttachmentCreateIn(
            attachment_type="link",
            title="test",
            file_url="not-a-url",
        )


def test_link_attachment_rejects_content_text() -> None:
    with pytest.raises(ValidationError):
        AttachmentCreateIn(
            attachment_type="link",
            title="test",
            file_url="https://example.com",
            content_text="nope",
        )
