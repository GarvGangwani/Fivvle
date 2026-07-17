"""Request/response schemas for the Evidence chat surface.

Founder Q&A over a completed validation report. Reuses ChatMessageItem from
app.schemas.chat for message payloads — evidence chat is a flat thread, so the
tree fields (parent_message_id/sibling_*) simply carry their defaults.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import ChatMessageItem


class EvidenceChatSendRequest(BaseModel):
    """POST body for sending an evidence-chat message."""

    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, Field(min_length=1, max_length=4000)]
    # Verbatim text the founder highlighted in the report editor, if any. When
    # present it anchors the reply; when absent the service keyword-matches
    # findings against `message`.
    selection_text: Annotated[str, Field(max_length=4000)] | None = None
    # The q1-q7 question whose findings block encloses the selection.
    selection_question_id: Annotated[str, Field(pattern=r"^q[1-7]$")] | None = None


class EvidenceChatSendResponse(BaseModel):
    """POST response: the persisted user + assistant messages and the thread id."""

    user_message: ChatMessageItem
    assistant_message: ChatMessageItem
    thread_id: UUID


class EvidenceChatMessagesResponse(BaseModel):
    """GET response: full evidence-chat history (empty until first message)."""

    thread_id: UUID | None
    experiment_id: UUID
    messages: list[ChatMessageItem]
