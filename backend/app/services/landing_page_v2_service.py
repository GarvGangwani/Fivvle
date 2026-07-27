"""Landing Page Runtime — five-stage creative pipeline.

  Narrative Architect → Creative Director → Visual Composer → Component Planner → Renderer

Does NOT modify V1. Does NOT rerun research.
"""

from __future__ import annotations

import re
from typing import TypeVar, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_v2 import LandingPageV2Spec as LandingPageV2SpecRow
from app.db.models.validation_report import ValidationReport as ValidationReportRow
from app.llm.prompts.landing_page_v2_component import (
    LP_RUNTIME_COMPONENT_CACHE_BREAKPOINTS,
    LP_RUNTIME_COMPONENT_PROMPT_NAME,
    LP_RUNTIME_COMPONENT_SYSTEM_PROMPT,
    build_lp_runtime_component_user_prompt,
)
from app.llm.prompts.landing_page_v2_creative import (
    LP_RUNTIME_CREATIVE_CACHE_BREAKPOINTS,
    LP_RUNTIME_CREATIVE_PROMPT_NAME,
    LP_RUNTIME_CREATIVE_SYSTEM_PROMPT,
    build_lp_runtime_creative_user_prompt,
)
from app.llm.prompts.landing_page_v2_narrative import (
    LP_RUNTIME_NARRATIVE_CACHE_BREAKPOINTS,
    LP_RUNTIME_NARRATIVE_PROMPT_NAME,
    LP_RUNTIME_NARRATIVE_SYSTEM_PROMPT,
    build_lp_runtime_narrative_user_prompt,
)
from app.llm.prompts.landing_page_v2_visual import (
    LP_RUNTIME_VISUAL_CACHE_BREAKPOINTS,
    LP_RUNTIME_VISUAL_PROMPT_NAME,
    LP_RUNTIME_VISUAL_SYSTEM_PROMPT,
    build_lp_runtime_visual_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.landing_page_v2 import (
    ComponentPlannerOutput,
    CreativeDirectorOutput,
    LandingPageV2GenerationStatus,
    LandingPageV2Spec,
    NarrativeArchitectOutput,
    PipelineArtifacts,
    VisualComposerOutput,
)
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport
from app.services.landing_page_service import _landing_page_provider_and_model
from app.services.validation_report_editor import flatten_prosemirror_doc
from app.services.validation_report_for_landing import ValidationReportForLanding

_logger = get_logger(__name__)

_LP_NARRATIVE_MAX_TOKENS = 4096
_LP_CREATIVE_MAX_TOKENS = 8192
_LP_VISUAL_MAX_TOKENS = 4096
_LP_COMPONENT_MAX_TOKENS = 16384
_LP_TEMPERATURE = 0.6

_MAX_ERROR_LEN = 500

T = TypeVar("T")


class LandingPageV2Error(Exception):
    """Base V2 runtime error."""


class MissingResearchData(LandingPageV2Error):
    """Validation report or refined idea not available."""


def _sanitize_error(exc: Exception) -> str:
    msg = str(exc)
    msg = re.sub(r"[A-Za-z0-9_\-]{32,}", "[REDACTED]", msg)
    return f"{type(exc).__name__}: {msg}"[:_MAX_ERROR_LEN]


def _collect_uploaded_assets(landing_page: LandingPage | None) -> list[dict[str, str]]:
    if landing_page is None or not landing_page.page_json:
        return []
    assets: list[dict[str, str]] = []
    page_json = landing_page.page_json
    branding = page_json.get("branding") if isinstance(page_json.get("branding"), dict) else {}
    logo_url = branding.get("logo_url") if isinstance(branding.get("logo_url"), str) else None
    if logo_url:
        assets.append({"asset_key": "logo", "role": "brand_logo", "url": logo_url})
    section_images = page_json.get("section_images")
    if isinstance(section_images, dict):
        for slot_id, url in section_images.items():
            if isinstance(url, str) and url.strip():
                assets.append(
                    {"asset_key": slot_id, "role": f"section_{slot_id}", "url": url}
                )
    return assets


def _merge_asset_urls(
    spec: LandingPageV2Spec,
    uploaded: list[dict[str, str]],
) -> tuple[LandingPageV2Spec, dict[str, str]]:
    url_by_key = {item["asset_key"]: item["url"] for item in uploaded if item.get("url")}
    resolved: dict[str, str] = dict(url_by_key)
    updated_refs = []
    for ref in spec.asset_refs:
        url = ref.url or url_by_key.get(ref.asset_key)
        if url:
            resolved[ref.asset_key] = url
        updated_refs.append(ref.model_copy(update={"url": url}))
    if not updated_refs and uploaded:
        from app.schemas.landing_page_v2 import AssetRefSpec

        updated_refs = [
            AssetRefSpec(
                asset_key=a["asset_key"],
                role=a.get("role", "upload"),
                alt=a.get("role", "Image"),
                url=a.get("url"),
            )
            for a in uploaded
        ]
    return spec.model_copy(update={"asset_refs": updated_refs}), resolved


async def _load_validation_report(
    db: AsyncSession,
    experiment_id: UUID,
) -> ValidationReportForLanding:
    """Fetch ValidationReport row: parse raw_report; flatten edited_doc when present."""
    result = await db.execute(
        select(ValidationReportRow).where(
            ValidationReportRow.experiment_id == experiment_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None or not row.raw_report:
        raise MissingResearchData("Validation report not found for experiment")
    report = ValidationReport.model_validate(row.raw_report)
    edited_narrative = flatten_prosemirror_doc(row.edited_doc)
    return ValidationReportForLanding(
        report=report,
        edited_narrative=edited_narrative,
        edited_doc_version=row.edited_doc_version,
    )


async def _get_or_create_v2_row(
    db: AsyncSession,
    experiment_id: UUID,
) -> LandingPageV2SpecRow:
    result = await db.execute(
        select(LandingPageV2SpecRow).where(
            LandingPageV2SpecRow.experiment_id == experiment_id
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = LandingPageV2SpecRow(experiment_id=experiment_id, generation_status="idle")
    db.add(row)
    await db.flush()
    return row


async def assert_v2_generation_prerequisites(
    db: AsyncSession,
    *,
    experiment_id: UUID,
) -> None:
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = exp_result.scalar_one_or_none()
    if experiment is None:
        raise MissingResearchData("Experiment not found")
    if not experiment.refined_idea:
        raise MissingResearchData("Refined idea not available")
    await _load_validation_report(db, experiment_id)


def _phase_from_row(row: LandingPageV2SpecRow) -> str:
    phase = getattr(row, "generation_phase", None) or "idle"
    if row.generation_status == "ready":
        return "ready"
    if row.generation_status == "failed":
        return "failed"
    return phase


async def get_landing_page_v2_status(
    db: AsyncSession,
    *,
    experiment_id: UUID,
) -> LandingPageV2GenerationStatus:
    v2_row = await _get_or_create_v2_row(db, experiment_id)
    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id)
    )
    landing_page = lp_result.scalar_one_or_none()
    publication_slug = landing_page.slug if landing_page and landing_page.live_at else None

    spec: LandingPageV2Spec | None = None
    resolved_assets: dict[str, str] = {}
    if v2_row.spec_json:
        try:
            spec = LandingPageV2Spec.model_validate(v2_row.spec_json)
            uploaded = _collect_uploaded_assets(landing_page)
            spec, resolved_assets = _merge_asset_urls(spec, uploaded)
        except Exception:
            _logger.warning(
                "landing page runtime spec validation failed on read",
                experiment_id=str(experiment_id),
            )

    return LandingPageV2GenerationStatus(
        experiment_id=str(experiment_id),
        generation_status=v2_row.generation_status,  # type: ignore[arg-type]
        generation_phase=_phase_from_row(v2_row),  # type: ignore[arg-type]
        error_detail=v2_row.error_detail,
        spec=spec,
        publication_slug=publication_slug,
        resolved_assets=resolved_assets,
    )


async def _set_generation_phase(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    phase: str,
) -> None:
    row = await _get_or_create_v2_row(db, experiment_id)
    row.generation_status = "generating"
    row.generation_phase = phase
    row.error_detail = None
    await db.flush()


async def _run_structured(
    db: AsyncSession,
    *,
    provider: llm_client.ProviderName,
    model: str,
    system: str,
    user: str,
    response_model: type[T],
    prompt_name: str,
    phase: str,
    max_tokens: int,
    experiment_id: UUID,
    cache_breakpoints: list[llm_client.CacheBreakpoint],
) -> T:
    result, _ = await llm_client.complete_structured(
        db,
        provider=provider,
        model=model,
        system=system,
        user=user,
        response_model=response_model,
        prompt_name=prompt_name,
        max_tokens=max_tokens,
        temperature=_LP_TEMPERATURE,
        experiment_id=experiment_id,
        phase=phase,
        cache_breakpoints=cache_breakpoints,
    )
    return result


async def generate_landing_page_v2_spec(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    page_goal: str = "waitlist",
    regeneration_hint: str | None = None,
) -> LandingPageV2Spec:
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = exp_result.scalar_one_or_none()
    if experiment is None:
        raise MissingResearchData("Experiment not found")
    if not experiment.refined_idea:
        raise MissingResearchData("Refined idea not available")

    validation_bundle = await _load_validation_report(db, experiment_id)
    validation_report = validation_bundle.report
    edited_narrative = validation_bundle.edited_narrative
    refined_idea = RefinedIdea.model_validate(experiment.refined_idea)
    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id)
    )
    landing_page = lp_result.scalar_one_or_none()
    uploaded_assets = _collect_uploaded_assets(landing_page)

    settings = get_settings()
    provider, model = _landing_page_provider_and_model(settings)
    typed_provider = cast(llm_client.ProviderName, provider)

    # Stage 1 — Narrative Architect
    await _set_generation_phase(db, experiment_id=experiment_id, phase="planning_narrative")
    await db.commit()

    narrative = await _run_structured(
        db,
        provider=typed_provider,
        model=model,
        system=LP_RUNTIME_NARRATIVE_SYSTEM_PROMPT,
        user=build_lp_runtime_narrative_user_prompt(
            validation_report=validation_report,
            refined_idea=refined_idea,
            page_goal=page_goal,
            regeneration_hint=regeneration_hint,
            edited_narrative=edited_narrative,
        ),
        response_model=NarrativeArchitectOutput,
        prompt_name=LP_RUNTIME_NARRATIVE_PROMPT_NAME,
        phase="lp_narrative_architect",
        max_tokens=_LP_NARRATIVE_MAX_TOKENS,
        experiment_id=experiment_id,
        cache_breakpoints=LP_RUNTIME_NARRATIVE_CACHE_BREAKPOINTS,
    )

    # Stage 2 — Creative Director
    await _set_generation_phase(db, experiment_id=experiment_id, phase="creative_direction")
    await db.commit()

    creative = await _run_structured(
        db,
        provider=typed_provider,
        model=model,
        system=LP_RUNTIME_CREATIVE_SYSTEM_PROMPT,
        user=build_lp_runtime_creative_user_prompt(
            narrative=narrative,
            validation_report=validation_report,
            refined_idea=refined_idea,
            page_goal=page_goal,
        ),
        response_model=CreativeDirectorOutput,
        prompt_name=LP_RUNTIME_CREATIVE_PROMPT_NAME,
        phase="lp_creative_director",
        max_tokens=_LP_CREATIVE_MAX_TOKENS,
        experiment_id=experiment_id,
        cache_breakpoints=LP_RUNTIME_CREATIVE_CACHE_BREAKPOINTS,
    )

    # Stage 3 — Visual Composer
    await _set_generation_phase(db, experiment_id=experiment_id, phase="visual_composition")
    await db.commit()

    visual = await _run_structured(
        db,
        provider=typed_provider,
        model=model,
        system=LP_RUNTIME_VISUAL_SYSTEM_PROMPT,
        user=build_lp_runtime_visual_user_prompt(
            narrative=narrative,
            creative=creative,
            refined_idea=refined_idea,
            available_assets=uploaded_assets,
        ),
        response_model=VisualComposerOutput,
        prompt_name=LP_RUNTIME_VISUAL_PROMPT_NAME,
        phase="lp_visual_composer",
        max_tokens=_LP_VISUAL_MAX_TOKENS,
        experiment_id=experiment_id,
        cache_breakpoints=LP_RUNTIME_VISUAL_CACHE_BREAKPOINTS,
    )

    # Stage 4 — Component Planner
    await _set_generation_phase(db, experiment_id=experiment_id, phase="component_planning")
    await db.commit()

    planner = await _run_structured(
        db,
        provider=typed_provider,
        model=model,
        system=LP_RUNTIME_COMPONENT_SYSTEM_PROMPT,
        user=build_lp_runtime_component_user_prompt(
            narrative=narrative,
            creative=creative,
            visual=visual,
            validation_report=validation_report,
            refined_idea=refined_idea,
            page_goal=page_goal,
            regeneration_hint=regeneration_hint,
            available_assets=uploaded_assets,
        ),
        response_model=ComponentPlannerOutput,
        prompt_name=LP_RUNTIME_COMPONENT_PROMPT_NAME,
        phase="lp_component_planner",
        max_tokens=_LP_COMPONENT_MAX_TOKENS,
        experiment_id=experiment_id,
        cache_breakpoints=LP_RUNTIME_COMPONENT_CACHE_BREAKPOINTS,
    )

    spec = LandingPageV2Spec(
        page_goal=page_goal,  # type: ignore[arg-type]
        pipeline=PipelineArtifacts(
            narrative=narrative,
            creative_director=creative,
            visual_composer=visual,
        ),
        design_tokens=planner.design_tokens,
        components=planner.components,
        asset_refs=[],
    )
    spec, resolved = _merge_asset_urls(spec, uploaded_assets)

    from app.services.spark_version_service import get_latest_spark_version_id

    # Stamp cascade dimensions at generation; edited_doc_version 0 when overlay absent.
    stamped_edited_doc_version = (
        0
        if edited_narrative is None
        else (validation_bundle.edited_doc_version or 0)
    )

    v2_row = await _get_or_create_v2_row(db, experiment_id)
    v2_row.spec_json = spec.model_dump(mode="json")
    v2_row.generation_status = "ready"
    v2_row.generation_phase = "ready"
    v2_row.error_detail = None
    v2_row.spark_version_id = await get_latest_spark_version_id(db, experiment_id)
    v2_row.refined_idea_version = experiment.refined_idea_version
    v2_row.edited_doc_version = stamped_edited_doc_version
    await db.flush()

    _logger.info(
        "landing page runtime spec generated",
        experiment_id=str(experiment_id),
        component_count=len(spec.components),
        archetype=narrative.business_archetype,
    )
    return spec


async def run_landing_page_v2_generation_task(
    experiment_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    page_goal: str,
    regeneration_hint: str | None,
) -> None:
    async with sessionmaker() as session:
        v2_row = await _get_or_create_v2_row(session, experiment_id)
        v2_row.generation_status = "generating"
        v2_row.generation_phase = "planning_narrative"
        v2_row.error_detail = None
        await session.commit()

        try:
            await generate_landing_page_v2_spec(
                session,
                experiment_id=experiment_id,
                page_goal=page_goal,
                regeneration_hint=regeneration_hint,
            )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            async with sessionmaker() as err_session:
                row = await _get_or_create_v2_row(err_session, experiment_id)
                row.generation_status = "failed"
                row.generation_phase = "failed"
                row.error_detail = _sanitize_error(exc)
                await err_session.commit()
            _logger.error(
                "landing page runtime generation failed",
                experiment_id=str(experiment_id),
                error_type=type(exc).__name__,
            )
