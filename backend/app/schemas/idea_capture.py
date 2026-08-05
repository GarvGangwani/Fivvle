"""Pydantic schemas for original-idea capture and theme classification."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

IdeaTheme = Literal["violet", "pink", "green", "orange"]


class IdeaThemeOutput(BaseModel):
    """Structured LLM output for idea_theme_v1."""

    model_config = ConfigDict(extra="forbid")

    theme: Annotated[
        IdeaTheme,
        Field(description="One of: violet, pink, green, orange."),
    ]


class OriginFrozenAttachment(BaseModel):
    """Frozen chat attachment surfaced on experiment detail / artifact."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    original_filename: str
    content_kind: str
    media_type: str | None = None
    created_at: datetime


class CaptureIdeaRequest(BaseModel):
    """Body for POST /experiments/{id}/capture-idea."""

    model_config = ConfigDict(extra="forbid")

    idea_text: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description="Founder's original idea text to freeze forever.",
        ),
    ]
    attachment_ids: Annotated[
        list[UUID],
        Field(
            default_factory=list,
            max_length=20,
            description="Chat attachment ids to freeze as origin artifacts.",
        ),
    ]


class CaptureIdeaFrozenAttachment(BaseModel):
    """Minimal ref for an attachment frozen at capture."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    original_filename: str
    content_kind: str


class CaptureIdeaResponse(BaseModel):
    """Captured original-idea state."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: UUID
    original_idea: str
    original_idea_captured_at: datetime
    idea_theme: IdeaTheme
    frozen_attachments: list[CaptureIdeaFrozenAttachment]
    confirmation_message: str
