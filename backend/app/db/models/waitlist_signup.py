"""SQLAlchemy model for the WaitlistSignup table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NOT unique — one person can sign up for multiple experiments
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    # Indexed for per-source conversion analytics
    source_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="waitlist_signups")
