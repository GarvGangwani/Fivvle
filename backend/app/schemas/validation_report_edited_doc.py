"""Request/response schemas for the founder-editable validation-report doc.

The editable-doc surface exposes a ProseMirror-doc JSON view of a
ValidationReport. `raw_report` remains the immutable source of truth; the
`edited_doc` overlay is what the founder edits. See
`app/services/validation_report_editor.py` for the rendering and CAS logic.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EditedDocResponse(BaseModel):
    """Response for GET/PATCH edited-doc.

    - doc: the ProseMirror-doc JSON. Either the deterministic server render of
      raw_report (source="generated") or the persisted overlay (source="persisted").
    - version: the current edited_doc_version. 0 until the first successful PATCH.
    - source: whether `doc` came from a live render or the persisted overlay.
    - edited_doc_behind_regeneration: True when a persisted edit predates the most
      recent research regeneration (edited_at < generated_at). Always False for
      "generated" responses.
    """

    model_config = ConfigDict(extra="forbid")

    doc: dict[str, Any]
    version: int
    source: Literal["generated", "persisted"]
    edited_doc_behind_regeneration: bool


class EditedDocPatchRequest(BaseModel):
    """PATCH body: the new doc plus the version the client is editing against.

    base_version implements optimistic concurrency (compare-and-swap): the
    server accepts the write only when base_version equals the row's current
    edited_doc_version. A first edit uses base_version=0.
    """

    model_config = ConfigDict(extra="forbid")

    doc: dict[str, Any] = Field(
        description="The full ProseMirror-doc JSON to persist as the edited overlay.",
    )
    base_version: int = Field(
        ge=0,
        description=(
            "The edited_doc_version the client last read. Must equal the row's "
            "current version or the PATCH is rejected with 409. Use 0 for the first edit."
        ),
    )
