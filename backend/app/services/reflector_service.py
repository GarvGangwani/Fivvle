"""Reflector phase — rule-driven decision + LLM-driven query refinement + partial
re-search + partial re-read.

Per ADR 0013 and docs/planning/b3-reflector-phase.md §§2, 4, 5, 6.

Partial Tavily fan-out mirrors ``execute_search_plan``'s asyncio.gather pattern over
(question_id, query) pairs (same depth/cap as Searcher) but is NOT a call into
``execute_search_plan``: queries come from refined LLM outputs, and failures never
raise ``SearcherFailure`` — they degrade per task (partial results).

Module-private LLM draft schema: ``_RefinedQueryListDraft``.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

import app.integrations.tavily as tavily_client
import app.llm.client as llm_client
from app.config import Settings
from app.integrations.tavily import TavilyResult
from app.llm.prompts.reflector_query_refinement import (
    PROMPT_NAME as REFINEMENT_PROMPT_NAME,
)
from app.llm.prompts.reflector_query_refinement import (
    REFLECTOR_QUERY_REFINEMENT_SYSTEM_PROMPT,
    build_reflector_query_refinement_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.planner import ResearchPlan, ResearchQuestion
from app.schemas.reader import ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.reflector import (
    QuestionReSearchSpec,
    ReflectorDecision,
    ReflectorPhaseSummary,
)

from app.services.reader_service import _load_refined_idea_for_reader

_logger = get_logger(__name__)

REFLECTOR_QUERY_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
    llm_client.CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
]

_REFLECTOR_CACHE_BPS_DEFAULT = object()

K_SPARSE_THRESHOLD = 2  # planning §2; calibration-pending
MAX_QUESTIONS_PER_RUN = 4  # planning §5; calibration-pending
MAX_REFINED_QUERIES_PER_QUESTION = 3  # planning §4

_SEARCH_DEPTH: Literal["basic", "advanced"] = "advanced"
_MAX_RESULTS_PER_QUERY = 5
_TOP_RESULTS_PER_QUESTION = 10

# Model/provider defaults live in Settings (reflector_query_provider/reflector_query_model).
# Beta ships Haiku across all phases; override via env without code changes.
_REFINEMENT_MAX_TOKENS = 1024
_REFINEMENT_TEMPERATURE = 0.4


class _RefinedQueryListDraft(BaseModel):
    """LLM-facing output for query refinement; module-private."""

    model_config = ConfigDict(extra="forbid")
    queries: list[str] = Field(..., min_length=1, max_length=4)


def _extract_domain_from_url(url: str) -> str:
    """Extract registrable-looking host segment. urllib only; no SSRF (no fetch)."""
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return ""
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _evaluate_question_rules(reader_output: ReaderOutput) -> list[str]:
    """Return trigger signal labels for this question (OR-disjuncts, planning §2).

    Empty list means no triggers fire.

    Three disjuncts:
      - gap_note: evidence_gap_note is not None
      - sparse_atoms: len(extracted_evidence) <= K_SPARSE_THRESHOLD
      - mono_domain: len(extracted_evidence) >= 2 and unique_domains <= 1
    """
    triggers: list[str] = []

    if reader_output.evidence_gap_note is not None:
        triggers.append("gap_note")

    if len(reader_output.extracted_evidence) <= K_SPARSE_THRESHOLD:
        triggers.append("sparse_atoms")

    if len(reader_output.extracted_evidence) >= 2:
        domains = {
            _extract_domain_from_url(ev.source_url)
            for ev in reader_output.extracted_evidence
        }
        domains.discard("")
        if len(domains) <= 1:
            triggers.append("mono_domain")

    return triggers


def _evaluate_all_rules(
    reader_outputs: dict[str, ReaderOutput],
    research_plan: ResearchPlan,
) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """Rule pass in plan order; capped schedule + remainder skipped."""
    flagged_in_order: list[tuple[str, list[str]]] = []
    for question in research_plan.questions:
        qid = question.id
        ro = reader_outputs.get(qid)
        if ro is None:
            continue
        triggers = _evaluate_question_rules(ro)
        if triggers:
            flagged_in_order.append((qid, triggers))

    scheduled = flagged_in_order[:MAX_QUESTIONS_PER_RUN]
    skipped = [qid for qid, _ in flagged_in_order[MAX_QUESTIONS_PER_RUN:]]
    return scheduled, skipped


def _emit_calibration_signal_snapshot(
    *,
    question_id: str,
    ro: ReaderOutput,
    experiment_id: UUID,
) -> None:
    domains: set[str] = set()
    for ev in ro.extracted_evidence:
        d = _extract_domain_from_url(ev.source_url)
        if d:
            domains.add(d)

    high = sum(1 for ev in ro.extracted_evidence if ev.relevance == "high")
    med = sum(1 for ev in ro.extracted_evidence if ev.relevance == "medium")
    low = sum(1 for ev in ro.extracted_evidence if ev.relevance == "low")

    _logger.debug(
        "reflector signal snapshot",
        question_id=question_id,
        experiment_id=str(experiment_id),
        evidence_count=len(ro.extracted_evidence),
        relevance_high_count=high,
        relevance_medium_count=med,
        relevance_low_count=low,
        unique_domain_count=len(domains),
        domains=sorted(domains),
        has_gap_note=ro.evidence_gap_note is not None,
        trigger_gap_note=ro.evidence_gap_note is not None,
        trigger_sparse_atoms=len(ro.extracted_evidence) <= K_SPARSE_THRESHOLD,
        trigger_mono_domain=(
            len(ro.extracted_evidence) >= 2 and len(domains) <= 1
        ),
    )


async def _refine_queries_for_question(
    *,
    db: AsyncSession,
    experiment_id: UUID,
    question: ResearchQuestion,
    reader_output: ReaderOutput,
    triggers: list[str],
    refined_idea: RefinedIdea,
    research_plan: ResearchPlan,
    settings: Settings,
    cache_breakpoints: list[llm_client.CacheBreakpoint] | None | object = _REFLECTOR_CACHE_BPS_DEFAULT,
) -> tuple[list[str], Decimal]:
    """LLM call for one flagged question; ([], …) means skip that re-search."""

    high = sum(1 for ev in reader_output.extracted_evidence if ev.relevance == "high")
    med = sum(1 for ev in reader_output.extracted_evidence if ev.relevance == "medium")
    low = sum(1 for ev in reader_output.extracted_evidence if ev.relevance == "low")
    domains_set: set[str] = set()
    for ev in reader_output.extracted_evidence:
        d = _extract_domain_from_url(ev.source_url)
        if d:
            domains_set.add(d)

    if cache_breakpoints is _REFLECTOR_CACHE_BPS_DEFAULT:
        breakpoints: list[llm_client.CacheBreakpoint] | None = REFLECTOR_QUERY_CACHE_BREAKPOINTS
    else:
        breakpoints = cache_breakpoints  # type: ignore[assignment]
    use_cache = breakpoints is not None
    cache_breakpoints_used = len(breakpoints) if breakpoints else 0

    user_prompt = build_reflector_query_refinement_user_prompt(
        refined_idea=refined_idea,
        research_plan=research_plan,
        question_id=question.id,
        question_text=question.question,
        trigger_signals=triggers,
        evidence_count=len(reader_output.extracted_evidence),
        relevance_high_count=high,
        relevance_medium_count=med,
        relevance_low_count=low,
        unique_domain_count=len(domains_set),
        existing_domains=sorted(domains_set),
        original_search_queries=question.search_queries,
        evidence_gap_note=reader_output.evidence_gap_note,
        for_cache=use_cache,
    )

    try:
        draft, meta = await llm_client.complete_structured(
            db,
            provider=settings.reflector_query_provider,
            model=settings.reflector_query_model,
            prompt_name=REFINEMENT_PROMPT_NAME,
            system=REFLECTOR_QUERY_REFINEMENT_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=_RefinedQueryListDraft,
            max_tokens=_REFINEMENT_MAX_TOKENS,
            temperature=_REFINEMENT_TEMPERATURE,
            max_retries=2,
            experiment_id=experiment_id,
            phase="reflector",
            cache_breakpoints=breakpoints,
        )

        trimmed: list[str] = []
        for raw_q in draft.queries:
            if not raw_q or not isinstance(raw_q, str):
                continue
            piece = raw_q.strip()[:200]
            if piece:
                trimmed.append(piece)

        validated = trimmed[:MAX_REFINED_QUERIES_PER_QUESTION]
        if not validated:
            _logger.warning(
                "reflector query refinement returned empty list",
                question_id=question.id,
                experiment_id=str(experiment_id),
            )
            return [], Decimal("0")

        _logger.debug(
            "reflector query refinement cache breakpoints",
            question_id=question.id,
            experiment_id=str(experiment_id),
            cache_breakpoints_used=cache_breakpoints_used,
        )

        _logger.info(
            "reflector query refinement complete",
            question_id=question.id,
            experiment_id=str(experiment_id),
            refined_queries_count=len(validated),
            cost_usd=str(meta.cost_usd),
            prompt_tokens=meta.prompt_tokens,
            completion_tokens=meta.completion_tokens,
            latency_ms=meta.latency_ms,
        )
        return validated, meta.cost_usd
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "reflector query refinement failed",
            question_id=question.id,
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        return [], Decimal("0")


def _merge_search_results(
    existing: dict[str, list[TavilyResult]],
    new_results: dict[str, list[TavilyResult]],
) -> dict[str, list[TavilyResult]]:
    """Merge Tavily lists per question with URL-first-wins dedup."""
    merged: dict[str, list[TavilyResult]] = {k: list(v) for k, v in existing.items()}
    for qid, new_rows in new_results.items():
        existing_urls = {r.url for r in merged.get(qid, [])}
        for r in new_rows:
            if r.url not in existing_urls:
                merged.setdefault(qid, []).append(r)
                existing_urls.add(r.url)
    return merged


def _rank_and_cap_per_question(
    results: dict[str, list[TavilyResult]],
) -> dict[str, list[TavilyResult]]:
    """Sort by Tavily score desc and keep top N per question — Searcher-aligned."""
    out: dict[str, list[TavilyResult]] = {}
    for qid, rows in results.items():
        sorted_rows = sorted(
            rows,
            key=lambda r: r.score if r.score is not None else 0.0,
            reverse=True,
        )
        out[qid] = sorted_rows[:_TOP_RESULTS_PER_QUESTION]
    return out


async def _partial_re_search(
    *,
    decision: ReflectorDecision,
    experiment_id: UUID,
    db: AsyncSession,
) -> tuple[dict[str, list[TavilyResult]], int, int]:
    """Run Tavily for refined queries concurrently; return (rows, successes, failures)."""

    task_pairs: list[tuple[str, str]] = [
        (spec.question_id, q)
        for spec in decision.questions_to_re_search
        for q in spec.refined_queries
    ]
    if not task_pairs:
        return {}, 0, 0

    async def _run_single_search(
        question_id: str, query: str
    ) -> tuple[str, list[TavilyResult] | BaseException]:
        try:
            results = await tavily_client.search(
                db,
                query=query,
                experiment_id=experiment_id,
                max_results=_MAX_RESULTS_PER_QUERY,
                search_depth=_SEARCH_DEPTH,
            )
            return question_id, results
        except BaseException as exc:  # noqa: BLE001
            return question_id, exc

    raw_outcomes: list[tuple[str, list[TavilyResult] | BaseException]] = list(
        await asyncio.gather(
            *[_run_single_search(qid, qtxt) for qid, qtxt in task_pairs],
            return_exceptions=False,
        )
    )

    acc: dict[str, dict[str, TavilyResult]] = {}
    successes = 0
    failures = 0
    per_question_new_hits: dict[str, int] = {}

    for question_id, outcome in raw_outcomes:
        url_map = acc.setdefault(question_id, {})
        if isinstance(outcome, BaseException):
            failures += 1
            _logger.warning(
                "reflector partial tavily search failed",
                question_id=question_id,
                experiment_id=str(experiment_id),
                error_type=type(outcome).__name__,
            )
            continue
        successes += 1
        for result in outcome:
            if result.url not in url_map:
                url_map[result.url] = result

    new_by_question: dict[str, list[TavilyResult]] = {}
    for qid, url_map in acc.items():
        rows = sorted(
            url_map.values(),
            key=lambda r: r.score if r.score is not None else 0.0,
            reverse=True,
        )
        if rows:
            new_by_question[qid] = rows
            per_question_new_hits[qid] = len(rows)

    _logger.info(
        "reflector partial re-search aggregate",
        experiment_id=str(experiment_id),
        total_task_pairs=len(task_pairs),
        success_count=successes,
        failure_count=failures,
        questions_with_any_new_hit=len(new_by_question),
        per_question_new_tavily_hit_counts=per_question_new_hits,
    )
    return new_by_question, successes, failures


async def _partial_re_read(
    *,
    db: AsyncSession,
    experiment_id: UUID,
    questions_to_re_read: list[ResearchQuestion],
    search_results: dict[str, list[TavilyResult]],
    refined_idea: RefinedIdea,
    research_questions: list[ResearchQuestion],
    settings: Settings,
) -> dict[str, ReaderOutput]:
    """Re-run Reader extraction for a subset of questions after partial re-search."""
    from app.services.reader_service import _extract_for_question  # noqa: PLC0415

    tasks = [
        _extract_for_question(
            db=db,
            experiment_id=experiment_id,
            question=q,
            tavily_results=search_results.get(q.id, []),
            refined_idea=refined_idea,
            research_questions=research_questions,
            settings=settings,
        )
        for q in questions_to_re_read
    ]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    re_read_outputs: dict[str, ReaderOutput] = {}
    for q, outcome in zip(questions_to_re_read, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            _logger.warning(
                "reflector partial re-read raised",
                question_id=q.id,
                experiment_id=str(experiment_id),
                error_type=type(outcome).__name__,
            )
            continue
        reader_output, _stats = outcome
        re_read_outputs[q.id] = reader_output
    return re_read_outputs


def _merge_reader_outputs(
    existing: dict[str, ReaderOutput],
    re_read: dict[str, ReaderOutput],
) -> dict[str, ReaderOutput]:
    """Successful re-reads replace; skips leave prior atoms intact."""
    merged = dict(existing)
    for qid, new_ro in re_read.items():
        merged[qid] = new_ro
    return merged


def _zero_phase_summary() -> ReflectorPhaseSummary:
    return ReflectorPhaseSummary(
        loop_iteration=0,
        questions_flagged_count=0,
        questions_scheduled_count=0,
        decision_method="rule_v1",
        waves_used=0,
    )


def _finalize_reflector_summary(
    summary: ReflectorPhaseSummary,
    *,
    reader_outputs: dict[str, ReaderOutput],
    research_plan: ResearchPlan,
) -> ReflectorPhaseSummary:
    """Attach deterministic evidence analysis (expanded Reflector responsibility)."""
    from app.services.evidence_analysis_service import analyze_evidence
    from app.services.evidence_atoms import collect_evidence_atoms

    atoms = collect_evidence_atoms(reader_outputs, research_plan)
    analysis = analyze_evidence(
        atoms,
        reader_outputs=reader_outputs,
        research_plan=research_plan,
    )
    return summary.model_copy(update={"evidence_analysis": analysis})


async def execute_reflector(
    *,
    experiment_id: UUID,
    research_plan: ResearchPlan,
    reader_outputs: dict[str, ReaderOutput],
    search_results: dict[str, list[TavilyResult]],
    db: AsyncSession,
    settings: Settings,
) -> tuple[
    dict[str, ReaderOutput],
    dict[str, list[TavilyResult]],
    ReflectorPhaseSummary,
]:
    """Reflector entry point — §6 friendly: never raises; errors return inputs."""
    max_waves = settings.reflector_max_refinement_waves

    if max_waves <= 0:
        _logger.info(
            "reflector disabled (max_refinement_waves <= 0)",
            experiment_id=str(experiment_id),
        )
        try:
            summary = _finalize_reflector_summary(
                _zero_phase_summary(),
                reader_outputs=reader_outputs,
                research_plan=research_plan,
            )
        except Exception:
            _logger.exception("reflector.finalize_failed_disabled_path")
            summary = _zero_phase_summary()
        return reader_outputs, search_results, summary

    _t_phase0 = time.perf_counter()
    total_cost_delta = Decimal("0")
    total_tavily_tasks_succeeded = 0
    total_partial_re_read_successes = 0
    waves_used = 0
    last_loop_iteration = 0
    last_questions_flagged = 0
    last_questions_scheduled = 0

    try:
        current_reader_outputs = reader_outputs
        current_search_results = search_results

        refined_idea = await _load_refined_idea_for_reader(db, experiment_id)

        for wave in range(max_waves):
            flagged, skipped_due_to_budget = _evaluate_all_rules(
                current_reader_outputs, research_plan
            )

            for question in research_plan.questions:
                ro = current_reader_outputs.get(question.id)
                if ro is None:
                    continue
                _emit_calibration_signal_snapshot(
                    question_id=question.id,
                    ro=ro,
                    experiment_id=experiment_id,
                )

            questions_rule_flagged_before_cap = (
                len(flagged) + len(skipped_due_to_budget)
            )
            last_loop_iteration = wave
            last_questions_flagged = questions_rule_flagged_before_cap
            last_questions_scheduled = len(flagged)

            _logger.info(
                "reflector decision complete",
                experiment_id=str(experiment_id),
                questions_flagged_for_re_search=questions_rule_flagged_before_cap,
                questions_scheduled_for_re_search=len(flagged),
                re_search_triggered=len(flagged) > 0,
                loop_iteration=wave,
                decision_method="rule_v1",
                max_refinement_waves=max_waves,
                per_question_budget_exhausted_count=len(skipped_due_to_budget),
            )

            if not flagged:
                break

            q_by_id: dict[str, ResearchQuestion] = {
                q.id: q for q in research_plan.questions
            }
            refinement_tasks = []
            flagged_pairs: list[tuple[str, list[str]]] = []
            for qid, triggers in flagged:
                qobj = q_by_id.get(qid)
                if qobj is None or qid not in current_reader_outputs:
                    continue
                flagged_pairs.append((qid, triggers))
                refinement_tasks.append(
                    _refine_queries_for_question(
                        db=db,
                        experiment_id=experiment_id,
                        question=qobj,
                        reader_output=current_reader_outputs[qid],
                        triggers=triggers,
                        refined_idea=refined_idea,
                        research_plan=research_plan,
                        settings=settings,
                    )
                )
            refinement_batches = await asyncio.gather(*refinement_tasks)

            for _refined, ref_cost in refinement_batches:
                total_cost_delta += ref_cost

            scheduled_specs: list[QuestionReSearchSpec] = []
            for (qid, triggers), (refined, _ref_cost) in zip(
                flagged_pairs,
                refinement_batches,
                strict=True,
            ):
                if not refined:
                    continue
                try:
                    scheduled_specs.append(
                        QuestionReSearchSpec(
                            question_id=qid,
                            trigger_signals=triggers,
                            refined_queries=refined,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "reflector failed to build QuestionReSearchSpec",
                        question_id=qid,
                        experiment_id=str(experiment_id),
                        error_type=type(exc).__name__,
                    )

            decision = ReflectorDecision(
                questions_to_re_search=scheduled_specs,
                skipped_question_ids_due_to_budget=skipped_due_to_budget,
            )

            if not decision.questions_to_re_search:
                _logger.info(
                    "reflector wave fizzled",
                    experiment_id=str(experiment_id),
                    loop_iteration=wave,
                    questions_flagged_count=questions_rule_flagged_before_cap,
                    reason="no_executable_re_searches",
                )
                break

            new_search_results, tav_succ, _ = await _partial_re_search(
                decision=decision,
                experiment_id=experiment_id,
                db=db,
            )

            if not new_search_results:
                _logger.info(
                    "reflector wave fizzled",
                    experiment_id=str(experiment_id),
                    loop_iteration=wave,
                    questions_flagged_count=questions_rule_flagged_before_cap,
                    reason="re_search_failed_or_empty",
                )
                break

            waves_used += 1

            merged_search = _merge_search_results(
                current_search_results, new_search_results
            )
            current_search_results = _rank_and_cap_per_question(merged_search)

            qs_with_new_hits = {
                qid for qid, rows in new_search_results.items() if rows
            }
            scheduled_qids_with_spec = {
                spec.question_id for spec in decision.questions_to_re_search
            }
            questions_to_re_read = [
                q
                for q in research_plan.questions
                if q.id in qs_with_new_hits and q.id in scheduled_qids_with_spec
            ]

            re_read_outputs = await _partial_re_read(
                db=db,
                experiment_id=experiment_id,
                questions_to_re_read=questions_to_re_read,
                search_results=current_search_results,
                refined_idea=refined_idea,
                research_questions=research_plan.questions,
                settings=settings,
            )
            total_partial_re_read_successes += len(re_read_outputs)
            current_reader_outputs = _merge_reader_outputs(
                current_reader_outputs, re_read_outputs
            )
            total_tavily_tasks_succeeded += tav_succ

        summary = ReflectorPhaseSummary(
            loop_iteration=last_loop_iteration,
            questions_flagged_count=last_questions_flagged,
            questions_scheduled_count=last_questions_scheduled,
            decision_method="rule_v1",
            waves_used=waves_used,
        )

        _logger.info(
            "reflector phase complete",
            experiment_id=str(experiment_id),
            total_cost_delta_usd=str(total_cost_delta),
            total_partial_tavily_tasks_succeeded=total_tavily_tasks_succeeded,
            partial_re_read_success_question_count=total_partial_re_read_successes,
            waves_used=waves_used,
            total_phase_latency_ms=int(
                round((time.perf_counter() - _t_phase0) * 1000)
            ),
        )

        summary = _finalize_reflector_summary(
            summary,
            reader_outputs=current_reader_outputs,
            research_plan=research_plan,
        )

        return current_reader_outputs, current_search_results, summary

    except Exception as exc:  # noqa: BLE001
        _logger.error(
            (
                "reflector phase encountered unexpected error; degrading "
                "to pre-reflector outputs"
            ),
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        try:
            summary = _finalize_reflector_summary(
                _zero_phase_summary(),
                reader_outputs=reader_outputs,
                research_plan=research_plan,
            )
        except Exception:
            _logger.exception("reflector.finalize_failed_in_handler")
            summary = _zero_phase_summary()
        return reader_outputs, search_results, summary
