"""Pydantic models for POST /chat/turn (planning §7.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.enums import ChatTurnKind, ExperimentStatus
from app.services.chat_service import ChatTurnResult


class ChatTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: UUID | None = None
    experiment_id: UUID | None = None
    message: Annotated[str, Field(min_length=1, max_length=4000)]
    deep_research: bool
    idempotency_key: Annotated[str, Field(min_length=1, max_length=200)] | None = None

    @model_validator(mode="after")
    def _check_idempotency_required(self) -> ChatTurnRequest:
        if self.deep_research and self.idempotency_key is None:
            raise ValueError("idempotency_key is required when deep_research=true")
        return self


class ChatTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    thread_id: UUID
    message_id: UUID
    experiment_id: UUID | None
    assistant_message: str
    turn_kind: ChatTurnKind
    clarifying_dimension: str | None
    pipeline_dispatched: bool
    dispatched_at: datetime | None
    experiment_status: ExperimentStatus | None
    research_error_detail: str | None

    @classmethod
    def from_result(cls, result: ChatTurnResult) -> ChatTurnResponse:
        return cls(
            thread_id=result.thread_id,
            message_id=result.message_id,
            experiment_id=result.experiment_id,
            assistant_message=result.assistant_message,
            turn_kind=result.turn_kind,
            clarifying_dimension=result.clarifying_dimension,
            pipeline_dispatched=result.pipeline_dispatched,
            dispatched_at=result.dispatched_at,
            experiment_status=result.experiment_status,
            research_error_detail=result.research_error_detail,
        )
