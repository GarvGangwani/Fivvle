"""Pydantic schemas for the LaunchKit artifact (Launch phase, PR 1).

A LaunchKit is a small structured launch package that lives beside a
LandingPage. It answers the founder's "okay, it validated — now what do I
actually do to launch?" question with four parts:

- ``first_channel`` + ``first_channel_rationale`` — a deterministic channel pick
  (Python rule) explained by the LLM in one or two sentences.
- ``first_cohort_hint`` — a deterministic, geography-aware sentence naming the
  first ~10 people to reach (Python rule).
- ``share_copy_variants`` — 3-5 ready-to-post copy blocks (LLM-written,
  geography-aware, one per surface).
- ``readiness_checklist`` — a fixed 5-item pre-launch checklist (Python).

Only ``first_channel_rationale`` + ``share_copy_variants`` come from the LLM
(see ``LaunchKitLLMOutput``); everything else is assembled deterministically in
``app/services/launch_kit_service.py``.

The persisted DB shape mirrors the Evidence editable-doc pattern: an immutable
``raw_report`` plus a nullable ``edited_doc``, versioned for optimistic
concurrency. The ``LaunchKit`` model here is the schema-pure artifact; the API
envelopes it with a ``version`` field (see the router response models).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LaunchChannel(StrEnum):
    """The single best first place a founder should launch."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    HACKERNEWS = "hackernews"
    PRODUCT_HUNT = "product_hunt"
    DM_CHAIN = "dm_chain"
    NEWSLETTER = "newsletter"
    COMMUNITY_SLACK = "community_slack"
    OTHER = "other"


class ShareSurface(StrEnum):
    """The concrete format a share-copy variant is written for.

    The picked ``first_channel`` is a strong hint to the LLM for which surfaces
    to write; there is deliberately no strict channel→surface table (see PR 1
    sign-off). The LLM selects surfaces appropriate to the channel.
    """

    TWEET = "tweet"
    REDDIT_POST = "reddit_post"
    DM_OPENER = "dm_opener"
    LINKEDIN_POST = "linkedin_post"
    HACKERNEWS_SHOW = "hackernews_show"


class ShareCopyVariant(BaseModel):
    """One ready-to-post copy block for a specific surface."""

    model_config = ConfigDict(extra="forbid")

    surface: ShareSurface
    text: str = Field(min_length=1, max_length=1200)
    # Founder-facing regen budget lives on each variant; bumped on regenerate.
    regenerated_count: int = Field(default=0, ge=0)


class ReadinessItem(BaseModel):
    """One pre-launch checklist item. ``checked_at`` is null until ticked."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=140)
    checked_at: datetime | None = None


class LaunchKit(BaseModel):
    """The full, schema-pure LaunchKit artifact.

    This is what GET/PATCH return inside an envelope. ``raw_report`` carries the
    immutable LLM-emitted subset for audit/regeneration parity with Evidence.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    landing_page_id: UUID
    first_channel: LaunchChannel
    first_channel_rationale: str = Field(min_length=1, max_length=280)
    first_cohort_hint: str = Field(min_length=1, max_length=500)
    share_copy_variants: list[ShareCopyVariant] = Field(min_length=3, max_length=5)
    readiness_checklist: list[ReadinessItem] = Field(min_length=4, max_length=6)
    generated_at: datetime
    founder_edited: bool = False
    raw_report: dict


class LaunchKitLLMOutput(BaseModel):
    """The subset of a LaunchKit the LLM produces (launch_kit_v1 prompt).

    The deterministic parts (channel pick, cohort hint, checklist) are assembled
    in Python and never come from the model.
    """

    model_config = ConfigDict(extra="forbid")

    first_channel_rationale: str = Field(min_length=1, max_length=280)
    share_copy_variants: list[ShareCopyVariant] = Field(min_length=3, max_length=5)


# --- API request/response envelopes ---------------------------------------


class LaunchKitGenerateResponse(BaseModel):
    """202 response for POST /generate-launch-kit."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: UUID
    generation_started: bool


class LaunchKitEnvelope(BaseModel):
    """GET/PATCH response: the artifact plus its optimistic-concurrency version."""

    model_config = ConfigDict(extra="forbid")

    launch_kit: LaunchKit
    version: int = Field(ge=1)


class ShareCopyVariantPatch(BaseModel):
    """Edit the text of a single share-copy variant, addressed by list index."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=1200)


class ReadinessItemPatch(BaseModel):
    """Tick/untick a single checklist item, addressed by its stable id."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    checked_at: datetime | None = None


class LaunchKitPatch(BaseModel):
    """The set of founder-editable fields. All optional; only provided keys apply."""

    model_config = ConfigDict(extra="forbid")

    first_channel: LaunchChannel | None = None
    first_channel_rationale: str | None = Field(default=None, min_length=1, max_length=280)
    first_cohort_hint: str | None = Field(default=None, min_length=1, max_length=500)
    share_copy_variants: list[ShareCopyVariantPatch] | None = None
    readiness_checklist: list[ReadinessItemPatch] | None = None


class LaunchKitPatchRequest(BaseModel):
    """PATCH /launch-kit body: CAS ``version`` + the fields to change."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    patch: LaunchKitPatch


class LaunchKitRegenRequest(BaseModel):
    """POST /launch-kit/regenerate-variant body.

    Server-side version bump only — no client ``version``. The click is atomic;
    CAS is for concurrent PATCH races, not regen.
    """

    model_config = ConfigDict(extra="forbid")

    surface: ShareSurface


class LaunchKitRegenLLMOutput(BaseModel):
    """Single-variant output from ``launch_kit_regen_v1``."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1200)
