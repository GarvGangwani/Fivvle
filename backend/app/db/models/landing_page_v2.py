"""Experimental landing page runtime V2 — spec stored separately from V1."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class LandingPageV2Spec(Base):
    """Structured page specification for the V2 runtime (isolated from V1 rows)."""

    __tablename__ = "landing_page_v2_specs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    spec_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="idle",
    )
    generation_phase: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default="idle",
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cascade stamps — mirror LandingPage (v1). NULL = pre-dimension / not-stale.
    spark_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiment_spark_versions.id"),
        nullable=True,
    )
    refined_idea_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edited_doc_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    experiment: Mapped[Experiment] = relationship(back_populates="landing_page_v2")
