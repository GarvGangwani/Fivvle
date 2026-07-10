"""Schemas for experiment Spark-phase attachments and upload signing."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AttachmentType = Literal[
    "image",
    "document",
    "pdf",
    "markdown",
    "pasted_text",
    "link",
]

TEXT_ATTACHMENT_TYPES: frozenset[str] = frozenset({"pasted_text", "markdown"})
FILE_ATTACHMENT_TYPES: frozenset[str] = frozenset({"image", "document", "pdf"})
LINK_ATTACHMENT_TYPES: frozenset[str] = frozenset({"link"})

ALLOWED_UPLOAD_MIMES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "application/pdf",
        "text/markdown",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


class AttachmentCreateIn(BaseModel):
    attachment_type: AttachmentType
    title: str = Field(min_length=1, max_length=500)
    content_text: str | None = None
    file_url: str | None = None
    file_mime: str | None = Field(default=None, max_length=100)
    file_size_bytes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_type_payload(self) -> AttachmentCreateIn:
        title = self.title.strip()
        if not title:
            raise ValueError("title is required")
        self.title = title

        if self.attachment_type in TEXT_ATTACHMENT_TYPES:
            if not (self.content_text and self.content_text.strip()):
                raise ValueError(
                    f"{self.attachment_type} attachments require content_text"
                )
            if self.file_url:
                raise ValueError(
                    f"{self.attachment_type} attachments must not include file_url"
                )
            self.content_text = self.content_text.strip()
            self.file_url = None
            self.file_mime = None
            self.file_size_bytes = None
            return self

        if self.attachment_type == "link":
            if not self.file_url or not self.file_url.strip():
                raise ValueError("link attachments require file_url")
            url = self.file_url.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("link file_url must be an http(s) URL")
            if self.content_text:
                raise ValueError("link attachments must not include content_text")
            self.file_url = url
            self.content_text = None
            self.file_mime = None
            self.file_size_bytes = None
            return self

        if not self.file_url or not self.file_url.strip():
            raise ValueError(f"{self.attachment_type} attachments require file_url")
        self.file_url = self.file_url.strip()
        if self.attachment_type != "markdown":
            self.content_text = None
        return self


class AttachmentPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content_text: str | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    user_id: UUID
    attachment_type: AttachmentType
    title: str
    content_text: str | None = None
    file_url: str | None = None
    file_mime: str | None = None
    file_size_bytes: int | None = None
    created_at: datetime


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=1, le=MAX_ATTACHMENT_BYTES)


class UploadUrlResponse(BaseModel):
    upload_url: str
    file_url: str
    expires_at: datetime
