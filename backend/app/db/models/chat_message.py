"""SQLAlchemy model for the ChatMessage table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    thread: Mapped[ChatThread] = relationship(back_populates="messages")
    experiment: Mapped[Experiment | None] = relationship()
