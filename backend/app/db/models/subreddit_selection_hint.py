"""Cache of LLM-selected subreddits per topic+geography.

Mirrors GeographySourceHint pattern: keyed on normalized {topic, geography}
hash, values are the LLM-picked subreddit names. Cache never expires
automatically — manual invalidation via admin script (deferred). See
geography_hint_service.py for the reference pattern.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SubredditSelectionHint(Base):
    __tablename__ = "subreddit_selection_hints"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    normalized_key: Mapped[str] = mapped_column(
        String(400), unique=True, nullable=False, index=True,
    )
    original_topic: Mapped[str] = mapped_column(String(300), nullable=False)
    original_geography: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    subreddits: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False,
    )
