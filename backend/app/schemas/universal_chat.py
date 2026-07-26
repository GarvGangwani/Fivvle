"""Request/response schemas for the universal chat surface.

Canvas-wide coach / future agent. Isolated thread via experiments.universal_thread_id.
Reuses ChatMessageItem from app.schemas.chat (including optional tool_payload).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import ChatMessageItem


class UniversalChatSendRequest(BaseModel):
    """POST body for sending a universal-chat message."""

    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, Field(min_length=1, max_length=4000)]
    # Accepted for API shape parity with POST /chat/turn. v1 does not process
    # attachments (dock UI ships attach disabled). Reserved for a later PR.
    attachment_ids: Annotated[
        list[UUID],
        Field(default_factory=list, max_length=5),
    ]


class UniversalChatSendResponse(BaseModel):
    """POST response: all rows created this turn (user → tools → assistant)."""

    user_message: ChatMessageItem
    assistant_message: ChatMessageItem
    # Ordered rows for this turn so the dock can render tool chips without refetch.
    messages: list[ChatMessageItem]
    thread_id: UUID


class UniversalChatMessagesResponse(BaseModel):
    """GET response: linear active-branch messages for the universal thread."""

    thread_id: UUID | None
    experiment_id: UUID
    active_leaf_message_id: UUID | None
    messages: list[ChatMessageItem]
