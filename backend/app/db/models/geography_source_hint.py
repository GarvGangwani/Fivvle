"""SQLAlchemy model for geography → Tavily include_domains cache rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeographySourceHint(Base):
    """Lazy LLM-generated Tavily domain hints keyed by normalized geography."""

    __tablename__ = "geography_source_hints"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    normalized_key: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )
    original_geography: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    include_domains: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
