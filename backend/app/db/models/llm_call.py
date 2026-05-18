"""SQLAlchemy model for the LLMCall table.

Audit table — every call through app.llm.client writes one row here.
experiment_id is nullable with SET NULL on delete: cost/audit data
survives even when the parent experiment is deleted.

Column relationship (prompt_tokens vs cache columns)
-------------------------------------------------
``prompt_tokens`` is **total** input tokens for the API call (backward-compatible
semantics for dashboards and rollups). When Anthropic prompt caching is used,
that total decomposes per the Messages API::

    prompt_tokens = uncached_tail_input_tokens
                    + cache_read_input_tokens
                    + cache_creation_input_tokens

where **uncached_tail_input_tokens** is the provider's ``usage.input_tokens``
field (tokens after the last cache breakpoint — *not* “plain input minus cache”).

Persisted names:
- ``cached_input_tokens`` ← ``usage.cache_read_input_tokens`` on the wire.
- ``cache_creation_input_tokens`` ← ``usage.cache_creation_input_tokens`` (writes).

When caching is **not** used (or for pre-migration rows), ``cached_input_tokens``
and ``cache_creation_input_tokens`` are **NULL**. Aggregations MUST use
``COALESCE(..., 0)`` (ADR 0014 / planning doc §15.1).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class LLMCall(Base):
    __tablename__ = "llm_calls"

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
    # Phase within the workflow, e.g. "refinement", "research_planner"
    phase: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    # Provider slug, e.g. "anthropic", "groq"
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    # Anthropic prompt caching (NULL = legacy / caching not in use for this row)
    cached_input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    # 6 decimal places — LLM costs are fractions of a cent
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=Decimal("0"),
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    # External request ID returned by the provider (for support / debugging)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment | None] = relationship(back_populates="llm_calls")
