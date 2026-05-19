"""Pydantic schemas for multi-source Searcher output (ADR 0015).

Trends numeric series and merged per-source bundles live here.
TavilyResult remains on the Tavily integration module (same pattern as today).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.integrations.tavily import TavilyResult


class TrendsPoint(BaseModel):
    """Single interest-over-time observation for one keyword."""

    model_config = ConfigDict(extra="forbid")

    date: Annotated[
        str,
        Field(
            min_length=10,
            max_length=10,
            description="ISO date (YYYY-MM-DD) for this observation.",
        ),
    ]
    value: Annotated[
        int,
        Field(
            ge=0,
            le=100,
            description="Google Trends relative interest score (0–100).",
        ),
    ]


class TrendsSeries(BaseModel):
    """Interest-over-time series for one keyword."""

    model_config = ConfigDict(extra="forbid")

    keyword: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Keyword phrase used for this Trends pull.",
        ),
    ]
    points: Annotated[
        list[TrendsPoint],
        Field(
            min_length=0,
            max_length=520,
            description="Time-ordered interest points (initial cap; calibrate later).",
        ),
    ]


class MergedSearchResults(BaseModel):
    """Per-source Searcher output keyed by provenance (ADR 0015)."""

    model_config = ConfigDict(extra="forbid")

    tavily: dict[str, list[TavilyResult]]
    trends: dict[str, TrendsSeries] | None = None


# Import after Trends* / MergedSearchResults are defined so integrations.trends
# can load this module without a circular import (see integrations/__init__.py).
from app.integrations.tavily import TavilyResult  # noqa: E402

MergedSearchResults.model_rebuild()
