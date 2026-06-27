"""Validate and extract text from chat attachment uploads."""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

from pypdf import PdfReader

from app.utils.image_upload import sniff_image_content_type

MAX_CHAT_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARS_PER_FILE = 40_000
MAX_ATTACHMENTS_PER_TURN = 5

_ALLOWED_EXTENSIONS = frozenset(
    {
        "png",
        "jpg",
        "jpeg",
        "webp",
        "pdf",
        "txt",
        "md",
        "markdown",
        "docx",
    }
)

_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class ChatAttachmentValidationError(ValueError):
    """User-facing validation failure."""


def sanitize_display_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    if not base:
        raise ChatAttachmentValidationError("Filename is required.")
    cleaned = re.sub(r"[^\w.\- ()]", "_", base)
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    return cleaned


def extension_from_filename(filename: str) -> str | None:
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext if ext in _ALLOWED_EXTENSIONS else None


def _looks_like_utf8_text(data: bytes) -> bool:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not text.strip():
        return False
    # Reject obvious binary payloads mislabeled as text.
    non_printable = sum(1 for ch in text if ch not in "\t\n\r" and ord(ch) < 32)
    return non_printable / max(len(text), 1) < 0.02


def _extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text.strip())
    return "\n\n".join(parts)


def _extract_docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ChatAttachmentValidationError("Invalid Word document.")
            xml_bytes = archive.read("word/document.xml")
    except zipfile.BadZipFile as exc:
        raise ChatAttachmentValidationError("Invalid Word document.") from exc

    root = ElementTree.fromstring(xml_bytes)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", _DOCX_NS):
        runs = [
            node.text
            for node in paragraph.findall(".//w:t", _DOCX_NS)
            if node.text
        ]
        if runs:
            paragraphs.append("".join(runs))
    return "\n".join(paragraphs)


def _truncate_extracted(text: str) -> str:
    if len(text) <= MAX_EXTRACTED_CHARS_PER_FILE:
        return text
    return text[:MAX_EXTRACTED_CHARS_PER_FILE].rstrip() + "\n\n[Truncated]"


def detect_attachment_kind(
    data: bytes,
    *,
    filename: str,
) -> str:
    """Return one of: image, pdf, docx, text."""
    if not data:
        raise ChatAttachmentValidationError("Uploaded file is empty.")
    if len(data) > MAX_CHAT_ATTACHMENT_BYTES:
        raise ChatAttachmentValidationError("Each file must be 10 MB or smaller.")

    if sniff_image_content_type(data) is not None:
        return "image"

    if data.startswith(b"%PDF"):
        return "pdf"

    ext = extension_from_filename(filename)
    if ext == "docx" or data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if "word/document.xml" in archive.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            if ext == "docx":
                raise ChatAttachmentValidationError("Invalid Word document.") from None

    if ext in {"txt", "md", "markdown"} or _looks_like_utf8_text(data):
        return "text"

    raise ChatAttachmentValidationError(
        "Unsupported file type. Use PNG, JPEG, WebP, PDF, TXT, Markdown, or DOCX."
    )


def extract_attachment_text(
    data: bytes,
    *,
    filename: str,
    kind: str,
) -> str:
    if kind == "image":
        return ""

    if kind == "pdf":
        try:
            text = _extract_pdf_text(data)
        except Exception as exc:
            raise ChatAttachmentValidationError(
                "Could not read text from this PDF."
            ) from exc
    elif kind == "docx":
        text = _extract_docx_text(data)
    elif kind == "text":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ChatAttachmentValidationError(
                "Text files must be UTF-8 encoded."
            ) from exc
    else:
        raise ChatAttachmentValidationError("Unsupported file type.")

    text = text.strip()
    if not text and kind != "image":
        raise ChatAttachmentValidationError(
            "No readable text was found in this file."
        )
    return _truncate_extracted(text)
