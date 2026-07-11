"""Pydantic models for POST /chat/turn (planning §7.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.enums import ChatRole, ChatTurnKind, ExperimentStatus
from app.schemas.refinement import ClarifyingQuestion
from app.services.chat_service import ChatTurnResult


class ChatTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: UUID | None = None
    experiment_id: UUID | None = None
    message: Annotated[str, Field(default="", max_length=4000)]
    attachment_ids: Annotated[
        list[UUID],
        Field(default_factory=list, max_length=5),
    ]
    name: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Optional project name when starting a new experiment via chat.",
        ),
    ] = None
    deep_research: bool
    idempotency_key: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    selected_option_indices: list[int] | None = None
    custom_added_text: Annotated[str | None, Field(default=None, max_length=2000)] = None
    answered_question_from_message_id: UUID | None = None

    @model_validator(mode="after")
    def _check_turn_payload(self) -> ChatTurnRequest:
        if self.deep_research and self.idempotency_key is None:
            raise ValueError("idempotency_key is required when deep_research=true")
        if not self.message.strip() and not self.attachment_ids:
            raise ValueError("message or attachment_ids is required")
        return self


class ChatAttachmentUploadItem(BaseModel):
    id: UUID
    filename: str
    content_kind: str
    excerpt: str
    char_count: int


class ChatAttachmentsUploadResponse(BaseModel):
    attachments: list[ChatAttachmentUploadItem]


class ChatTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    thread_id: UUID
    message_id: UUID
    experiment_id: UUID | None
    assistant_message: str
    turn_kind: ChatTurnKind
    clarifying_dimension: str | None
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    pipeline_dispatched: bool
    dispatched_at: datetime | None
    experiment_status: ExperimentStatus | None
    research_error_detail: str | None
    refinement_count: int | None = None

    @classmethod
    def from_result(cls, result: ChatTurnResult) -> ChatTurnResponse:
        return cls(
            thread_id=result.thread_id,
            message_id=result.message_id,
            experiment_id=result.experiment_id,
            assistant_message=result.assistant_message,
            turn_kind=result.turn_kind,
            clarifying_dimension=result.clarifying_dimension,
            clarifying_questions=list(result.clarifying_questions),
            pipeline_dispatched=result.pipeline_dispatched,
            dispatched_at=result.dispatched_at,
            experiment_status=result.experiment_status,
            research_error_detail=result.research_error_detail,
            refinement_count=result.refinement_count,
        )


class ChatMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: ChatRole
    content: str
    turn_kind: ChatTurnKind | None
    clarifying_questions: list[ClarifyingQuestion] | None = None
    metadata: dict | None = None
    parent_message_id: UUID | None = None
    sibling_count: int = 1
    sibling_index: int = 0
    created_at: datetime

    @classmethod
    def from_orm_message(
        cls,
        message: object,
        *,
        sibling_count: int = 1,
        sibling_index: int = 0,
    ) -> ChatMessageItem:
        """Map ORM ChatMessage → API item (metadata_json → metadata)."""
        cq_raw = getattr(message, "clarifying_questions", None)
        clarifying: list[ClarifyingQuestion] | None = None
        if cq_raw:
            clarifying = [ClarifyingQuestion.model_validate(item) for item in cq_raw]
        return cls(
            id=getattr(message, "id"),
            role=getattr(message, "role"),
            content=getattr(message, "content"),
            turn_kind=getattr(message, "turn_kind", None),
            clarifying_questions=clarifying,
            metadata=getattr(message, "metadata_json", None),
            parent_message_id=getattr(message, "parent_message_id", None),
            sibling_count=sibling_count,
            sibling_index=sibling_index,
            created_at=getattr(message, "created_at"),
        )


class ExperimentChatMessagesResponse(BaseModel):
    thread_id: UUID | None
    experiment_id: UUID
    messages: list[ChatMessageItem]


class ChatEditTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: UUID
    message_id: UUID
    new_content: Annotated[str, Field(min_length=1, max_length=4000)]


class ChatEditTurnResponse(BaseModel):
    thread_id: UUID
    edited_message_id: UUID
    message_id: UUID
    experiment_id: UUID | None
    assistant_message: str
    turn_kind: ChatTurnKind
    clarifying_dimension: str | None
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    pipeline_dispatched: bool
    dispatched_at: datetime | None
    experiment_status: ExperimentStatus | None
    research_error_detail: str | None
    messages: list[ChatMessageItem]
