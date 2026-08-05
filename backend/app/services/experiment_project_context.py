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
from app.services.spark_version_service import (
    SparkPhaseVersionInfo,
    fetch_spark_phase_version_info,
)

_RAW_IDEA_MAX = 500


@dataclass(frozen=True)
class ExperimentProjectContext:
    """Terse "where is this experiment right now" summary for the coach prompt."""

    experiment_id: str
    status: str
    current_act: str
    name: str | None
    raw_idea: str | None
    # True once original_idea has been write-once captured.
    has_original_idea: bool
    original_idea: str | None
    idea_theme: str | None
    refined_one_liner: str | None
    target_audience: str | None
    has_validation_report: bool
    has_landing_page: bool
    has_insight_report: bool
    spark_version_current: int
    refined_idea_version: int
    refine_is_stale: bool
    evidence_is_stale: bool
    launch_is_stale: bool
    insight_is_stale: bool
    # Pre-rendered STALENESS line for the prompt; None when nothing is stale.
    staleness_line: str | None = None
    # UI open phase from the canvas overlay (client-supplied); None when closed.
    current_open_phase: str | None = None

    def to_prompt_block(self) -> str:
        """Render as terse markdown for the LLM project_context section."""
        lines = [
            f"status: {self.status}",
            f"current_act: {self.current_act}",
        ]
        if self.current_open_phase:
            lines.append(f"current_open_phase: {self.current_open_phase}")
        else:
            lines.append("current_open_phase: null")
        if self.name:
            lines.append(f"project_name: {self.name}")
        lines.append(f"has_original_idea: {str(self.has_original_idea).lower()}")
        if self.original_idea:
            lines.append(f"original_idea: {self.original_idea}")
        if self.idea_theme:
            lines.append(f"idea_theme: {self.idea_theme}")
        if self.raw_idea:
            lines.append(f"raw_idea: {self.raw_idea}")
        if self.refined_one_liner:
            lines.append(f"refined_one_liner: {self.refined_one_liner}")
        if self.target_audience:
            lines.append(f"target_audience: {self.target_audience}")
        lines.append(f"has_validation_report: {str(self.has_validation_report).lower()}")
        lines.append(f"has_landing_page: {str(self.has_landing_page).lower()}")
        lines.append(f"has_insight_report: {str(self.has_insight_report).lower()}")
        lines.append(f"spark_version_current: {self.spark_version_current}")
        lines.append(f"refined_idea_version: {self.refined_idea_version}")
        if self.staleness_line:
            lines.append(self.staleness_line)
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


def _format_staleness_line(info: SparkPhaseVersionInfo) -> str | None:
    """Compact STALENESS note for the coach prompt, or None when all fresh."""
    phase_labels: list[str] = []
    reasons: set[str] = set()
    if info.refine_is_stale:
        phase_labels.append("refine")
        reasons.update(info.refine_stale_reasons)
    if info.evidence_is_stale:
        phase_labels.append("evidence")
        reasons.update(info.evidence_stale_reasons)
    if info.launch_is_stale:
        phase_labels.append("launch")
        reasons.update(info.launch_stale_reasons)
    if info.signal_is_stale:
        phase_labels.append("insight")
        reasons.update(info.signal_stale_reasons)

    if not phase_labels:
        return None

    if "spark" in reasons and "refined_idea" in reasons:
        changed = "both"
    elif "refined_idea" in reasons:
        changed = "refined idea"
    elif "spark" in reasons:
        changed = "spark"
    else:
        changed = "upstream inputs"

    phases = " / ".join(phase_labels)
    return (
        "STALENESS: The user has changed "
        f"{changed} since generating {phases}. "
        "Any content from that phase reflects the older version. "
        "When answering research questions while evidence is stale, "
        "lead with a clear honest flag that the report predates the latest "
        "idea change before citing findings."
    )


async def get_experiment_project_context(
    db: AsyncSession,
    experiment: Experiment,
    *,
    current_open_phase: str | None = None,
) -> ExperimentProjectContext:
    """Load lean presence + idea fields for an already-owned experiment row.

    Re-fetches with selectinload so callers do not need to eager-load relations.
    Does not load report JSON, landing copy, or chat history.

    ``current_open_phase`` is the canvas overlay act from the client (or None).
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

    has_original_idea = exp.original_idea is not None
    original = exp.original_idea.strip() if exp.original_idea else ""
    original_idea = _truncate(original, _RAW_IDEA_MAX) if original else None
    idea_theme = (exp.idea_theme.strip().lower() if exp.idea_theme else None) or None

    phase_info = await fetch_spark_phase_version_info(db, exp)

    return ExperimentProjectContext(
        experiment_id=str(exp.id),
        status=exp.status.value,
        current_act=current_act_for_status(exp.status),
        name=(exp.name.strip() if exp.name else None) or None,
        raw_idea=raw_idea,
        has_original_idea=has_original_idea,
        original_idea=original_idea,
        idea_theme=idea_theme,
        refined_one_liner=refined_one_liner,
        target_audience=target_audience,
        has_validation_report=exp.validation_report is not None,
        has_landing_page=exp.landing_page is not None,
        has_insight_report=exp.insight_report is not None,
        spark_version_current=phase_info.current_spark_version,
        refined_idea_version=phase_info.current_refined_idea_version,
        refine_is_stale=phase_info.refine_is_stale,
        evidence_is_stale=phase_info.evidence_is_stale,
        launch_is_stale=phase_info.launch_is_stale,
        insight_is_stale=phase_info.signal_is_stale,
        staleness_line=_format_staleness_line(phase_info),
        current_open_phase=current_open_phase,
    )
