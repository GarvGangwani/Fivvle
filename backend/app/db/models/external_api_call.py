"""SQLAlchemy model for the ExternalAPICall table.

Audit table — every call through app.integrations.* writes one row here.
experiment_id is nullable with SET NULL on delete: cost/audit data
survives even when the parent experiment is deleted.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class ExternalAPICall(Base):
    __tablename__ = "external_api_calls"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # Nullable FK with SET NULL — audit record survives experiment deletion
    experiment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Provider slug, e.g. "tavily", "reddit", "pytrends"
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # Product-level rollup bucket — see app.cost.category.CostCategory
    cost_category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="platform",
        server_default="platform",
        index=True,
    )
    # Operation name, e.g. "search", "fetch_post"
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    # 6 decimal places — consistent with LLMCall; some external APIs charge per-call
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=Decimal("0"),
    )
    # Provider-reported credits when available (Tavily usage.credits).
    api_credits: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment | None] = relationship(
        back_populates="external_api_calls"
    )
