"""Tests for chat attachment validation and extraction."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.utils.chat_attachment import (
    ChatAttachmentValidationError,
    detect_attachment_kind,
    extract_attachment_text,
    sanitize_display_filename,
)


def test_sanitize_display_filename_strips_path() -> None:
    assert sanitize_display_filename(r"notes\pitch.pdf") == "pitch.pdf"


def test_detect_and_extract_utf8_text() -> None:
    data = b"# Idea notes\n\nUsers want faster onboarding."
    kind = detect_attachment_kind(data, filename="notes.md")
    assert kind == "text"
    text = extract_attachment_text(data, filename="notes.md", kind=kind)
    assert "faster onboarding" in text


def test_detect_and_extract_docx() -> None:
    buffer = io.BytesIO()
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Founder memo</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    data = buffer.getvalue()

    kind = detect_attachment_kind(data, filename="memo.docx")
    assert kind == "docx"
    text = extract_attachment_text(data, filename="memo.docx", kind=kind)
    assert text == "Founder memo"


def test_rejects_unknown_binary() -> None:
    with pytest.raises(ChatAttachmentValidationError):
        detect_attachment_kind(b"\x00\x01\x02\x03", filename="mystery.bin")
