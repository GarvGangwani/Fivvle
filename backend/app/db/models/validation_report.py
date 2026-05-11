"""SQLAlchemy model for the ValidationReport table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class ValidationReport(Base):
    __tablename__ = "validation_reports"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # unique=True enforces the 1:1 constraint with Experiment at the DB level.
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    research_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    findings_per_question: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    competitors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reddit_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_trends: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    news_signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    citations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    market_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection_loops_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="validation_report")
