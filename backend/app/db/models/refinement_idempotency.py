"""SQLAlchemy model for the RefinementIdempotency table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class RefinementIdempotency(Base):
    __tablename__ = "refinement_idempotency"
    __table_args__ = (
        PrimaryKeyConstraint("thread_id", "idempotency_key"),
        Index("idx_refinement_idempotency_created_at", "created_at"),
    )

    thread_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    response_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    experiment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment | None] = relationship()
