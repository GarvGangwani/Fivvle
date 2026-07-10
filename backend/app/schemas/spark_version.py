"""Pydantic schemas for Spark version save / list endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SparkSaveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_idea: str = Field(max_length=2000)


class SparkVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    version_number: int
    raw_idea: str | None = None
    attachment_ids_snapshot: list[UUID] = Field(default_factory=list)
    created_at: datetime
