"""SQLAlchemy model for the PageView table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class PageView(Base):
    __tablename__ = "page_views"

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
    # Indexed for per-source analytics queries (conversion rate by source tag)
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
    time_on_page_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # INET supports both IPv4 and IPv6; nullable for privacy-respecting clients
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="page_views")
