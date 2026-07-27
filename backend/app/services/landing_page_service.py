"""Landing page service — 2-LLM-call + 1-Python-function pipeline (ADR 0022).

Single public function: generate_landing_page().

Called by the landing page dispatcher (deferred wiring). Reads Experiment +
ValidationReport, calls Kimi twice (strategist then copy generator), applies a
fixed designer template via theme_to_page_json(), and persists copy_json +
page_json on the LandingPage row.

Pipeline stages:
  1. Strategist (lp_strategist_v2) — ValidationReport + RefinedIdea + page_goal
     (+ optional founder-edited narrative) → LandingPageInputModel + LandingPageStrategy.
  2. Copy generator (lp_copy_v1) — input model + strategy → CopyOutput.
  3. Theme applicator (Python) — TEMPLATES lookup + section assembly → page_json.

Does NOT change Experiment.status — status transitions live in the caller
(dispatcher / orchestrator), mirroring insight_service and synthesizer_service.

Per .cursorrules: imports complete_structured from app.llm.client. Does NOT
import anthropic / kimi / groq clients directly.

Per AGENTS.md logging hygiene: NEVER log copy_json content, ValidationReport
content, RefinedIdea content, or PII. Log only aggregate counts and flags
(experiment_id, section_count, template_id, cost, latency).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.enums import LandingCtaType, LandingDensity
from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.db.models.validation_report import ValidationReport as ValidationReportRow
from app.llm.prompts.landing_page import (
    LP_COPY_PROMPT_NAME,
    LP_COPY_SYSTEM_PROMPT,
    LP_STRATEGIST_PROMPT_NAME,
    LP_STRATEGIST_SYSTEM_PROMPT,
    build_lp_copy_user_prompt,
    build_lp_strategist_user_prompt,
)
from app.logging_config import get_logger
from app.utils.experiment_naming import (
    ensure_unique_landing_slug,
    resolve_name_from_refined,
    resolve_slug_base_from_experiment,
    sync_landing_page_project_name,
)
from app.schemas.landing_page import (
    CopyOutput,
    LandingPageInputModel,
    LandingPageStrategy,
)
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport
from app.services.validation_report_editor import flatten_prosemirror_doc
from app.services.validation_report_for_landing import ValidationReportForLanding

_logger = get_logger(__name__)

LP_STRATEGIST_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
    llm_client.CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
]

LP_COPY_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
    llm_client.CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
]

# Strategist emits two nested models; copy emits per-section dicts.
_LP_STRATEGIST_MAX_TOKENS = 8192
_LP_COPY_MAX_TOKENS = 16384

# 0.6 — Kimi k2.6 requires temperature=0.6 when thinking is disabled (ADR 0018).
_LP_TEMPERATURE = 0.6

TemplateId = Literal[
    "dark-premium",
    "bold-v1",
    "minimal-v3",
    "editorial-saas",
    "aether",
    "abstract",
]

TEMPLATES: dict[str, dict[str, Any]] = {
    "dark-premium": {
        "name": "Dark Premium",
        "default_color_mode": "dark",
        "color_palette": {
            "primary": "#0a0908",
            "secondary": "#100e0c",
            "accent": "#c9a25f",
            "background": "#0a0908",
        },
        "typography": {
            "heading_font": "'Instrument Serif', serif",
            "body_font": "'Manrope', sans-serif",
        },
        "visual_style": "dark-premium",
    },
    "bold-v1": {
        "name": "Bold V1",
        "default_color_mode": "light",
        "color_palette": {
            "primary": "#111111",
            "secondary": "#EDE7DB",
            "accent": "#FF3B1F",
            "background": "#F5F1EA",
        },
        "typography": {
            "heading_font": "'Bricolage Grotesque', sans-serif",
            "body_font": "'Inter Tight', sans-serif",
        },
        "visual_style": "bold-v1",
    },
    "minimal-v3": {
        "name": "Minimal v3",
        "default_color_mode": "light",
        "color_palette": {
            "primary": "#040404",
            "secondary": "#f7efde",
            "accent": "#C73A1B",
            "background": "#f7efde",
        },
        "typography": {
            "heading_font": "'Bricolage Grotesque', sans-serif",
            "body_font": "'Hanken Grotesk', sans-serif",
        },
        "visual_style": "minimal-v3",
    },
    "editorial-saas": {
        "name": "Editorial SaaS",
        "default_color_mode": "light",
        "color_palette": {
            "primary": "#18181b",
            "secondary": "#f2f1ed",
            "accent": "#000000",
            "background": "#f8f8f6",
        },
        "typography": {
            "heading_font": "'Cormorant Garamond', serif",
            "body_font": "'Inter', sans-serif",
        },
        "visual_style": "editorial-saas",
    },
    "aether": {
        "name": "Aether",
        "default_color_mode": "light",
        "color_palette": {
            "primary": "#1d1d1d",
            "secondary": "#ececec",
            "accent": "#d6fd70",
            "background": "#f2f2f2",
        },
        "typography": {
            "heading_font": "'Plus Jakarta Sans', sans-serif",
            "body_font": "'Plus Jakarta Sans', sans-serif",
        },
        "visual_style": "aether",
    },
    "abstract": {
        "name": "Abstract",
        "default_color_mode": "light",
        "color_palette": {
            "primary": "#1a1d1b",
            "secondary": "#edeae4",
            "accent": "#2d4a3e",
            "background": "#f6f4f0",
        },
        "typography": {
            "heading_font": "'Outfit', sans-serif",
            "body_font": "'Outfit', sans-serif",
        },
        "visual_style": "abstract",
    },
}

_TEXT_DEFAULT_BY_TEMPLATE: dict[str, str] = {
    "dark-premium": "#ebe4d4",
    "bold-v1": "#111111",
    "minimal-v3": "#040404",
    "editorial-saas": "#18181b",
    "aether": "#1d1d1d",
    "abstract": "#1a1d1b",
}


class MissingValidationReportError(Exception):  # noqa: N818
    """Raised when generate_landing_page cannot find a ValidationReport row
    for the experiment. Indicates upstream pipeline failure — should not occur
    in normal flow (research must complete before landing page generation).
    """


class LandingPageGenerationError(Exception):  # noqa: N818
    """Raised when landing page generation fails due to missing prerequisites
    or an LLM/provider error during strategist or copy generation.
    """


class StrategistOutput(BaseModel):
    """Combined Stage 1 structured output — strategist LLM response shape."""

    model_config = ConfigDict(extra="forbid")

    input_model: LandingPageInputModel = Field(...)
    strategy: LandingPageStrategy = Field(...)


def resolve_template_id(template_id: str | None) -> str:
    """Return a valid template ID, defaulting to dark-premium."""
    if template_id and template_id in TEMPLATES:
        return template_id
    return "dark-premium"


def theme_to_page_json(
    template_config: dict[str, Any],
    copy_json: dict[str, Any],
    strategy: LandingPageStrategy,
    template_id: str,
) -> dict[str, Any]:
    """Build page_json consumed by the frontend preview.

    Pure Python — no LLM. Merges fixed designer template config with
    strategy-driven section order and copy content.
    """
    tid = resolve_template_id(template_id)
    tpl = template_config
    order = list(strategy.section_sequence)
    sections: list[dict[str, Any]] = []

    for section_type in order:
        content = copy_json.get(section_type)
        if content is None:
            continue
        if section_type in ("features", "faq"):
            sections.append({"type": section_type, "content": {"items": content}})
        else:
            sections.append({"type": section_type, "content": content})

    palette = tpl["color_palette"]
    typo = tpl["typography"]
    color_mode = tpl["default_color_mode"]
    text_default = _TEXT_DEFAULT_BY_TEMPLATE.get(tid, "#18181b")
    default_cp = {
        "preset": f"{tid}-default",
        "accent": palette["accent"],
        "background": palette["background"],
        "foreground": text_default,
    }

    return {
        "template_id": tid,
        "template_name": tpl["name"],
        "color_mode": color_mode,
        "color_palette": default_cp,
        "branding": {
            "icon_mode": "initials",
        },
        "theme": {
            "primary_color": palette["primary"],
            "secondary_color": palette["secondary"],
            "accent_color": palette["accent"],
            "background_color": palette["background"],
            "text_color": text_default,
            "heading_font": typo["heading_font"],
            "body_font": typo["body_font"],
            "font_family": f"{typo['heading_font']}, {typo['body_font']}",
            "style": tpl["visual_style"],
        },
        "sections": sections,
    }


def _page_goal_to_cta_type(page_goal: str) -> LandingCtaType:
    mapping = {
        "waitlist": LandingCtaType.WAITLIST,
        "interest": LandingCtaType.INTEREST,
        "contact": LandingCtaType.CONTACT,
    }
    return mapping.get(page_goal, LandingCtaType.WAITLIST)


async def _generate_unique_slug(db: AsyncSession, experiment: Experiment) -> str:
    """Derive a short slug from project name (user or AI), with collision handling."""
    base_slug = resolve_slug_base_from_experiment(experiment)
    if len(base_slug) < 6:
        base_slug = f"lp-{experiment.id.hex[:12]}"
    return await ensure_unique_landing_slug(
        db,
        base_slug,
        experiment_id=experiment.id,
    )


async def _fetch_validation_report(
    db: AsyncSession, experiment_id: UUID
) -> ValidationReportForLanding:
    """Fetch ValidationReport row: parse raw_report; flatten edited_doc when present."""
    stmt = select(ValidationReportRow).where(
        ValidationReportRow.experiment_id == experiment_id
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None or row.raw_report is None:
        raise MissingValidationReportError(
            f"No ValidationReport found for experiment {experiment_id}"
        )
    report = ValidationReport.model_validate(row.raw_report)
    edited_narrative = flatten_prosemirror_doc(row.edited_doc)
    return ValidationReportForLanding(
        report=report,
        edited_narrative=edited_narrative,
        edited_doc_version=row.edited_doc_version,
    )


async def _fetch_experiment(db: AsyncSession, experiment_id: UUID) -> Experiment:
    """Fetch Experiment row. Raises LandingPageGenerationError if missing."""
    stmt = select(Experiment).where(Experiment.id == experiment_id)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise LandingPageGenerationError(
            f"No Experiment found for experiment_id {experiment_id}"
        )
    return row


def _parse_refined_idea(experiment: Experiment) -> RefinedIdea:
    """Parse Experiment.refined_idea JSONB into RefinedIdea."""
    if experiment.refined_idea is None:
        raise LandingPageGenerationError(
            f"Experiment {experiment.id} has no refined_idea — refinement must "
            "complete before landing page generation."
        )
    return RefinedIdea.model_validate(experiment.refined_idea)


def _landing_page_provider_and_model(settings: object) -> tuple[str, str]:
    """Resolve provider/model until dedicated landing_page_* Settings fields ship."""
    provider = getattr(settings, "landing_page_provider", None)
    model = getattr(settings, "landing_page_model", None)
    if provider is None:
        provider = getattr(settings, "insight_provider", "kimi")
    if model is None:
        model = getattr(settings, "insight_model", "kimi-k2.6")
    return provider, model


async def _fetch_landing_page_row(
    db: AsyncSession, experiment_id: UUID
) -> LandingPage | None:
    stmt = select(LandingPage).where(LandingPage.experiment_id == experiment_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _scalar_fields_for_insert(
    *,
    copy_json: dict[str, Any],
    refined_idea: RefinedIdea,
    input_model: LandingPageInputModel,
    page_goal: str,
) -> dict[str, Any]:
    """Derive required NOT NULL scalar columns for a new LandingPage row."""
    hero = copy_json.get("hero") if isinstance(copy_json.get("hero"), dict) else {}
    problem = (
        copy_json.get("problem") if isinstance(copy_json.get("problem"), dict) else {}
    )
    return {
        "headline": str(hero.get("headline") or refined_idea.headline),
        "subheadline": hero.get("subheadline") or refined_idea.subheadline,
        "problem_desc": str(
            problem.get("body")
            or problem.get("heading")
            or refined_idea.value_proposition
        ),
        "solution_desc": str(
            input_model.offer_core.transformation_promise or refined_idea.value_proposition
        ),
        "cta_text": str(hero.get("cta") or refined_idea.cta_text),
        "cta_type": _page_goal_to_cta_type(page_goal),
    }


def _compact_text(value: str | None, fallback: str, max_len: int = 160) -> str:
    text = (value or "").strip() or fallback.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


_GENERIC_COMPARISON_LABEL = "The old way"


def _scrub_competitor_names_from_text(text: str, competitor_names: list[str]) -> str:
    """Replace known competitor names with generic phrasing in public copy."""
    cleaned = text
    for name in competitor_names:
        name = name.strip()
        if len(name) < 2:
            continue
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        cleaned = pattern.sub(_GENERIC_COMPARISON_LABEL.lower(), cleaned)
    return cleaned


def _scrub_competitor_names_from_copy(
    copy_json: dict[str, Any],
    competitor_names: list[str],
) -> dict[str, Any]:
    """Defense-in-depth: strip research competitor names from published copy."""
    if not competitor_names:
        return copy_json

    scrubbed: dict[str, Any] = {}
    for section, payload in copy_json.items():
        if section == "comparison" and isinstance(payload, dict):
            comparison = dict(payload)
            raw_name = str(comparison.get("competitor_name") or "").strip()
            if any(
                raw_name.lower() == name.strip().lower() for name in competitor_names if name.strip()
            ):
                comparison["competitor_name"] = _GENERIC_COMPARISON_LABEL
            scrubbed[section] = comparison
            continue

        if isinstance(payload, str):
            scrubbed[section] = _scrub_competitor_names_from_text(payload, competitor_names)
        elif isinstance(payload, dict):
            scrubbed[section] = {
                key: _scrub_competitor_names_from_text(value, competitor_names)
                if isinstance(value, str)
                else [
                    _scrub_competitor_names_from_text(item, competitor_names)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
                if isinstance(value, list)
                else value
                for key, value in payload.items()
            }
        elif isinstance(payload, list):
            scrubbed[section] = [
                {
                    key: _scrub_competitor_names_from_text(val, competitor_names)
                    if isinstance(val, str)
                    else val
                    for key, val in item.items()
                }
                if isinstance(item, dict)
                else _scrub_competitor_names_from_text(item, competitor_names)
                if isinstance(item, str)
                else item
                for item in payload
            ]
        else:
            scrubbed[section] = payload
    return scrubbed


def _fill_text(value: str | None, fallback: str, *, max_len: int = 200) -> str:
    """Keep LLM/user copy intact; only compact synthesized fallbacks."""
    text = (value or "").strip()
    if text:
        return text
    return _compact_text(None, fallback, max_len)


def _ensure_complete_copy_json(
    *,
    copy_json: dict[str, Any],
    strategy: LandingPageStrategy,
    input_model: LandingPageInputModel,
    refined_idea: RefinedIdea,
) -> dict[str, Any]:
    """Guarantee a complete, concise section set for the chosen strategy order.

    LLM output can occasionally omit a section or return sparse payloads. This
    normalizer keeps section shapes complete and user-facing copy brief.
    """
    completed = dict(copy_json)
    sequence = list(strategy.section_sequence)

    hero_default = {
        "headline": _compact_text(
            refined_idea.headline,
            input_model.offer_core.one_line_pitch,
            max_len=200,
        ),
        "subheadline": _compact_text(
            refined_idea.subheadline,
            input_model.offer_core.transformation_promise,
            max_len=480,
        ),
        "cta": _compact_text(refined_idea.cta_text, "Join the waitlist", max_len=80),
    }
    problem_default = {
        "heading": _compact_text(
            input_model.problem_intelligence.pain_points[0]
            if input_model.problem_intelligence.pain_points
            else "The old way is broken",
            "The old way is broken",
            max_len=90,
        ),
        "body": _compact_text(
            input_model.problem_intelligence.urgency,
            input_model.offer_core.transformation_promise,
            max_len=200,
        ),
    }
    cta_default = {
        "heading": _compact_text(
            input_model.offer_core.one_line_pitch,
            refined_idea.headline,
            max_len=90,
        ),
        "subheading": _compact_text(
            input_model.offer_core.transformation_promise,
            refined_idea.subheadline,
            max_len=160,
        ),
        "button": _compact_text(refined_idea.cta_text, "Get early access", max_len=44),
    }

    for section in sequence:
        existing = completed.get(section)
        if section == "hero":
            payload = existing if isinstance(existing, dict) else {}
            completed[section] = {
                "headline": _fill_text(
                    str(payload.get("headline") or ""),
                    hero_default["headline"],
                    max_len=200,
                ),
                "subheadline": _fill_text(
                    str(payload.get("subheadline") or ""),
                    hero_default["subheadline"],
                    max_len=480,
                ),
                "cta": _fill_text(
                    str(payload.get("cta") or ""),
                    hero_default["cta"],
                    max_len=80,
                ),
            }
            continue

        if section == "problem":
            payload = existing if isinstance(existing, dict) else {}
            completed[section] = {
                "heading": _fill_text(
                    str(payload.get("heading") or ""),
                    problem_default["heading"],
                    max_len=200,
                ),
                "body": _fill_text(
                    str(payload.get("body") or ""),
                    problem_default["body"],
                    max_len=600,
                ),
            }
            continue

        if section == "features":
            items = existing if isinstance(existing, list) else []
            if not items:
                pain_points = input_model.problem_intelligence.pain_points[:3]
                items = [
                    {
                        "title": _compact_text(point, "Clear user benefit", max_len=72),
                        "description": _compact_text(
                            input_model.offer_core.transformation_promise,
                            "A concrete outcome your users care about.",
                            max_len=150,
                        ),
                    }
                    for point in pain_points
                ]
            completed[section] = items[:5]
            continue

        if section == "comparison":
            payload = existing if isinstance(existing, dict) else {}
            completed[section] = {
                "metric_label": _fill_text(
                    str(payload.get("metric_label") or ""),
                    "What changes for you",
                    max_len=120,
                ),
                "competitor_name": _fill_text(
                    str(payload.get("competitor_name") or ""),
                    _GENERIC_COMPARISON_LABEL,
                    max_len=120,
                ),
                "our_features": list(payload.get("our_features") or [])[:4]
                or [
                    _compact_text(
                        input_model.positioning_intelligence.differentiators,
                        "A faster path to the outcome you want",
                        max_len=200,
                    )
                ],
                "competitor_features": list(payload.get("competitor_features") or [])[:4]
                or [
                    _compact_text(
                        input_model.problem_intelligence.alternatives,
                        "More manual steps and waiting",
                        max_len=200,
                    )
                ],
            }
            continue

        if section == "proof":
            payload = existing if isinstance(existing, dict) else {}
            elements = list(payload.get("elements") or [])[:5]
            if not elements:
                hooks = input_model.proof_intelligence.social_proof_hooks[:3]
                elements = [
                    _compact_text(
                        hook,
                        "Built around how you actually work today.",
                        max_len=130,
                    )
                    for hook in hooks
                ]
                if not elements:
                    elements = [
                        _compact_text(
                            input_model.offer_core.transformation_promise,
                            "Designed to remove friction from day one.",
                            max_len=130,
                        )
                    ]
            completed[section] = {
                "headline": _fill_text(
                    str(payload.get("headline") or ""),
                    "Why people trust this approach",
                    max_len=200,
                ),
                "elements": elements,
            }
            continue

        if section == "objections":
            payload = existing if isinstance(existing, dict) else {}
            items = list(payload.get("items") or [])[:4]
            if not items:
                top = input_model.proof_intelligence.top_objections[:3]
                rebuttals = input_model.proof_intelligence.objection_rebuttals
                items = [
                    {
                        "question": _compact_text(ob, "Is this really worth switching?", max_len=110),
                        "answer": _compact_text(
                            rebuttals.get(ob),
                            input_model.positioning_intelligence.differentiators,
                            max_len=170,
                        ),
                    }
                    for ob in top
                ]
            completed[section] = {
                "heading": _fill_text(
                    str(payload.get("heading") or ""),
                    "You might be wondering…",
                    max_len=200,
                ),
                "items": items,
            }
            continue

        if section == "faq":
            items = existing if isinstance(existing, list) else []
            completed[section] = items[:5]
            continue

        if section == "cta":
            payload = existing if isinstance(existing, dict) else {}
            completed[section] = {
                "heading": _fill_text(
                    str(payload.get("heading") or ""),
                    cta_default["heading"],
                    max_len=200,
                ),
                "subheading": _fill_text(
                    str(payload.get("subheading") or ""),
                    cta_default["subheading"],
                    max_len=400,
                ),
                "button": _fill_text(
                    str(payload.get("button") or ""),
                    cta_default["button"],
                    max_len=80,
                ),
            }
            continue

        if section == "pricing" and section not in completed:
            completed[section] = {"plans": []}

    return completed


async def _persist_landing_page_row(
    db: AsyncSession,
    *,
    experiment: Experiment,
    copy_json: dict[str, Any],
    page_json: dict[str, Any],
    template_id: str,
    refined_idea: RefinedIdea,
    input_model: LandingPageInputModel,
    page_goal: str,
    edited_doc_version: int | None = None,
) -> LandingPage:
    """UPDATE or INSERT LandingPage with copy_json and page_json."""
    existing = await _fetch_landing_page_row(db, experiment.id)
    resolved_tid = resolve_template_id(template_id)
    display_name = (
        experiment.name.strip()
        if experiment.name and experiment.name.strip()
        else resolve_name_from_refined(refined_idea)
    )
    page_json = sync_landing_page_project_name(page_json, display_name)
    # Stamp VR edited_doc_version at generation; 0 when overlay never persisted.
    stamped_edited_doc_version = (
        0 if edited_doc_version is None else edited_doc_version
    )

    if existing is not None:
        existing.copy_json = copy_json
        existing.page_json = page_json
        existing.template_id = resolved_tid
        from app.services.spark_version_service import get_latest_spark_version_id

        existing.spark_version_id = await get_latest_spark_version_id(db, experiment.id)
        existing.refined_idea_version = experiment.refined_idea_version
        existing.edited_doc_version = stamped_edited_doc_version
        row = existing
    else:
        scalars = _scalar_fields_for_insert(
            copy_json=copy_json,
            refined_idea=refined_idea,
            input_model=input_model,
            page_goal=page_goal,
        )
        from app.services.spark_version_service import get_latest_spark_version_id

        row = LandingPage(
            experiment_id=experiment.id,
            template_id=resolved_tid,
            palette_id="default",
            font_pair_id="default",
            density=LandingDensity.ROOMY,
            slug=await _generate_unique_slug(db, experiment),
            copy_json=copy_json,
            page_json=page_json,
            spark_version_id=await get_latest_spark_version_id(db, experiment.id),
            refined_idea_version=experiment.refined_idea_version,
            edited_doc_version=stamped_edited_doc_version,
            **scalars,
        )
        db.add(row)

    return row


async def generate_landing_page(
    db: AsyncSession,
    experiment_id: UUID,
    page_goal: str = "waitlist",
    template_id: str = "dark-premium",
    regeneration_hint: str | None = None,
) -> None:
    """Run the 2-LLM + 1-Python landing page pipeline for an experiment.

    Pipeline:
      1. Fetch ValidationReport (raise MissingValidationReportError if missing).
      2. Fetch Experiment and parse RefinedIdea.
      3. Call strategist LLM (lp_strategist_v1) → StrategistOutput.
      4. Call copy LLM (lp_copy_v1) → CopyOutput.
      5. Apply theme_to_page_json() with TEMPLATES[template_id].
      6. Persist copy_json + page_json on LandingPage (UPDATE or INSERT).
         Caller commits the transaction.

    Does NOT change Experiment.status.

    Raises:
      MissingValidationReportError — no ValidationReport for the experiment.
      LandingPageGenerationError — missing experiment/refined_idea or LLM failure.
    """
    settings = get_settings()
    provider, model = _landing_page_provider_and_model(settings)
    typed_provider = cast(llm_client.ProviderName, provider)

    vr_bundle = await _fetch_validation_report(db, experiment_id)
    vr = vr_bundle.report
    edited_narrative = vr_bundle.edited_narrative
    experiment = await _fetch_experiment(db, experiment_id)
    refined_idea = _parse_refined_idea(experiment)

    resolved_template_id = resolve_template_id(template_id)
    is_regeneration = bool(regeneration_hint and regeneration_hint.strip())

    try:
        strategist_output, strategist_result = await llm_client.complete_structured(
            db,
            provider=typed_provider,
            model=model,
            prompt_name=LP_STRATEGIST_PROMPT_NAME,
            system=LP_STRATEGIST_SYSTEM_PROMPT,
            user=build_lp_strategist_user_prompt(
                vr,
                refined_idea,
                page_goal,
                regeneration_hint=regeneration_hint,
                edited_narrative=edited_narrative,
                for_cache=not is_regeneration,
            ),
            response_model=StrategistOutput,
            max_tokens=_LP_STRATEGIST_MAX_TOKENS,
            temperature=_LP_TEMPERATURE,
            experiment_id=experiment_id,
            phase="landing_page",
            cache_breakpoints=[]
            if is_regeneration
            else LP_STRATEGIST_CACHE_BREAKPOINTS,
        )

        copy_output, copy_result = await llm_client.complete_structured(
            db,
            provider=typed_provider,
            model=model,
            prompt_name=LP_COPY_PROMPT_NAME,
            system=LP_COPY_SYSTEM_PROMPT,
            user=build_lp_copy_user_prompt(
                strategist_output.input_model,
                strategist_output.strategy,
                regeneration_hint=regeneration_hint,
                for_cache=not is_regeneration,
            ),
            response_model=CopyOutput,
            max_tokens=_LP_COPY_MAX_TOKENS,
            temperature=_LP_TEMPERATURE,
            experiment_id=experiment_id,
            phase="landing_page",
            cache_breakpoints=[] if is_regeneration else LP_COPY_CACHE_BREAKPOINTS,
        )
    except LandingPageGenerationError:
        raise
    except Exception as exc:
        raise LandingPageGenerationError(
            f"Landing page LLM call failed for experiment {experiment_id}"
        ) from exc

    page_json = theme_to_page_json(
        TEMPLATES[resolved_template_id],
        copy_output.copy_json,
        strategist_output.strategy,
        resolved_template_id,
    )
    page_json["meta"] = {
        "generation_id": uuid4().hex,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "regeneration_hint": regeneration_hint,
    }

    copy_json = copy_output.model_dump(mode="json")["copy_json"]
    copy_json = _ensure_complete_copy_json(
        copy_json=copy_json,
        strategy=strategist_output.strategy,
        input_model=strategist_output.input_model,
        refined_idea=refined_idea,
    )
    copy_json = _scrub_competitor_names_from_copy(
        copy_json,
        strategist_output.input_model.positioning_intelligence.competitors,
    )

    await _persist_landing_page_row(
        db,
        experiment=experiment,
        copy_json=copy_json,
        page_json=page_json,
        template_id=resolved_template_id,
        refined_idea=refined_idea,
        input_model=strategist_output.input_model,
        page_goal=page_goal,
        edited_doc_version=(
            0
            if edited_narrative is None
            else (vr_bundle.edited_doc_version or 0)
        ),
    )
    await db.flush()

    total_cost: Decimal = strategist_result.cost_usd + copy_result.cost_usd
    total_latency_ms = strategist_result.latency_ms + copy_result.latency_ms
    section_count = len(strategist_output.strategy.section_sequence)

    _logger.info(
        "landing page generated",
        experiment_id=str(experiment_id),
        section_count=section_count,
        template_id=resolved_template_id,
        cost_usd=str(total_cost),
        latency_ms=total_latency_ms,
        strategist_latency_ms=strategist_result.latency_ms,
        copy_latency_ms=copy_result.latency_ms,
    )
