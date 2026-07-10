"""Schemas for experiment canvas layout, resources, and activity stream."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CanvasNodeId = Literal[
    "spark",
    "refine",
    "evidence",
    "launch",
    "signal",
    "resources",
    "spark-expanded",
]
ResourceType = Literal["link", "doc", "image", "competitor", "other"]


class NodePosition(BaseModel):
    x: float
    y: float


class CanvasLayoutIn(BaseModel):
    node_positions: dict[CanvasNodeId, NodePosition]


class CanvasLayoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_id: str
    user_id: str
    node_positions: dict[CanvasNodeId, NodePosition]
    updated_at: datetime


class ResourceCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str | None = None
    note: str | None = None
    resource_type: ResourceType = "link"

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class ResourcePatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    url: str | None = None
    note: str | None = None
    resource_type: ResourceType | None = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    experiment_id: str
    user_id: str
    title: str
    url: str | None = None
    note: str | None = None
    resource_type: ResourceType
    created_at: datetime


class EventCreateIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    payload: dict = Field(default_factory=dict)


class ActivityItem(BaseModel):
    id: str
    event_type: str
    summary: str
    metadata: dict = Field(default_factory=dict)
    occurred_at: datetime
