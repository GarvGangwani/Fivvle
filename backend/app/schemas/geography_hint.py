"""Pydantic schemas for geography hint LLM generation."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class GeographyHintDraft(BaseModel):
    """LLM-facing structured output for hint generation. Module-private-ish;
    exported for testability but not used outside the hint service."""

    model_config = ConfigDict(extra="forbid")

    include_domains: Annotated[
        list[Annotated[str, Field(min_length=3, max_length=100)]],
        Field(
            min_length=0,
            max_length=15,
            description=(
                "Domains (no scheme, no path — 'example.com' not 'https://example.com/foo') "
                "that publish authoritative or high-quality content specifically about "
                "the given geography. Prefer: national statistics offices, central banks, "
                "leading local business press, regulatory bodies, and top consumer/tech "
                "publications native to that geography. Exclude: US-first global outlets "
                "(e.g. nytimes.com, wsj.com, techcrunch.com) unless the geography IS the "
                "United States. Exclude aggregators (Wikipedia, Medium). Return an empty "
                "list if the geography is too vague, too broad ('global'), or the model "
                "has no confident local knowledge."
            ),
        ),
    ]
    rationale: Annotated[
        str,
        Field(
            min_length=0,
            max_length=400,
            description=(
                "One-to-two sentence explanation of the domain choices. Not shown to "
                "founders — audit/debug use only. Empty string is acceptable when "
                "include_domains is empty."
            ),
        ),
    ]
