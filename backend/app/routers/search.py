"""Global experiment search for authenticated users."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.db.session import get_session
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.tags import SearchResult
from app.utils.experiment_naming import get_experiment_display_name

router = APIRouter(prefix="/search", tags=["search"])


def _snippet(text: str, query: str, max_len: int = 120) -> str:
    lowered = text.lower()
    idx = lowered.find(query.lower())
    if idx < 0:
        return text[:max_len] + ("…" if len(text) > max_len else "")
    start = max(0, idx - 30)
    end = min(len(text), idx + len(query) + 60)
    chunk = text[start:end].strip()
    if start > 0:
        chunk = f"…{chunk}"
    if end < len(text):
        chunk = f"{chunk}…"
    return chunk


@router.get("", response_model=list[SearchResult])
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def search_experiments(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str, Query(min_length=2)],
    limit: Annotated[int, Query(le=25)] = 10,
) -> list[SearchResult]:
    """Global search across the user's experiments."""
    pattern = f"%{q}%"
    tags_text = func.array_to_string(Experiment.tags, " ")
    recommendation = cast(ValidationReport.raw_report["overall_recommendation"], String)

    stmt = (
        select(Experiment)
        .outerjoin(ValidationReport, ValidationReport.experiment_id == Experiment.id)
        .where(
            Experiment.user_id == current_user.id,
            Experiment.status != ExperimentStatus.ARCHIVED,
            or_(
                Experiment.name.ilike(pattern),
                Experiment.raw_idea.ilike(pattern),
                tags_text.ilike(pattern),
                recommendation.ilike(pattern),
                cast(Experiment.refined_idea["refined_one_liner"], String).ilike(pattern),
            ),
        )
        .options(selectinload(Experiment.validation_report))
        .order_by(Experiment.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    experiments = list(result.scalars().unique().all())

    items: list[SearchResult] = []
    for experiment in experiments:
        title = get_experiment_display_name(experiment)
        matched_field = "title"
        snippet_source = title
        q_lower = q.lower()

        if experiment.name and q_lower in experiment.name.lower():
            matched_field = "title"
            snippet_source = experiment.name
        elif experiment.tags and any(q_lower in tag.lower() for tag in experiment.tags):
            matched_field = "tags"
            snippet_source = ", ".join(experiment.tags)
        elif experiment.refined_idea and isinstance(experiment.refined_idea, dict):
            one_liner = str(experiment.refined_idea.get("refined_one_liner", ""))
            if q_lower in one_liner.lower():
                matched_field = "refined_idea"
                snippet_source = one_liner
        elif q_lower in experiment.raw_idea.lower():
            matched_field = "raw_idea"
            snippet_source = experiment.raw_idea
        elif (
            experiment.validation_report is not None
            and experiment.validation_report.raw_report.get("overall_recommendation")
            and q_lower
            in str(experiment.validation_report.raw_report["overall_recommendation"]).lower()
        ):
            matched_field = "recommendation"
            snippet_source = str(
                experiment.validation_report.raw_report["overall_recommendation"]
            )
        else:
            snippet_source = title or experiment.raw_idea

        items.append(
            SearchResult(
                id=str(experiment.id),
                title=title,
                snippet=_snippet(snippet_source, q),
                matched_field=matched_field,
                status=experiment.status.value,
            )
        )
    return items
