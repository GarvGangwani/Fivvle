"""Request/response schemas for the universal chat surface.

Canvas-wide coach / future agent. Isolated thread via experiments.universal_thread_id.
Reuses ChatMessageItem from app.schemas.chat (including optional tool_payload).
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.chat import ChatMessageItem

UniversalOpenPhase = Literal["refine", "evidence", "launch", "signal"]


class UniversalMcqAnswer(BaseModel):
    """Structured MCQ click or skip from the master rail."""

    model_config = ConfigDict(extra="forbid")

    selected_option_indices: Annotated[
        list[int],
        Field(default_factory=list, max_length=8),
    ]
    answered_question_id: UUID
    # When true, founder dismissed the question — proceed without an option.
    skipped: bool = False

    @model_validator(mode="after")
    def _require_indices_unless_skipped(self) -> "UniversalMcqAnswer":
        if self.skipped:
            return self
        if len(self.selected_option_indices) < 1:
            raise ValueError(
                "selected_option_indices must be non-empty unless skipped=true"
            )
        return self


class UniversalChatSendRequest(BaseModel):
    """POST body for sending a universal-chat message."""

    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, Field(default="", max_length=4000)]
    # Resolved via POST /chat/attachments → extract-to-text injection.
    attachment_ids: Annotated[
        list[UUID],
        Field(default_factory=list, max_length=5),
    ]
    # Canvas overlay act currently open in the client (or null when closed).
    current_open_phase: UniversalOpenPhase | None = None
    # Exact MCQ click from the rail. When set, refine executor skips the
    # free-text resolver and submits selected_option_indices directly.
    mcq_answer: UniversalMcqAnswer | None = None
    # Message edit: fork a sibling of this USER row (same parent). History for
    # the LLM is the branch up to that parent; the new USER row becomes the
    # active leaf so prior subsequent turns drop off the active branch.
    replace_message_id: UUID | None = None
    # Agent-initiated kick after idea capture — no new USER bubble; forces refine.
    kick: Literal["post_capture_refine"] | None = None

    @model_validator(mode="after")
    def _require_message_or_attachments(self) -> "UniversalChatSendRequest":
        if self.kick is not None:
            return self
        if self.mcq_answer is not None:
            return self
        if not self.message.strip() and not self.attachment_ids:
            raise ValueError("message or attachment_ids is required")
        return self

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
    # Present when metadata_json.turn_status == running on the active branch.
    in_progress_turn_id: UUID | None = None


class UniversalChatCancelRequest(BaseModel):
    """POST body for explicit stop of a durable universal-chat turn."""

    model_config = ConfigDict(extra="forbid")

    turn_id: UUID
