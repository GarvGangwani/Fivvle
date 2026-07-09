"""Pydantic schemas for experiment category tags."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.llm.prompts.tag_generator import TAG_VOCABULARY

TagVocabulary = Annotated[
    str,
    Field(description="Category tag from the fixed Fivvle vocabulary."),
]


class TagGeneratorOutput(BaseModel):
    """Structured LLM output for tag_generator_v1."""

    model_config = ConfigDict(extra="forbid")

    tags: Annotated[
        list[TagVocabulary],
        Field(
            min_length=2,
            max_length=3,
            description="Two or three tags from the fixed vocabulary.",
        ),
    ]


class UpdateExperimentTagsRequest(BaseModel):
    """Body for PATCH /experiments/{id}/tags."""

    tags: Annotated[
        list[str],
        Field(min_length=1, max_length=3, description="1–3 tags from the vocabulary."),
    ]


class SearchResult(BaseModel):
    """Single row from GET /search."""

    id: str
    title: str
    snippet: str
    matched_field: str
    status: str
