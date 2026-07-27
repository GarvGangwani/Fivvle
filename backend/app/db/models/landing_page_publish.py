"""SQLAlchemy model for LandingPagePublish (Signal analytics cohorts)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.landing_page import LandingPage
    from app.db.models.page_view import PageView
    from app.db.models.waitlist_signup import WaitlistSignup


class LandingPagePublish(Base):
    __tablename__ = "landing_page_publishes"
    __table_args__ = (
        UniqueConstraint(
            "landing_page_id",
            "publish_number",
            name="uq_landing_page_publishes_landing_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    landing_page_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("landing_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publish_number: Mapped[int] = mapped_column(Integer, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("clock_timestamp()"),
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Relationships ---
    landing_page: Mapped[LandingPage] = relationship(back_populates="publishes")
    page_views: Mapped[list[PageView]] = relationship(back_populates="publish")
    waitlist_signups: Mapped[list[WaitlistSignup]] = relationship(
        back_populates="publish",
    )
