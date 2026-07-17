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


class SiblingInfo(BaseModel):
    """Position of a message within its sibling group (same parent).

    ``sibling_ids`` is the ordered (oldest→newest) list of message ids in the
    group, so the client can activate a specific sibling by id.
    """

    sibling_index: int
    sibling_count: int
    sibling_ids: list[UUID] = Field(default_factory=list)


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
    # Branch parent. None → backend uses the current active leaf (or None for the
    # first turn). When provided, it must be an evidence-chat message in the thread.
    parent_message_id: UUID | None = None


class EvidenceChatSendResponse(BaseModel):
    """POST response: the persisted user + assistant messages and the thread id."""

    user_message: ChatMessageItem
    assistant_message: ChatMessageItem
    thread_id: UUID


class EvidenceChatMessagesResponse(BaseModel):
    """GET response: the active branch (root→leaf) + sibling metadata.

    ``messages`` is the currently active branch only; ``sibling_info`` maps a
    message id to its position within its sibling group, for branch navigation.
    """

    thread_id: UUID | None
    experiment_id: UUID
    active_leaf_message_id: UUID | None
    messages: list[ChatMessageItem]
    sibling_info: dict[str, SiblingInfo] = Field(default_factory=dict)


class EvidenceChatEditRequest(BaseModel):
    """POST body for editing a user message (creates a new sibling branch)."""

    model_config = ConfigDict(extra="forbid")

    content: Annotated[str, Field(min_length=1, max_length=4000)]
    selection_text: Annotated[str, Field(max_length=4000)] | None = None
    selection_question_id: Annotated[str, Field(pattern=r"^q[1-7]$")] | None = None


class EvidenceChatEditResponse(BaseModel):
    """POST response: the new user + assistant branch and its sibling metadata."""

    new_user_message: ChatMessageItem
    new_assistant_message: ChatMessageItem
    thread_id: UUID
    active_leaf_message_id: UUID
    sibling_info: dict[str, SiblingInfo] = Field(default_factory=dict)


class EvidenceChatActivateResponse(BaseModel):
    """POST response: the resolved active leaf after switching branches."""

    thread_id: UUID
    active_leaf_message_id: UUID


class EvidenceChatRegenerateRequest(BaseModel):
    """POST body for regenerating an assistant reply.

    Same shape as EvidenceChatSendRequest minus `message` — the parent user
    message supplies the question; only the selection anchor may change.
    """

    model_config = ConfigDict(extra="forbid")

    selection_text: Annotated[str, Field(max_length=4000)] | None = None
    selection_question_id: Annotated[str, Field(pattern=r"^q[1-7]$")] | None = None


class EvidenceChatRegenerateResponse(BaseModel):
    """POST response: the new assistant message (the user message is unchanged)."""

    assistant_message: ChatMessageItem
    thread_id: UUID
