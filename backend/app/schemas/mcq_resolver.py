"""Schemas for rail-native MCQ free-text resolution."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class McqIndexResolution(BaseModel):
    """Lightweight structured map from founder prose → pending MCQ options."""

    model_config = ConfigDict(extra="forbid")

    selected_indices: Annotated[
        list[int],
        Field(
            default_factory=list,
            description=(
                "0-based indices into the pending MCQ options list. "
                "Empty list means ambiguous / no confident match — do not "
                "submit an MCQ answer turn."
            ),
        ),
    ]
