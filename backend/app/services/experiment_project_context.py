"""Lean experiment project-context summary for universal chat prompts.

Returns presence flags + short idea fields only — no report bodies, landing
copy, or message history. Contrast with ``build_experiment_discussion_context``
which compresses full validation-report content for post-research discuss mode.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.schemas.refinement import RefinedIdea

_RAW_IDEA_MAX = 500


@dataclass(frozen=True)
class ExperimentProjectContext:
    """Terse "where is this experiment right now" summary for the coach prompt."""

    experiment_id: str
    status: str
    current_act: str
    name: str | None
    raw_idea: str | None
    refined_one_liner: str | None
    target_audience: str | None
    has_validation_report: bool
    has_landing_page: bool
    has_insight_report: bool

    def to_prompt_block(self) -> str:
        """Render as terse markdown for the LLM project_context section."""
        lines = [
            f"status: {self.status}",
            f"current_act: {self.current_act}",
        ]
        if self.name:
            lines.append(f"project_name: {self.name}")
        if self.raw_idea:
            lines.append(f"raw_idea: {self.raw_idea}")
        if self.refined_one_liner:
            lines.append(f"refined_one_liner: {self.refined_one_liner}")
        if self.target_audience:
            lines.append(f"target_audience: {self.target_audience}")
        lines.append(f"has_validation_report: {str(self.has_validation_report).lower()}")
        lines.append(f"has_landing_page: {str(self.has_landing_page).lower()}")
        lines.append(f"has_insight_report: {str(self.has_insight_report).lower()}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)


def current_act_for_status(status: ExperimentStatus) -> str:
    """Map experiment status to the five-act journey label for coaching copy."""
    if status in {ExperimentStatus.SPARK, ExperimentStatus.DRAFT}:
        return "spark"
    if status in {ExperimentStatus.REFINING, ExperimentStatus.REFINED}:
        return "refine"
    if status in {
        ExperimentStatus.RESEARCHING,
        ExperimentStatus.RESEARCH_PLANNING,
        ExperimentStatus.RESEARCH_SEARCHING,
        ExperimentStatus.RESEARCH_READING,
        ExperimentStatus.RESEARCH_REFLECTING,
        ExperimentStatus.RESEARCH_VOICES,
        ExperimentStatus.RESEARCH_SYNTHESIZING,
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.RESEARCH_FAILED,
    }:
        return "evidence"
    if status in {
        ExperimentStatus.LANDING_GENERATING,
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
    }:
        return "launch"
    if status in {
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.ANALYZING,
        ExperimentStatus.COMPLETED,
    }:
        return "signal"
    if status == ExperimentStatus.ARCHIVED:
        return "archived"
    return "spark"


def _truncate(text: str, max_len: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


async def get_experiment_project_context(
    db: AsyncSession,
    experiment: Experiment,
) -> ExperimentProjectContext:
    """Load lean presence + idea fields for an already-owned experiment row.

    Re-fetches with selectinload so callers do not need to eager-load relations.
    Does not load report JSON, landing copy, or chat history.
    """
    result = await db.execute(
        select(Experiment)
        .options(
            selectinload(Experiment.validation_report),
            selectinload(Experiment.landing_page),
            selectinload(Experiment.insight_report),
        )
        .where(Experiment.id == experiment.id)
    )
    exp = result.scalar_one()

    refined_one_liner: str | None = None
    target_audience: str | None = None
    if exp.refined_idea:
        idea = RefinedIdea.model_validate(exp.refined_idea)
        refined_one_liner = idea.refined_one_liner.strip() or None
        target_audience = idea.target_audience.strip() or None

    raw = exp.raw_idea.strip() if exp.raw_idea else ""
    raw_idea = _truncate(raw, _RAW_IDEA_MAX) if raw else None

    return ExperimentProjectContext(
        experiment_id=str(exp.id),
        status=exp.status.value,
        current_act=current_act_for_status(exp.status),
        name=(exp.name.strip() if exp.name else None) or None,
        raw_idea=raw_idea,
        refined_one_liner=refined_one_liner,
        target_audience=target_audience,
        has_validation_report=exp.validation_report is not None,
        has_landing_page=exp.landing_page is not None,
        has_insight_report=exp.insight_report is not None,
    )
