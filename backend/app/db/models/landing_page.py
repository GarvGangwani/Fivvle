"""SQLAlchemy model for the LandingPage table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import LandingCtaType, LandingDensity

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class LandingPage(Base):
    __tablename__ = "landing_pages"

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
    # Template and style identifiers — e.g. "minimal", "vibrant"
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)
    palette_id: Mapped[str] = mapped_column(String(50), nullable=False)
    font_pair_id: Mapped[str] = mapped_column(String(50), nullable=False)
    density: Mapped[LandingDensity] = mapped_column(
        SQLEnum(
            LandingDensity,
            name="landing_density",
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=LandingDensity.ROOMY,
    )
    enabled_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Hero copy
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    subheadline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    problem_desc: Mapped[str] = mapped_column(Text, nullable=False)
    solution_desc: Mapped[str] = mapped_column(Text, nullable=False)
    cta_text: Mapped[str] = mapped_column(String(100), nullable=False)
    cta_type: Mapped[LandingCtaType] = mapped_column(
        SQLEnum(
            LandingCtaType,
            name="landing_cta_type",
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=LandingCtaType.WAITLIST,
    )

    # Optional sections — structure validated at Pydantic layer
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    how_it_works: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    faq: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    founder_bio: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    copy_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    page_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Public URL slug — pattern ^[a-z0-9-]{6,40}$ enforced at Pydantic layer
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Publishing lifecycle timestamps — null until the relevant event occurs
    live_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_revalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    spark_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiment_spark_versions.id"),
        nullable=True,
    )
    refined_idea_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="landing_page")
