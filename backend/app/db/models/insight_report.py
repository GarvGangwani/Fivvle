"""SQLAlchemy model for the InsightReport table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import InsightRecommendation

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class InsightReport(Base):
    __tablename__ = "insight_reports"

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
    traffic_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    conversion_by_source: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    research_takeaways: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_type: Mapped[InsightRecommendation | None] = mapped_column(
        SQLEnum(
            InsightRecommendation,
            name="insight_recommendation",
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    # Full InsightReportOutput Pydantic payload. Mirrors ValidationReport.raw_report
    # pattern: queryable scalar columns plus the full structured output for
    # frontend rendering and future schema evolution. Per planning doc §4.2.
    raw_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="insight_report")
