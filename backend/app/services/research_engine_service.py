"""State machine wrapper for the research engine pipeline (B2.4 / ADR 0009).

This module is the single owner of the RESEARCHING → RESEARCH_READY (or
RESEARCH_FAILED) state transitions.  It is called by InProcessDispatcher and
will be called by the Cloud Function wrapper in B3.

State machine (B3 Reader + Reflector + Voices):
    RESEARCHING → RESEARCH_PLANNING → RESEARCH_SEARCHING
                → RESEARCH_READING → RESEARCH_REFLECTING → RESEARCH_VOICES
                → RESEARCH_SYNTHESIZING → RESEARCH_READY

On any unrecoverable error:
    → RESEARCH_FAILED  (with sanitized research_error_detail)

Per AGENTS.md «Logging hygiene»:
    - NEVER log ValidationReport content, RefinedIdea content, Tavily results
    - Log only safe aggregate metadata (counts, costs, recommendation enum)
    - research_error_detail must be scrubbed of secrets before writing to DB

Per ARCHITECTURE.md:
    - All DB mutations via SQLAlchemy 2.0 style (select / update / insert)
    - One session per pipeline run — not per HTTP request
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.validation_report import ValidationReport
from app.logging_config import get_logger
from app.services.research_dev_capture import dev_capture_write

_logger = get_logger(__name__)
_slog = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Secrets that must never appear in research_error_detail.
# These are the env-var NAMES for the keys we want to redact — the actual
# key values are pulled from the running process environment to build the
# redaction set at module load time.
# ---------------------------------------------------------------------------
_SECRET_ENV_NAMES = [
    "ANTHROPIC_API_KEY",
    "TAVILY_API_KEY",
    "GROQ_API_KEY",
    "DATABASE_URL",
    "FIREBASE_PROJECT_ID",
    "RESEARCH_ENGINE_URL",
]

# Max length of the error detail written to the DB column.
_MAX_ERROR_DETAIL_LEN = 500


def _build_redaction_set() -> set[str]:
    """Collect actual secret VALUES from the environment for redaction.

    Only includes values with >8 chars (avoids redacting short strings like
    project names that happen to appear in error messages).
    """
    import os  # noqa: PLC0415 — deferred to keep module import fast

    values: set[str] = set()
    for name in _SECRET_ENV_NAMES:
        val = os.environ.get(name, "")
        if val and len(val) > 8:
            values.add(val)
    return values


def _sanitize_error_detail(phase: str, exc: Exception) -> str:
    """Build a sanitized error string safe to write to the DB and return in APIs.

    Format: "{phase}:{ExceptionType}: {truncated message}"

    Redacts:
    - Known secret values (API keys, DB URL) from the message
    - Any string matching a key-like pattern (long alphanumeric + symbols)
    - Stack traces are not included — only the exception type and message

    The result is truncated to _MAX_ERROR_DETAIL_LEN characters.
    """
    raw_msg = str(exc)

    # Redact known secret values first.
    redaction_set = _build_redaction_set()
    for secret in redaction_set:
        if secret in raw_msg:
            raw_msg = raw_msg.replace(secret, "[REDACTED]")

    # Redact anything that looks like an API key (long token-like strings).
    # Pattern: 20+ consecutive non-whitespace characters mixing alnum + symbols.
    raw_msg = re.sub(r"[A-Za-z0-9_\-]{32,}", "[REDACTED]", raw_msg)

    detail = f"{phase}:{type(exc).__name__}: {raw_msg}"
    return detail[:_MAX_ERROR_DETAIL_LEN]


# ---------------------------------------------------------------------------
# State transition helpers
# ---------------------------------------------------------------------------


async def _set_status(
    session: AsyncSession,
    experiment_id: UUID,
    new_status: ExperimentStatus,
    *,
    error_detail: str | None = None,
) -> None:
    """Write a status transition and flush within the current session.

    Does NOT commit — the caller controls commit boundaries.
    Logs the transition at INFO level with structured fields.
    """
    updates: dict[str, object] = {"status": new_status}
    if error_detail is not None:
        updates["research_error_detail"] = error_detail

    await session.execute(
        update(Experiment)
        .where(Experiment.id == experiment_id)
        .values(**updates)
    )
    await session.flush()

    _slog.info(
        "research state transition",
        experiment_id=str(experiment_id),
        new_status=new_status,
        has_error_detail=error_detail is not None,
    )


async def _write_validation_report(
    session: AsyncSession,
    experiment_id: UUID,
    raw_report: dict,
    *,
    reflection_loops_used: int = 0,
    spark_version_id: UUID | None = None,
) -> None:
    """Upsert a ValidationReport row with the raw_report payload.

    Uses INSERT … ON CONFLICT (experiment_id) DO UPDATE so it is idempotent —
    safe to retry on transient failures after partial writes.

    B2.4 writes:
        raw_report = verbatim Pydantic model dict
        clarity_score = None  (B3 synthesizer prompt will populate)
        reflection_loops_used — refinement waves with ≥1 successful Tavily re-search
        generated_at = now()
        spark_version_id — Spark snapshot this report was generated against
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: PLC0415

    stmt = pg_insert(ValidationReport).values(
        experiment_id=experiment_id,
        raw_report=raw_report,
        clarity_score=None,
        reflection_loops_used=reflection_loops_used,
        generated_at=datetime.now(UTC),
        spark_version_id=spark_version_id,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["experiment_id"],
        set_={
            "raw_report": stmt.excluded.raw_report,
            "clarity_score": stmt.excluded.clarity_score,
            "reflection_loops_used": stmt.excluded.reflection_loops_used,
            "generated_at": stmt.excluded.generated_at,
            "spark_version_id": stmt.excluded.spark_version_id,
        },
    )
    await session.execute(stmt)
    await session.flush()


# ---------------------------------------------------------------------------
# Public entry point — called by InProcessDispatcher.dispatch
# ---------------------------------------------------------------------------


async def run_research_engine_pipeline(
    experiment_id: UUID,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """Run the full research pipeline for an experiment with state machine transitions.

    This function owns the RESEARCHING → … → RESEARCH_READY/FAILED transitions.
    It creates its own DB session (background task, not request-scoped) and
    commits each status transition atomically so the frontend polling endpoint
    always sees a consistent state.

    State machine (B3 Reader + Reflector):
        RESEARCHING → RESEARCH_PLANNING → RESEARCH_SEARCHING
                    → RESEARCH_READING → RESEARCH_REFLECTING → RESEARCH_SYNTHESIZING
                    → RESEARCH_READY

    On failure at any phase:
        → RESEARCH_FAILED (research_error_detail written, report NOT saved)

    Args:
        experiment_id: The experiment to research.
        sessionmaker:  Async session factory (from get_sessionmaker()).

    Errors:
        All exceptions are caught internally. On unexpected errors that escape
        the phase-level try/except, the experiment is set to RESEARCH_FAILED
        and the error is logged. This function never raises to its caller
        (InProcessDispatcher's done-callback handles any escape).
    """
    log = _slog.bind(experiment_id=str(experiment_id))
    log.info("pipeline starting")

    async with sessionmaker() as session:
        try:
            # ------------------------------------------------------------------
            # 0. Load the experiment and its refined_idea.
            #    If the experiment is missing or has no refined_idea, fail fast.
            # ------------------------------------------------------------------
            result = await session.execute(
                select(Experiment).where(Experiment.id == experiment_id)
            )
            experiment = result.scalar_one_or_none()
            if experiment is None:
                log.error("pipeline aborted: experiment not found")
                return  # Nothing to update — the row doesn't exist.

            if experiment.refined_idea is None:
                log.error("pipeline aborted: refined_idea is None — cannot research")
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail="pipeline:ValueError: refined_idea is None; cannot start research",
                )
                await session.commit()
                return

            # Deserialise the JSONB refined_idea into a RefinedIdea Pydantic model.
            from app.schemas.refinement import RefinedIdea  # noqa: PLC0415
            from app.schemas.targeting import ExperimentTargeting  # noqa: PLC0415
            refined_idea = RefinedIdea.model_validate(experiment.refined_idea)
            targeting = ExperimentTargeting.from_experiment(experiment)
            dev_capture_write("refined_idea.json", refined_idea)
            dev_capture_write("targeting.json", targeting)

            from app.services.spark_version_service import (  # noqa: PLC0415
                get_latest_spark_version_id,
            )

            spark_version_id = await get_latest_spark_version_id(session, experiment_id)

            # ------------------------------------------------------------------
            # 1. RESEARCH_PLANNING — planner generates research questions.
            # ------------------------------------------------------------------
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_PLANNING)
            await session.commit()

            from app.services.planner_service import plan_research  # noqa: PLC0415
            try:
                research_plan = await plan_research(
                    db=session,
                    refined_idea=refined_idea,
                    experiment_id=experiment_id,
                    targeting=targeting,
                )
            except Exception as exc:
                detail = _sanitize_error_detail("planner", exc)
                log.error("pipeline failed at planner", error_type=type(exc).__name__)
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
                return

            log.info(
                "pipeline phase complete",
                phase="planner",
                question_count=len(research_plan.questions),
            )
            dev_capture_write("research_plan.json", research_plan)

            # ------------------------------------------------------------------
            # 2. RESEARCH_SEARCHING — searcher executes the research plan.
            # ------------------------------------------------------------------
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_SEARCHING)
            await session.commit()

            from app.schemas.search import MergedSearchResults  # noqa: PLC0415
            from app.services.searcher_service import (  # noqa: PLC0415
                SearcherFailure,
                execute_search_plan,
            )
            try:
                merged: MergedSearchResults = await execute_search_plan(
                    db=session,
                    research_plan=research_plan,
                    experiment_id=experiment_id,
                    refined_idea=refined_idea,
                    targeting=targeting,
                )
            except (SearcherFailure, Exception) as exc:
                detail = _sanitize_error_detail("searcher", exc)
                log.error("pipeline failed at searcher", error_type=type(exc).__name__)
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
                return

            # Persist Tavily/Trends ExternalAPICall rows before later phases can fail.
            await session.commit()

            search_results = merged.tavily
            trends_signals = merged.trends

            total_results = sum(len(v) for v in search_results.values())
            log.info(
                "pipeline phase complete",
                phase="searcher",
                total_tavily_results=total_results,
            )
            dev_capture_write("search_results.json", search_results)

            # ------------------------------------------------------------------
            # 3. RESEARCH_READING — reader extracts structured evidence per question.
            # ------------------------------------------------------------------
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_READING)
            await session.commit()

            log.info(
                "reader phase started",
                experiment_id=str(experiment_id),
                question_count=len(research_plan.questions),
            )

            from app.config import get_settings  # noqa: PLC0415
            from app.services.reader_service import (  # noqa: PLC0415
                ReaderTotalFailure,
                execute_reader,
            )

            settings = get_settings()

            try:
                reader_outputs = await execute_reader(
                    experiment_id=experiment_id,
                    research_questions=research_plan.questions,
                    search_results_by_question=search_results,
                    db=session,
                    settings=settings,
                )
            except ReaderTotalFailure as exc:
                detail = _sanitize_error_detail("reader", exc)
                log.error(
                    "reader phase failed",
                    experiment_id=str(experiment_id),
                    error_type=type(exc).__name__,
                )
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
                return
            except Exception as exc:
                detail = _sanitize_error_detail("reader", exc)
                log.error("pipeline failed at reader", error_type=type(exc).__name__)
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
                return

            total_extracted_evidence = sum(
                len(ro.extracted_evidence) for ro in reader_outputs.values()
            )
            log.info(
                "reader phase completed",
                experiment_id=str(experiment_id),
                total_extracted_evidence=total_extracted_evidence,
            )
            dev_capture_write("reader_outputs.json", reader_outputs)

            # ------------------------------------------------------------------
            # 4. RESEARCH_REFLECTING — evidence sufficiency + optional re-search/re-read.
            # ------------------------------------------------------------------
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_REFLECTING)
            await session.commit()

            from app.services.reflector_service import execute_reflector  # noqa: PLC0415

            # Reflector NEVER raises into the orchestrator per planning §6.
            # On any internal failure, returns original inputs unchanged.
            reader_outputs, search_results, reflector_summary = await execute_reflector(
                experiment_id=experiment_id,
                research_plan=research_plan,
                reader_outputs=reader_outputs,
                search_results=search_results,
                db=session,
                settings=settings,
            )

            await session.commit()

            dev_capture_write("reflected_outputs.json", reader_outputs)
            dev_capture_write("evidence_analysis.json", reflector_summary.evidence_analysis)

            # ------------------------------------------------------------------
            # 4c. RESEARCH_VOICES — Reddit-based qualitative evidence.
            # Soft-fails: never crashes the pipeline. Empty VoicesOutput on failure.
            # ------------------------------------------------------------------
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_VOICES)
            await session.commit()

            from app.schemas.voices import VoicesOutput  # noqa: PLC0415
            from app.services.voices_service import execute_voices  # noqa: PLC0415

            try:
                voices_output = await execute_voices(
                    db=session,
                    refined_idea=refined_idea,
                    research_plan=research_plan,
                    targeting=targeting,
                    experiment_id=experiment_id,
                    settings=settings,
                )
            except Exception as exc:
                log.warning(
                    "voices phase raised unexpectedly",
                    error_type=type(exc).__name__,
                )
                voices_output = VoicesOutput(
                    atoms=[],
                    skipped_reason="voices_service_raised",
                )

            await session.commit()

            log.info(
                "voices phase complete",
                voice_atom_count=len(voices_output.atoms),
                subreddits_searched=len(voices_output.subreddits_searched),
                threads_fetched=voices_output.threads_fetched,
                comments_fetched=voices_output.comments_fetched,
                skipped_reason=voices_output.skipped_reason,
            )

            # ------------------------------------------------------------------
            # 4b. REASONING — business construction intelligence (deterministic).
            #     Runs inside RESEARCH_SYNTHESIZING boundary before Synthesizer LLM.
            # ------------------------------------------------------------------
            from app.services.reasoning_engine_service import execute_reasoning_engine

            evidence_analysis = reflector_summary.evidence_analysis
            reasoning_output = None
            if evidence_analysis is not None:
                reasoning_output = execute_reasoning_engine(
                    refined_idea=refined_idea,
                    evidence_analysis=evidence_analysis,
                )
            dev_capture_write("reasoning_output.json", reasoning_output)

            # ------------------------------------------------------------------
            # 5. RESEARCH_SYNTHESIZING — synthesizer communicates reasoning → report.
            # ------------------------------------------------------------------
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_SYNTHESIZING)
            await session.commit()

            from app.services.research_engine import RUBRIC_VERSION_DEFAULT  # noqa: PLC0415
            from app.services.synthesizer_input import (  # noqa: PLC0415
                build_citation_hydration_index,
                build_synthesizer_input,
            )
            from app.services.synthesizer_service import (  # noqa: PLC0415
                SynthesizerHallucinatedCitation,
                synthesize_report,
            )

            # Build SynthesizerInput from Reader output + Reasoning Engine output.
            synth_input = build_synthesizer_input(
                refined_idea=refined_idea,
                research_plan=research_plan,
                reader_outputs=reader_outputs,
                rubric_version=RUBRIC_VERSION_DEFAULT,
                trends_signals=trends_signals,
                evidence_analysis=evidence_analysis,
                reasoning_output=reasoning_output,
                targeting=targeting,
                voices_output=voices_output,
                experiment_id=experiment_id,
            )

            # Build the hydration index from Searcher results — used by _hydrate_draft
            # server-side to populate Citation.title and Citation.source_domain. NEVER
            # serialized into the LLM prompt. Per ADR 0012.
            # CRITICAL: Re-build after Reflector so new Tavily rows from any re-search
            # are covered (planning §7).
            citation_hydration_index = build_citation_hydration_index(search_results)

            try:
                report = await synthesize_report(
                    db=session,
                    synth_input=synth_input,
                    citation_hydration_index=citation_hydration_index,
                    experiment_id=experiment_id,
                )
            except SynthesizerHallucinatedCitation as exc:
                detail = _sanitize_error_detail("synthesizer", exc)
                log.error(
                    "synthesizer phase failed",
                    experiment_id=str(experiment_id),
                    error_type=type(exc).__name__,
                )
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
                return
            except Exception as exc:
                detail = _sanitize_error_detail("synthesizer", exc)
                log.error("pipeline failed at synthesizer", error_type=type(exc).__name__)
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
                return

            # ------------------------------------------------------------------
            # 6. Persist the report and transition to RESEARCH_READY.
            # ------------------------------------------------------------------
            raw_report_dict = report.model_dump(mode="json")
            await _write_validation_report(
                session,
                experiment_id,
                raw_report_dict,
                reflection_loops_used=reflector_summary.waves_used,
                spark_version_id=spark_version_id,
            )
            await _set_status(session, experiment_id, ExperimentStatus.RESEARCH_READY)
            await session.commit()

            total_citations = sum(
                len(f.citations)
                for qf in report.questions_and_findings
                for f in qf.findings
            )
            log.info(
                "pipeline completed",
                total_tavily_results=total_results,
                total_citations=total_citations,
                recommendation=report.overall_recommendation,
            )

        except Exception as exc:
            # Catch-all: unexpected bug that escaped the phase-level handlers.
            # Log the type only — message may contain secrets.
            log.error(
                "pipeline unexpected failure",
                error_type=type(exc).__name__,
            )
            try:
                detail = _sanitize_error_detail("pipeline", exc)
                await _set_status(
                    session, experiment_id, ExperimentStatus.RESEARCH_FAILED,
                    error_detail=detail,
                )
                await session.commit()
            except Exception as commit_exc:
                # If even the failure write fails, log and give up.
                log.error(
                    "pipeline failed to write RESEARCH_FAILED status",
                    error_type=type(commit_exc).__name__,
                )
