"""LaunchKit service — deterministic assembly + one LLM call (Launch phase, PR 1).

Public surface:
  - generate_launch_kit(db, experiment_id) -> LaunchKit
        Orchestrates: fetch context → pick channel (Python) → LLM call for
        rationale + share copy → assemble deterministic parts → persist
        (insert or regenerate) → return the assembled LaunchKit.
  - get_launch_kit(db, experiment_id) -> LaunchKitEnvelope | None
  - patch_launch_kit(db, experiment_id, expected_version, patch) -> LaunchKitEnvelope
  - regenerate_variant(db, experiment_id, surface) -> LaunchKitEnvelope
        LLM rewrite of one share-copy surface into edited_doc; server bumps
        version (no client CAS). Never mutates raw_report.

Deterministic helpers (pure, unit-testable, no I/O):
  - pick_first_channel(refined_idea, validation_report) -> LaunchChannel
  - derive_first_cohort_hint(refined_idea) -> str
  - default_readiness_checklist() -> list[ReadinessItem]

Only ``first_channel_rationale`` + ``share_copy_variants`` come from the LLM.
Everything else is assembled in Python so the kit is stable and testable.

Per .cursorrules: imports complete_structured from app.llm.client only; does NOT
import provider SDKs directly. Every LLM call logs to LLMCall via the client
wrapper (prompt_name=launch_kit_v1, phase=launch_kit).

Per AGENTS.md logging hygiene: NEVER log RefinedIdea / ValidationReport / copy
content. Log only aggregate counts, the picked channel, cost, and latency.

Does NOT change Experiment.status — status transitions live in the caller
(dispatcher / router), mirroring insight_service and landing_page_service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.launch_kit import LaunchKit as LaunchKitRow
from app.db.models.validation_report import ValidationReport as ValidationReportRow
from app.llm.prompts.launch_kit import (
    LAUNCH_KIT_CACHE_BREAKPOINTS,
    LAUNCH_KIT_PROMPT_NAME,
    LAUNCH_KIT_REGEN_PROMPT_NAME,
    LAUNCH_KIT_SYSTEM_PROMPT,
    build_launch_kit_regen_user_prompt,
    build_launch_kit_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.launch_kit import (
    LaunchChannel,
    LaunchKit,
    LaunchKitEnvelope,
    LaunchKitLLMOutput,
    LaunchKitPatch,
    LaunchKitRegenLLMOutput,
    ReadinessItem,
    ShareSurface,
)
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport

_logger = get_logger(__name__)

_LAUNCH_KIT_MAX_TOKENS = 4096
_LAUNCH_KIT_REGEN_MAX_TOKENS = 1024
# 0.6 — Kimi k2.6 requires temperature=0.6 when thinking is disabled (ADR 0018).
_LAUNCH_KIT_TEMPERATURE = 0.6


# --- Exceptions ------------------------------------------------------------


class LaunchKitError(Exception):
    """Base for LaunchKit domain errors."""


class LaunchKitPreconditionError(LaunchKitError):
    """A required input (landing page, validation report, refined idea) is missing."""


class LaunchKitLLMError(LaunchKitError):
    """The launch_kit_v1 LLM call failed."""


class LaunchKitNotFoundError(LaunchKitError):
    """No LaunchKit row exists for the experiment."""


class LaunchKitVersionConflictError(LaunchKitError):
    """The client's expected version does not match the stored version (CAS)."""


# --- Provider resolution ---------------------------------------------------


def _launch_kit_provider_and_model(settings: object) -> tuple[str, str]:
    """Resolve provider/model, defaulting to Kimi k2.6.

    Kept local (not shared with landing) so LaunchKit stays decoupled. Honors
    optional ``launch_kit_provider`` / ``launch_kit_model`` settings if they are
    ever added; otherwise falls back to the insight defaults (kimi / kimi-k2.6).
    """
    provider = getattr(settings, "launch_kit_provider", None)
    model = getattr(settings, "launch_kit_model", None)
    if provider is None:
        provider = getattr(settings, "insight_provider", "kimi")
    if model is None:
        model = getattr(settings, "insight_model", "kimi-k2.6")
    return provider, model


# --- Deterministic assembly ------------------------------------------------

# Priority-ordered keyword → channel table. The first channel with any keyword
# present in the combined idea+signals text wins; Twitter is the safe default.
_CHANNEL_KEYWORDS: list[tuple[LaunchChannel, tuple[str, ...]]] = [
    (
        LaunchChannel.HACKERNEWS,
        (
            "developer",
            "engineer",
            "programmer",
            "devtool",
            "dev tool",
            " api",
            "open source",
            "open-source",
            " cli",
            " sdk",
            "infrastructure",
            "backend",
            "database",
            "devops",
        ),
    ),
    (
        LaunchChannel.LINKEDIN,
        (
            "b2b",
            "enterprise",
            "saas",
            "sales team",
            "recruit",
            " hr ",
            "human resources",
            "manager",
            "executive",
            "consult",
            "agency",
            "professional",
            "compliance",
            "operations",
            "procurement",
        ),
    ),
    (LaunchChannel.PRODUCT_HUNT, ("product hunt", "producthunt")),
    (
        LaunchChannel.NEWSLETTER,
        ("newsletter", "subscriber", "email list", "content creator"),
    ),
    (
        LaunchChannel.REDDIT,
        (
            "reddit",
            "subreddit",
            "community",
            "hobby",
            "hobbyist",
            "enthusiast",
            "gamer",
            "gaming",
            "niche",
        ),
    ),
    (
        LaunchChannel.TWITTER,
        ("creator", "designer", "indie", "consumer", "student", "influencer", "gen z"),
    ),
]


def pick_first_channel(
    refined_idea: RefinedIdea, validation_report: ValidationReport
) -> LaunchChannel:
    """Rule-based first-channel pick from the audience + distribution signals.

    Deterministic and side-effect-free. The LLM only explains this choice; it
    never makes it.
    """
    haystack = " ".join(
        part
        for part in (
            refined_idea.target_audience,
            refined_idea.refined_one_liner,
            refined_idea.value_proposition,
            validation_report.distribution_signals or "",
        )
        if part
    ).lower()
    for channel, keywords in _CHANNEL_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return channel
    return LaunchChannel.TWITTER


def derive_first_cohort_hint(refined_idea: RefinedIdea) -> str:
    """A geography-neutral, deterministic sentence naming the first ~10 people."""
    audience = refined_idea.target_audience.strip().rstrip(".")
    hint = (
        f"Start with 10 people who are unmistakably {audience}. Reach out one by one — "
        "people you already know or who are one introduction away — and ask them to try it "
        "and tell you the honest truth."
    )
    return hint[:500]


def default_readiness_checklist() -> list[ReadinessItem]:
    """The fixed 5-item pre-launch checklist. ``checked_at`` starts null."""
    return [
        ReadinessItem(
            id="landing_live",
            label="Landing page is live and loads correctly on mobile",
        ),
        ReadinessItem(
            id="waitlist_works",
            label="Waitlist form submits and the signup reaches you",
        ),
        ReadinessItem(
            id="share_copy_ready",
            label="At least one share-copy variant is ready to post",
        ),
        ReadinessItem(
            id="first_cohort_listed",
            label="You have listed your first 10 people to contact",
        ),
        ReadinessItem(
            id="tracking_on",
            label="Source tags are set up so you can see where signups come from",
        ),
    ]


# --- Fetch helpers ---------------------------------------------------------


async def _fetch_experiment(db: AsyncSession, experiment_id: UUID) -> Experiment:
    row = (
        await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    ).scalar_one_or_none()
    if row is None:
        raise LaunchKitPreconditionError(f"Experiment {experiment_id} not found")
    return row


async def _fetch_landing_page(db: AsyncSession, experiment_id: UUID) -> LandingPage:
    row = (
        await db.execute(
            select(LandingPage).where(LandingPage.experiment_id == experiment_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise LaunchKitPreconditionError(
            f"Experiment {experiment_id} has no landing page — cannot generate a launch kit"
        )
    return row


async def _fetch_validation_report(
    db: AsyncSession, experiment_id: UUID
) -> ValidationReport:
    row = (
        await db.execute(
            select(ValidationReportRow).where(
                ValidationReportRow.experiment_id == experiment_id
            )
        )
    ).scalar_one_or_none()
    if row is None or row.raw_report is None:
        raise LaunchKitPreconditionError(
            f"Experiment {experiment_id} has no validation report"
        )
    return ValidationReport.model_validate(row.raw_report)


def _parse_refined_idea(experiment: Experiment) -> RefinedIdea:
    if experiment.refined_idea is None:
        raise LaunchKitPreconditionError(
            f"Experiment {experiment.id} has no refined_idea — refinement must run first"
        )
    return RefinedIdea.model_validate(experiment.refined_idea)


async def _fetch_launch_kit_row(
    db: AsyncSession, experiment_id: UUID
) -> LaunchKitRow | None:
    return (
        await db.execute(
            select(LaunchKitRow).where(LaunchKitRow.experiment_id == experiment_id)
        )
    ).scalar_one_or_none()


# --- Persistence -----------------------------------------------------------


async def _persist_launch_kit_row(
    db: AsyncSession, *, experiment_id: UUID, launch_kit: LaunchKit
) -> None:
    """Insert a new row or overwrite an existing one (regeneration).

    Regeneration bumps ``version``, overwrites ``raw_report``, clears
    ``edited_doc`` and ``edited_at``, and refreshes ``generated_at``.
    """
    row = await _fetch_launch_kit_row(db, experiment_id)
    raw = launch_kit.model_dump(mode="json")
    if row is None:
        db.add(
            LaunchKitRow(
                experiment_id=experiment_id,
                landing_page_id=launch_kit.landing_page_id,
                raw_report=raw,
                edited_doc=None,
                version=1,
                edited_at=None,
                generated_at=launch_kit.generated_at,
            )
        )
    else:
        row.landing_page_id = launch_kit.landing_page_id
        row.raw_report = raw
        row.edited_doc = None
        row.version = row.version + 1
        row.edited_at = None
        row.generated_at = launch_kit.generated_at


# --- Orchestration ---------------------------------------------------------


async def generate_launch_kit(db: AsyncSession, experiment_id: UUID) -> LaunchKit:
    """Generate (or regenerate) the LaunchKit for an experiment.

    Raises:
      LaunchKitPreconditionError — missing landing page / validation report /
        refined idea.
      LaunchKitLLMError — the launch_kit_v1 LLM call failed.
    """
    settings = get_settings()
    provider, model = _launch_kit_provider_and_model(settings)
    typed_provider = cast(llm_client.ProviderName, provider)

    experiment = await _fetch_experiment(db, experiment_id)
    landing_page = await _fetch_landing_page(db, experiment_id)
    validation_report = await _fetch_validation_report(db, experiment_id)
    refined_idea = _parse_refined_idea(experiment)

    first_channel = pick_first_channel(refined_idea, validation_report)

    try:
        llm_output, llm_result = await llm_client.complete_structured(
            db,
            provider=typed_provider,
            model=model,
            prompt_name=LAUNCH_KIT_PROMPT_NAME,
            system=LAUNCH_KIT_SYSTEM_PROMPT,
            user=build_launch_kit_user_prompt(
                refined_idea,
                validation_report,
                first_channel,
                experiment.target_geography,
            ),
            response_model=LaunchKitLLMOutput,
            max_tokens=_LAUNCH_KIT_MAX_TOKENS,
            temperature=_LAUNCH_KIT_TEMPERATURE,
            experiment_id=experiment_id,
            phase="launch_kit",
            cache_breakpoints=LAUNCH_KIT_CACHE_BREAKPOINTS,
        )
    except Exception as exc:
        raise LaunchKitLLMError(
            f"LaunchKit LLM call failed for experiment {experiment_id}"
        ) from exc

    launch_kit = LaunchKit(
        schema_version=1,
        landing_page_id=landing_page.id,
        first_channel=first_channel,
        first_channel_rationale=llm_output.first_channel_rationale,
        first_cohort_hint=derive_first_cohort_hint(refined_idea),
        share_copy_variants=llm_output.share_copy_variants,
        readiness_checklist=default_readiness_checklist(),
        generated_at=datetime.now(timezone.utc),
        founder_edited=False,
        raw_report=llm_output.model_dump(mode="json"),
    )

    await _persist_launch_kit_row(db, experiment_id=experiment_id, launch_kit=launch_kit)
    await db.flush()

    _logger.info(
        "launch kit generated",
        experiment_id=str(experiment_id),
        first_channel=first_channel.value,
        variant_count=len(launch_kit.share_copy_variants),
        cost_usd=str(llm_result.cost_usd),
        latency_ms=llm_result.latency_ms,
    )
    return launch_kit


# --- Read / edit -----------------------------------------------------------


async def get_launch_kit(
    db: AsyncSession, experiment_id: UUID
) -> LaunchKitEnvelope | None:
    """Return the current LaunchKit (edited overlay if present) or None."""
    row = await _fetch_launch_kit_row(db, experiment_id)
    if row is None:
        return None
    launch_kit = LaunchKit.model_validate(row.edited_doc or row.raw_report)
    return LaunchKitEnvelope(launch_kit=launch_kit, version=row.version)


def _apply_patch(current: LaunchKit, patch: LaunchKitPatch) -> LaunchKit:
    """Apply a partial patch to a LaunchKit, returning a new instance.

    Raises ValueError for out-of-range variant indices or unknown checklist ids
    (the router maps ValueError → 400).
    """
    updated = current.model_copy(deep=True)

    if patch.first_channel is not None:
        updated.first_channel = patch.first_channel
    if patch.first_channel_rationale is not None:
        updated.first_channel_rationale = patch.first_channel_rationale
    if patch.first_cohort_hint is not None:
        updated.first_cohort_hint = patch.first_cohort_hint

    if patch.share_copy_variants is not None:
        for item in patch.share_copy_variants:
            if not 0 <= item.index < len(updated.share_copy_variants):
                raise ValueError(
                    f"share_copy_variants index {item.index} out of range"
                )
            updated.share_copy_variants[item.index].text = item.text

    if patch.readiness_checklist is not None:
        by_id = {r.id: r for r in updated.readiness_checklist}
        for item in patch.readiness_checklist:
            target = by_id.get(item.id)
            if target is None:
                raise ValueError(f"readiness item {item.id!r} not found")
            target.checked_at = item.checked_at

    return updated


async def patch_launch_kit(
    db: AsyncSession,
    experiment_id: UUID,
    *,
    expected_version: int,
    patch: LaunchKitPatch,
) -> LaunchKitEnvelope:
    """Apply a founder edit under optimistic concurrency (compare-and-swap).

    Raises:
      LaunchKitNotFoundError — no launch kit exists.
      LaunchKitVersionConflictError — expected_version != stored version.
      ValueError — malformed patch target (bad index / unknown id).
    """
    row = await _fetch_launch_kit_row(db, experiment_id)
    if row is None:
        raise LaunchKitNotFoundError(
            f"No launch kit for experiment {experiment_id}"
        )
    if row.version != expected_version:
        raise LaunchKitVersionConflictError(
            f"Version mismatch: expected {expected_version}, stored {row.version}"
        )

    current = LaunchKit.model_validate(row.edited_doc or row.raw_report)
    updated = _apply_patch(current, patch)
    updated.founder_edited = True

    row.edited_doc = updated.model_dump(mode="json")
    row.version = row.version + 1
    row.edited_at = datetime.now(timezone.utc)
    await db.flush()

    return LaunchKitEnvelope(launch_kit=updated, version=row.version)


async def regenerate_variant(
    db: AsyncSession,
    experiment_id: UUID,
    *,
    surface: ShareSurface,
) -> LaunchKitEnvelope:
    """Rewrite one share-copy surface via LLM; server bumps version.

    Loads ``edited_doc or raw_report``, replaces the matching surface's text,
    bumps ``regenerated_count`` on that variant only, writes ``edited_doc``,
    bumps ``version``, sets ``founder_edited=true``. Never rewrites
    ``raw_report``.

    Raises:
      LaunchKitNotFoundError — no launch kit exists.
      ValueError — surface not present in the kit's share_copy_variants.
      LaunchKitLLMError — the launch_kit_regen_v1 LLM call failed.
      LaunchKitPreconditionError — missing experiment context for the LLM.
    """
    row = await _fetch_launch_kit_row(db, experiment_id)
    if row is None:
        raise LaunchKitNotFoundError(
            f"No launch kit for experiment {experiment_id}"
        )

    current = LaunchKit.model_validate(row.edited_doc or row.raw_report)
    target = next(
        (v for v in current.share_copy_variants if v.surface == surface),
        None,
    )
    if target is None:
        raise ValueError(f"share_copy surface {surface.value!r} not found in kit")

    settings = get_settings()
    provider, model = _launch_kit_provider_and_model(settings)
    typed_provider = cast(llm_client.ProviderName, provider)

    experiment = await _fetch_experiment(db, experiment_id)
    validation_report = await _fetch_validation_report(db, experiment_id)
    refined_idea = _parse_refined_idea(experiment)

    try:
        llm_output, llm_result = await llm_client.complete_structured(
            db,
            provider=typed_provider,
            model=model,
            prompt_name=LAUNCH_KIT_REGEN_PROMPT_NAME,
            system=LAUNCH_KIT_SYSTEM_PROMPT,
            user=build_launch_kit_regen_user_prompt(
                refined_idea,
                validation_report,
                current.first_channel,
                experiment.target_geography,
                surface=surface,
                previous_text=target.text,
            ),
            response_model=LaunchKitRegenLLMOutput,
            max_tokens=_LAUNCH_KIT_REGEN_MAX_TOKENS,
            temperature=_LAUNCH_KIT_TEMPERATURE,
            experiment_id=experiment_id,
            phase="launch_kit",
            cache_breakpoints=LAUNCH_KIT_CACHE_BREAKPOINTS,
        )
    except Exception as exc:
        raise LaunchKitLLMError(
            f"LaunchKit regen LLM call failed for experiment {experiment_id}"
        ) from exc

    updated = current.model_copy(deep=True)
    for variant in updated.share_copy_variants:
        if variant.surface == surface:
            variant.text = llm_output.text
            variant.regenerated_count = variant.regenerated_count + 1
            break
    updated.founder_edited = True

    row.edited_doc = updated.model_dump(mode="json")
    row.version = row.version + 1
    row.edited_at = datetime.now(timezone.utc)
    await db.flush()

    _logger.info(
        "launch kit variant regenerated",
        experiment_id=str(experiment_id),
        surface=surface.value,
        version=row.version,
        cost_usd=str(llm_result.cost_usd),
        latency_ms=llm_result.latency_ms,
    )
    return LaunchKitEnvelope(launch_kit=updated, version=row.version)
