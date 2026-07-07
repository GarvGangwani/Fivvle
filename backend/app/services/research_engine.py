"""Research engine orchestrator — in-process Planner → Searcher → Reader → Reflector → Synthesizer.

Chains the five phases end-to-end and returns a validated ValidationReport. Runs
entirely within the caller's process with no Cloud Function wrapping and no
experiment state machine (see research_engine_service for B2.4/B3 state machine).

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

from app.config import get_settings
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea
from app.schemas.targeting import ExperimentTargeting
from app.schemas.validation_report import ValidationReport
from app.services.planner_service import plan_research
from app.services.reader_service import ReaderTotalFailure, execute_reader
from app.services.reflector_service import execute_reflector
from app.services.searcher_service import SearcherFailure, execute_search_plan
from app.services.synthesizer_input import (
    build_citation_hydration_index,
    build_synthesizer_input,
)
from app.services.synthesizer_service import synthesize_report

_logger = get_logger(__name__)

# Default rubric version used when the caller does not specify one.
# Bumping this version to "v2" etc. when the rubric criteria change
# ensures older reports are visibly tied to the rubric version they were
# graded against — important for longitudinal quality analysis.
RUBRIC_VERSION_DEFAULT = "v1"


class ResearchEngineFailure(Exception):  # noqa: N818
    """Raised when any phase of the research engine fails.

    Wraps the underlying exception with phase context so the caller
    (the Cloud Function trigger in B2.4, or the script in B2.3) can
    surface a meaningful error: "research engine failed in phase=searcher".

    Attributes:
        phase: The phase that failed — "planner", "searcher", "reader", or "synthesizer".
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
    targeting: ExperimentTargeting | None = None,
) -> ValidationReport:
    """Run Planner → Searcher → Reader → Reflector → Synthesizer; return ValidationReport.

    In-process orchestrator (no experiment status writes). Matches the B3 pipeline
    shape used by research_engine_service (ADR 0012).

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
            which phase failed ("planner", "searcher", "reader", "synthesizer").
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
            targeting=targeting,
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
        merged = await execute_search_plan(
            db=db,
            research_plan=research_plan,
            experiment_id=experiment_id,
            refined_idea=refined_idea,
            targeting=targeting,
        )
    except SearcherFailure as exc:
        raise ResearchEngineFailure(phase="searcher", cause=exc) from exc
    except Exception as exc:
        raise ResearchEngineFailure(phase="searcher", cause=exc) from exc

    search_results = merged.tavily
    trends_signals = merged.trends

    total_tavily_results = sum(len(v) for v in search_results.values())
    _logger.info(
        "research engine phase 2 complete",
        phase="searcher",
        total_tavily_results=total_tavily_results,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    # -------------------------------------------------------------------------
    # Phase 3: Reader
    # -------------------------------------------------------------------------
    settings = get_settings()
    try:
        reader_outputs = await execute_reader(
            experiment_id=experiment_id,
            research_questions=research_plan.questions,
            search_results_by_question=search_results,
            db=db,
            settings=settings,
        )
    except ReaderTotalFailure as exc:
        raise ResearchEngineFailure(phase="reader", cause=exc) from exc
    except Exception as exc:
        raise ResearchEngineFailure(phase="reader", cause=exc) from exc

    total_extracted_evidence = sum(
        len(ro.extracted_evidence) for ro in reader_outputs.values()
    )
    _logger.info(
        "research engine reader complete",
        phase="reader",
        total_extracted_evidence=total_extracted_evidence,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    # -------------------------------------------------------------------------
    # Phase 4: Reflector (no status writes — mirrors research_engine_service)
    # -------------------------------------------------------------------------
    reader_outputs, search_results, reflector_summary = await execute_reflector(
        experiment_id=experiment_id,
        research_plan=research_plan,
        reader_outputs=reader_outputs,
        search_results=search_results,
        db=db,
        settings=settings,
    )

    # -------------------------------------------------------------------------
    # Phase 4b: Reasoning Engine (deterministic business construction)
    # -------------------------------------------------------------------------
    from app.services.reasoning_engine_service import execute_reasoning_engine

    evidence_analysis = reflector_summary.evidence_analysis
    reasoning_output = None
    if evidence_analysis is not None:
        reasoning_output = execute_reasoning_engine(
            refined_idea=refined_idea,
            evidence_analysis=evidence_analysis,
        )

    # -------------------------------------------------------------------------
    # Phase 5: Synthesizer (communication layer)
    # -------------------------------------------------------------------------
    synth_input = build_synthesizer_input(
        refined_idea=refined_idea,
        research_plan=research_plan,
        reader_outputs=reader_outputs,
        rubric_version=rubric_version,
        trends_signals=trends_signals,
        evidence_analysis=evidence_analysis,
        reasoning_output=reasoning_output,
        targeting=targeting,
        experiment_id=experiment_id,
    )
    citation_hydration_index = build_citation_hydration_index(search_results)

    try:
        report = await synthesize_report(
            db=db,
            synth_input=synth_input,
            citation_hydration_index=citation_hydration_index,
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
        phases_run=5,
        question_count=len(research_plan.questions),
        total_tavily_results=total_tavily_results,
        total_unique_citations_in_report=total_unique_citations,
        recommendation=report.overall_recommendation,
        rubric_version=rubric_version,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    return report
