"""Pydantic schemas for original-idea capture and theme classification."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.idea_theme_palettes import THEME_PALETTE_NAMES, ThemePaletteName


class IdeaThemeOutput(BaseModel):
    """Structured LLM output for idea_theme_v2."""

    model_config = ConfigDict(extra="forbid")

    theme: Annotated[
        ThemePaletteName,
        Field(description=f"One of: {', '.join(THEME_PALETTE_NAMES)}."),
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
    #: AI-classified palette. Only a suggestion — the founder must accept it
    #: before it becomes the experiment's active `theme_palette`.
    suggested_palette: ThemePaletteName
    frozen_attachments: list[CaptureIdeaFrozenAttachment]
    user_message_id: UUID
