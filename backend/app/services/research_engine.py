"""Research engine orchestrator — in-process 3-phase pipeline.

Chains the Planner → Searcher → Synthesizer phases end-to-end and returns
a validated ValidationReport. This is the B2.3 in-process version — it runs
entirely within the caller's process with no Cloud Function wrapping, no state
machine transitions, and no trigger endpoint.

B2.4 will wrap this in a Cloud Function and add state machine transitions.
The orchestrator's interface (run_research_engine) is designed to be callable
from both the in-process context and the Cloud Function wrapper without changes.

Per .cursorrules "Research Engine":
- asyncio + Pydantic, NOT a framework
- Each phase is a separate function with typed input/output
- Prompts in app/llm/prompts/ as named module constants

Per AGENTS.md "Logging hygiene":
- NEVER log ValidationReport content, RefinedIdea content, or Tavily content
- Log only safe aggregate metadata (counts, costs, recommendation enum)

Exception handling:
- Phase-specific failures are caught and wrapped in ResearchEngineFailure with
  phase context so callers see "research engine failed in phase=searcher" rather
  than a raw Tavily or Anthropic exception.
- SearcherFailure (total searcher failure) is also wrapped.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea
from app.schemas.validation_report import ValidationReport
from app.services.planner_service import plan_research
from app.services.searcher_service import SearcherFailure, execute_search_plan
from app.services.synthesizer_input import build_synthesizer_input
from app.services.synthesizer_service import synthesize_report

_logger = get_logger(__name__)

# Default rubric version used when the caller does not specify one.
# Bumping this version to "v2" etc. when the rubric criteria change
# ensures older reports are visibly tied to the rubric version they were
# graded against — important for longitudinal quality analysis.
RUBRIC_VERSION_DEFAULT = "v1"


class ResearchEngineFailure(Exception):
    """Raised when any phase of the research engine fails.

    Wraps the underlying exception with phase context so the caller
    (the Cloud Function trigger in B2.4, or the script in B2.3) can
    surface a meaningful error: "research engine failed in phase=searcher".

    Attributes:
        phase: The phase that failed — "planner", "searcher", or "synthesizer".
        cause: The underlying exception that caused the failure.
    """

    def __init__(self, phase: str, cause: Exception) -> None:
        self.phase = phase
        self.cause = cause
        super().__init__(
            f"Research engine failed in phase={phase!r}: "
            f"{type(cause).__name__}: {cause}"
        )


async def run_research_engine(
    db: AsyncSession,
    refined_idea: RefinedIdea,
    rubric_version: str = RUBRIC_VERSION_DEFAULT,
    experiment_id: UUID | None = None,
) -> ValidationReport:
    """Run the 3-phase research engine: Planner → Searcher → Synthesizer.

    This is the B2.3 in-process orchestrator. It runs all three phases
    sequentially within the same process and returns the fully validated
    ValidationReport. No Cloud Function wrapping, no state machine
    transitions — those are added in B2.4.

    Args:
        db: AsyncSession from the caller's context. All phase services write
            LLMCall and ExternalAPICall rows inside this session for cost tracking.
        refined_idea: Validated RefinedIdea from the refinement phase.
            The planner builds research questions from this; the synthesizer
            uses it for context in the report (target audience, risks).
        rubric_version: Version string for the ValidationReport.rubric_version_used
            field. Defaults to RUBRIC_VERSION_DEFAULT ("v1"). Pass a different
            value to run the engine against a different rubric for evaluation.
        experiment_id: FK for LLMCall/ExternalAPICall cost rollup. Pass the
            Experiment.id if available; None is valid for script-level calls.

    Returns:
        Parsed and validated ValidationReport.

    Raises:
        ResearchEngineFailure: if any phase fails. The phase attribute identifies
            which phase failed ("planner", "searcher", "synthesizer"). The cause
            attribute holds the underlying exception.
    """
    _logger.info(
        "research engine started",
        rubric_version=rubric_version,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    # -------------------------------------------------------------------------
    # Phase 1: Planner
    # -------------------------------------------------------------------------
    try:
        research_plan = await plan_research(
            db=db,
            refined_idea=refined_idea,
            experiment_id=experiment_id,
        )
    except Exception as exc:
        raise ResearchEngineFailure(phase="planner", cause=exc) from exc

    _logger.info(
        "research engine phase 1 complete",
        phase="planner",
        question_count=len(research_plan.questions),
        has_synthesizer_notes=research_plan.notes_for_synthesizer is not None,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    # -------------------------------------------------------------------------
    # Phase 2: Searcher
    # -------------------------------------------------------------------------
    try:
        search_results = await execute_search_plan(
            db=db,
            research_plan=research_plan,
            experiment_id=experiment_id,
        )
    except SearcherFailure as exc:
        raise ResearchEngineFailure(phase="searcher", cause=exc) from exc
    except Exception as exc:
        raise ResearchEngineFailure(phase="searcher", cause=exc) from exc

    total_tavily_results = sum(len(v) for v in search_results.values())
    _logger.info(
        "research engine phase 2 complete",
        phase="searcher",
        total_tavily_results=total_tavily_results,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    # -------------------------------------------------------------------------
    # Phase 3: Synthesizer
    # -------------------------------------------------------------------------
    synth_input = build_synthesizer_input(
        refined_idea=refined_idea,
        research_plan=research_plan,
        tavily_results=search_results,
        rubric_version=rubric_version,
    )

    try:
        report = await synthesize_report(
            db=db,
            synth_input=synth_input,
            experiment_id=experiment_id,
        )
    except Exception as exc:
        raise ResearchEngineFailure(phase="synthesizer", cause=exc) from exc

    # -------------------------------------------------------------------------
    # Completion logging — aggregates only, never content
    # -------------------------------------------------------------------------
    total_unique_citations = sum(
        len(f.citations)
        for qf in report.questions_and_findings
        for f in qf.findings
    )

    _logger.info(
        "research engine completed",
        phases_run=3,
        question_count=len(research_plan.questions),
        total_tavily_results=total_tavily_results,
        total_unique_citations_in_report=total_unique_citations,
        recommendation=report.overall_recommendation,
        rubric_version=rubric_version,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    return report
