"""SQLAlchemy model for the LaunchKit table.

Mirrors the ValidationReport editable-doc pattern: an immutable ``raw_report``
JSONB (the full assembled LaunchKit payload) plus a nullable ``edited_doc``
overlay the founder mutates via PATCH, versioned for optimistic concurrency.

``generated_at`` uses ``clock_timestamp()`` (not ``now()``) so regeneration
timestamps advance within a transaction — Evidence inherited ``func.now()``
which is transaction-stable; LaunchKit is a fresh table with no legacy rows, so
it does not repeat that mistake.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class LaunchKit(Base):
    __tablename__ = "launch_kits"

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
    # The landing page this kit was generated against. This FK is the true
    # invariant: "no launch kit without a landing page." unique=True enforces the
    # 1:1 with LandingPage; CASCADE clears the kit if the landing page is deleted.
    landing_page_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("landing_pages.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # Verbatim assembled LaunchKit payload (deterministic parts + LLM subset).
    # Immutable after generation; regeneration overwrites it wholesale.
    raw_report: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # --- Founder-editable overlay (mirrors Evidence editable-doc surface) ---
    # NULL until the first PATCH, then the merged founder-edited LaunchKit JSON.
    edited_doc: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Optimistic-concurrency counter. Starts at 1 on generation; bumped on every
    # successful PATCH and on regeneration.
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    # Set to now() on each successful PATCH; NULL until the first edit.
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # clock_timestamp() advances within a transaction (unlike now()), giving
    # regenerations a strictly-increasing, time-sortable stamp.
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("clock_timestamp()"),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="launch_kit")
