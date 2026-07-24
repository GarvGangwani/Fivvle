"""SQLAlchemy model for the ChatMessage table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ChatRole, ChatTurnKind

if TYPE_CHECKING:
    from app.db.models.chat_thread import ChatThread
    from app.db.models.experiment import Experiment


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_messages_thread_id", "thread_id", "created_at"),
        Index("idx_chat_messages_experiment_id", "experiment_id"),
        Index("ix_chat_messages_parent", "parent_message_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ChatRole] = mapped_column(
        SQLEnum(
            ChatRole,
            name="chat_role",
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    experiment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
    )
    turn_kind: Mapped[ChatTurnKind | None] = mapped_column(
        SQLEnum(
            ChatTurnKind,
            name="chat_turn_kind",
            native_enum=False,
            length=40,
        ),
        nullable=True,
    )
    clarifying_dimension: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )
    clarifying_questions: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Structured payload for tool_call / tool_result roles (agent surfaces).
    # Expected shapes when tools land (application-enforced, not DB-checked):
    #   tool_call:   { "tool_name": str, "arguments": dict }
    #   tool_result: { "tool_name": str, "result": any, "error"?: str }
    # ``content`` for tool rows is a short human-readable label
    # (e.g. "Called: <tool_name>" / "Result received"), not empty.
    #
    # Tool-row branching semantics (future):
    # Tool rows (tool_call, tool_result) are always linear children in the
    # message tree. They MUST NOT have sibling groups. If assistant-message
    # branching is added later (edit/regenerate on the assistant turn after a
    # tool exchange), the branching MUST treat the whole
    # assistant → tool_call → tool_result → assistant sequence as one atomic
    # unit — regenerating the leading assistant message re-runs the tool
    # sequence; it does not fork tool_calls into siblings.
    tool_payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    parent_message_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("clock_timestamp()"),
        nullable=False,
    )

    # --- Relationships ---
    thread: Mapped[ChatThread] = relationship(
        back_populates="messages",
        foreign_keys=[thread_id],
    )
    experiment: Mapped[Experiment | None] = relationship()
    parent: Mapped[ChatMessage | None] = relationship(
        "ChatMessage",
        remote_side="ChatMessage.id",
        back_populates="children",
        foreign_keys=[parent_message_id],
    )
    children: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="parent",
        foreign_keys=[parent_message_id],
    )
