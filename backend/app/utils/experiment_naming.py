"""Helpers for experiment display names (dashboard, sidebar, landing pages)."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.experiment import Experiment
from app.db.models.landing_page import LandingPage
from app.schemas.refinement import RefinedIdea

_NAME_MAX_LEN = 100
_SLUG_MAX_LEN = 28
_SLUG_MIN_LEN = 6
LANDING_SLUG_RE = re.compile(r"^[a-z0-9-]{6,40}$")


def get_experiment_display_name(experiment: Experiment) -> str:
    """Display name for dashboards and search results."""
    if experiment.name and experiment.name.strip():
        return experiment.name.strip()
    raw = (experiment.raw_idea or "").strip()
    if not raw:
        return "Untitled project"
    if len(raw) <= 50:
        return raw
    return f"{raw[:50]}…"


def normalize_experiment_name(name: str | None) -> str | None:
    """Trim and validate a user-supplied name. Empty strings become None."""
    if name is None:
        return None
    stripped = name.strip()
    if not stripped:
        return None
    return stripped[:_NAME_MAX_LEN]


def resolve_name_from_refined(refined: RefinedIdea) -> str:
    """Derive a display name from structured refinement output."""
    if refined.project_name and refined.project_name.strip():
        return refined.project_name.strip()[:_NAME_MAX_LEN]

    one_liner = refined.refined_one_liner.strip()
    if not one_liner:
        return "Untitled project"
    if len(one_liner) <= 60:
        return one_liner

    truncated = one_liner[:60]
    last_space = truncated.rfind(" ")
    if last_space > 20:
        truncated = truncated[:last_space]
    return truncated.rstrip(".,;:")


def apply_llm_name_if_unset(experiment: Experiment, refined: RefinedIdea) -> None:
    """Set experiment.name from refinement when the founder did not provide one."""
    if experiment.name and experiment.name.strip():
        return
    experiment.name = resolve_name_from_refined(refined)


def sync_landing_page_project_name(
    page_json: dict | None,
    project_name: str,
) -> dict:
    """Merge project_name into landing page publish metadata."""
    base = dict(page_json) if isinstance(page_json, dict) else {}
    publish = base.get("publish")
    if not isinstance(publish, dict):
        publish = {}
    else:
        publish = dict(publish)
    publish["project_name"] = project_name
    base["publish"] = publish
    return base


def slugify_for_url(text: str, max_len: int = _SLUG_MAX_LEN) -> str:
    """Convert a project name to a short URL-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    s = s.strip("-")
    return s[:max_len].rstrip("-")


def normalize_landing_slug(slug: str) -> str:
    """Lowercase and trim a slug candidate."""
    return slug.strip().lower()


def validate_landing_slug(slug: str) -> str:
    """Validate slug format per public route rules. Raises ValueError if invalid."""
    normalized = normalize_landing_slug(slug)
    if not LANDING_SLUG_RE.match(normalized):
        raise ValueError(
            "Slug must be 6–40 characters, lowercase letters, numbers, and hyphens only."
        )
    return normalized


def resolve_slug_base_from_experiment(experiment: Experiment) -> str:
    """Derive a short slug base from user/AI project name — never raw idea or headline."""
    if experiment.name and experiment.name.strip():
        base = slugify_for_url(experiment.name.strip())
        if len(base) >= _SLUG_MIN_LEN:
            return base

    if experiment.refined_idea and isinstance(experiment.refined_idea, dict):
        project_name = experiment.refined_idea.get("project_name")
        if project_name and str(project_name).strip():
            base = slugify_for_url(str(project_name).strip())
            if len(base) >= _SLUG_MIN_LEN:
                return base
        try:
            refined = RefinedIdea.model_validate(experiment.refined_idea)
            base = slugify_for_url(resolve_name_from_refined(refined))
            if len(base) >= _SLUG_MIN_LEN:
                return base
        except Exception:
            pass

    return ""


async def ensure_unique_landing_slug(
    db: AsyncSession,
    base_slug: str,
    *,
    experiment_id: UUID,
    exclude_landing_page_id: UUID | None = None,
) -> str:
    """Return a collision-free slug, appending a short suffix when needed."""
    from uuid import uuid4

    candidate = base_slug
    for _ in range(5):
        stmt = select(LandingPage).where(LandingPage.slug == candidate)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None or (
            exclude_landing_page_id is not None
            and existing.id == exclude_landing_page_id
        ):
            return candidate
        suffix = uuid4().hex[:4]
        trimmed = base_slug[: _SLUG_MAX_LEN - 5].rstrip("-")
        candidate = f"{trimmed}-{suffix}"

    return f"lp-{experiment_id.hex[:12]}"
