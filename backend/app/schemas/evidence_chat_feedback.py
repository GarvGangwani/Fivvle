"""Request/response schemas for evidence-chat message feedback.

Write-only: the founder rates an assistant reply thumbs up/down. Verdict is a
closed set — no free-text, no stars (per PR 5 decisions). One verdict per
message; the endpoint upserts.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvidenceChatFeedbackRequest(BaseModel):
    """POST body: the thumbs verdict for an assistant message."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["up", "down"]


class EvidenceChatFeedbackResponse(BaseModel):
    """POST response: the persisted (message_id, verdict)."""

    message_id: UUID
    verdict: Literal["up", "down"]
