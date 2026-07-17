"""SQLAlchemy model for the EvidenceChatFeedback table.

Write-only observability: one thumbs up/down per assistant evidence-chat message.
There is no GET endpoint — the row exists purely so we can measure reply quality.
UNIQUE on message_id enforces one verdict per message (the endpoint upserts).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvidenceChatFeedback(Base):
    __tablename__ = "evidence_chat_feedback"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('up','down')",
            name="ck_evidence_chat_feedback_verdict",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # One feedback row per assistant message (UNIQUE). ON DELETE CASCADE: feedback
    # disappears with the message it rates.
    message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    verdict: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
