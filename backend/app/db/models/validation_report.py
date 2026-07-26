"""SQLAlchemy model for the ValidationReport table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, func, text
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
    # Verbatim ValidationReport Pydantic payload — full structured report in one
    # JSONB column.  Replaces the 9 legacy scalar JSONB columns dropped in B2.4.
    # NOT NULL: the service must supply a value; '{}' sentinel never reaches here.
    raw_report: Mapped[dict] = mapped_column(JSONB, nullable=False)
    spark_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiment_spark_versions.id"),
        nullable=True,
    )
    refined_idea_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Kept scalar columns (queryable aggregates, populated in B3) ---
    # clarity_score: B3 synthesizer prompt will output this; B2.4 writes NULL.
    clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # reflection_loops_used: B3 reflector will populate this; B2.4 writes 0.
    reflection_loops_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    # generated_at: audit timestamp retained across all schema versions.
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Founder-editable overlay (Evidence editable-doc surface) ---
    # raw_report stays immutable; edited_doc is a separate ProseMirror-doc JSON
    # blob the founder edits. NULL until the first PATCH, at which point the
    # server-rendered doc is persisted and versioned. See
    # app/services/validation_report_editor.py.
    edited_doc: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Optimistic-concurrency counter. 0 for never-edited rows (server default
    # backfills existing rows); incremented on every successful PATCH.
    edited_doc_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    # Set to now() on each successful PATCH. Compared against generated_at to
    # detect edits made before a research regeneration (staleness signal).
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="validation_report")
