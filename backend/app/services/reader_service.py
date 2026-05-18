"""Reader service — per-question structured evidence extraction.

Runs one LLM call per research question, concurrently (bounded by
``Settings.reader_concurrency_limit``), between Searcher and Synthesizer.

Public entry point: ``execute_reader()``.

Per planning doc ``b3-reader-phase.md`` §5–§9, ADR 0010, ADR 0011.
Did not define ``ReaderHallucinatedCitation``; the URL guard is implemented as
drop+count with optional sentinel when the hallucination rate exceeds the
threshold — no per-item raise path (§8.4).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import Settings
from app.db.models.experiment import Experiment
from app.integrations.tavily import TavilyResult
from app.llm.prompts.reader import (
    PROMPT_NAME,
    READER_SYSTEM_PROMPT,
    build_reader_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.planner import ResearchQuestion
from app.schemas.refinement import RefinedIdea
from app.schemas.reader import (
    ExtractedEvidence,
    ExtractedEvidenceDraft,
    ReaderOutput,
    ReaderOutputDraft,
)

_logger = get_logger(__name__)

URL_HALLUCINATION_THRESHOLD = 0.20  # Per planning doc §8.4, calibration-pending
QUOTE_HALLUCINATION_THRESHOLD = 0.10  # Per planning doc §4.2, calibration-pending

SENTINEL_LLM_FAILURE_MESSAGE = (
    "Reader extraction failed for this question — Synthesizer will receive "
    "no pre-extracted evidence."
)
SENTINEL_URL_THRESHOLD_MESSAGE = (
    "Reader extraction for this question exceeded URL hallucination "
    "threshold — content discarded."
)

_READER_MODEL = "claude-sonnet-4-6"
_READER_PROVIDER = "anthropic"
_READER_MAX_TOKENS = 4096
_READER_TEMPERATURE = 0.3

READER_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
    llm_client.CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
]

# Sentinel: default ``_extract_for_question(..., cache_breakpoints=...)`` uses
# :data:`READER_CACHE_BREAKPOINTS`; pass ``None`` explicitly to disable caching.
_READER_CACHE_BPS_DEFAULT = object()


class ReaderTotalFailure(Exception):  # noqa: N818 — name fixed by planning doc §8.2
    """Raised when Reader produced no evidence for ANY question.

    The orchestrator catches this and transitions the experiment to
    RESEARCH_FAILED. Per planning doc §8.2.
    """


async def _load_refined_idea_for_reader(
    db: AsyncSession,
    experiment_id: UUID,
) -> RefinedIdea:
    """Load ``Experiment.refined_idea`` for Reader Zone B (per planning doc)."""
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None:
        raise ValueError(f"experiment not found: {experiment_id}")
    if experiment.refined_idea is None:
        raise ValueError(f"experiment {experiment_id} has no refined_idea — cannot run reader")
    return RefinedIdea.model_validate(experiment.refined_idea)


def _empty_llm_stats() -> dict[str, Any]:
    return {
        "hallucinated_url_count": 0,
        "quote_hallucination_count": 0,
        "hallucination_rate": 0.0,
        "quote_hallucination_rate": 0.0,
        "sentinel_reason": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cost_usd": Decimal("0"),
        "latency_ms": 0,
    }


def _stats_for_sentinel_llm_failure() -> dict[str, Any]:
    s = _empty_llm_stats()
    s["sentinel_reason"] = "llm_call_failed"
    return s


def _emit_reader_question_complete(
    *,
    question_id: str,
    experiment_id: UUID,
    tavily_result_count: int,
    reader_output: ReaderOutput,
    stats: dict[str, Any],
) -> None:
    """One structured INFO line per question (planning doc §9)."""
    _logger.info(
        "reader question complete",
        question_id=question_id,
        experiment_id=str(experiment_id),
        tavily_result_count=tavily_result_count,
        extracted_evidence_count=len(reader_output.extracted_evidence),
        hallucinated_url_count=stats["hallucinated_url_count"],
        quote_hallucination_count=stats["quote_hallucination_count"],
        hallucination_rate=stats["hallucination_rate"],
        quote_hallucination_rate=stats["quote_hallucination_rate"],
        sentinel_reason=stats["sentinel_reason"],
        has_evidence_gap=reader_output.evidence_gap_note is not None,
        prompt_tokens=stats["prompt_tokens"],
        completion_tokens=stats["completion_tokens"],
        cost_usd=str(stats["cost_usd"]),
        latency_ms=stats["latency_ms"],
    )


def _emit_calibration_field_lengths(
    *,
    question_id: str,
    experiment_id: UUID,
    reader_output: ReaderOutput,
    cache_breakpoints_used: int,
) -> None:
    """DEBUG calibration emit per docs/planning §13 and calibration procedure."""
    ev = reader_output.extracted_evidence
    _logger.debug(
        "reader field length distribution",
        question_id=question_id,
        experiment_id=str(experiment_id),
        cache_breakpoints_used=cache_breakpoints_used,
        source_url_lengths=[len(e.source_url) for e in ev],
        verbatim_quote_lengths=[
            len(e.verbatim_quote) if e.verbatim_quote else 0 for e in ev
        ],
        paraphrase_lengths=[len(e.paraphrase) for e in ev],
        named_entities_counts=[len(e.named_entities) for e in ev],
        named_entities_max_item_lengths=[
            max((len(s) for s in e.named_entities), default=0) for e in ev
        ],
        evidence_gap_note_length=(
            len(reader_output.evidence_gap_note)
            if reader_output.evidence_gap_note
            else 0
        ),
    )


def _validate_question_output(
    draft: ReaderOutputDraft,
    tavily_results: list[TavilyResult],
    question_id: str,
    experiment_id: UUID,
    *,
    llm_meta: llm_client.LLMResult | None = None,
) -> tuple[ReaderOutput, dict[str, Any]]:
    """URL + quote guards; returns final ReaderOutput and stats for logging.

    ``llm_meta`` is ``LLMResult`` when the draft came from a successful
    ``complete_structured`` call (token/cost/latency for §9). For sentinel
    paths derived without an LLM success, pass ``None`` and zeros are used.
    """
    stats: dict[str, Any] = {
        "hallucinated_url_count": 0,
        "quote_hallucination_count": 0,
        "hallucination_rate": 0.0,
        "quote_hallucination_rate": 0.0,
        "sentinel_reason": None,
        "prompt_tokens": getattr(llm_meta, "prompt_tokens", 0) if llm_meta else 0,
        "completion_tokens": getattr(llm_meta, "completion_tokens", 0)
        if llm_meta
        else 0,
        "cost_usd": getattr(llm_meta, "cost_usd", Decimal("0")) if llm_meta else Decimal("0"),
        "latency_ms": getattr(llm_meta, "latency_ms", 0) if llm_meta else 0,
    }

    provided_urls = {r.url for r in tavily_results}
    hallucinated_url_count = 0
    clean_evidence_drafts: list[ExtractedEvidenceDraft] = []

    for evidence_draft in draft.extracted_evidence:
        if evidence_draft.source_url not in provided_urls:
            hallucinated_url_count += 1
            _logger.warning(
                "reader hallucinated url",
                question_id=question_id,
                experiment_id=str(experiment_id),
                hallucinated_url_count=hallucinated_url_count,
                evidence_items_before_drop=len(draft.extracted_evidence),
            )
        else:
            clean_evidence_drafts.append(evidence_draft)

    total_after_url_guard = len(clean_evidence_drafts)
    denom_url = hallucinated_url_count + total_after_url_guard
    hallucination_rate = (
        (hallucinated_url_count / denom_url) if denom_url > 0 else 0.0
    )
    stats["hallucinated_url_count"] = hallucinated_url_count
    stats["hallucination_rate"] = hallucination_rate

    if hallucination_rate > URL_HALLUCINATION_THRESHOLD:
        stats["sentinel_reason"] = "hallucination_threshold_exceeded"
        stats["quote_hallucination_count"] = 0
        stats["quote_hallucination_rate"] = 0.0
        out = ReaderOutput(
            question_id=question_id,
            extracted_evidence=[],
            evidence_gap_note=SENTINEL_URL_THRESHOLD_MESSAGE,
        )
        return out, stats

    content_by_url = {r.url: r.content for r in tavily_results}

    quote_hallucination_count = 0
    total_extractions_with_quote = sum(
        1 for ev in clean_evidence_drafts if ev.verbatim_quote is not None
    )

    final_evidence: list[ExtractedEvidence] = []
    for evidence_draft in clean_evidence_drafts:
        quote = evidence_draft.verbatim_quote
        if quote is not None:
            source_content = content_by_url.get(evidence_draft.source_url, "")
            if quote not in source_content:
                quote_hallucination_count += 1
                _logger.warning(
                    "reader hallucinated quote",
                    question_id=question_id,
                    experiment_id=str(experiment_id),
                    quote_hallucination_count=quote_hallucination_count,
                )
                quote = None

        final_evidence.append(
            ExtractedEvidence(
                source_url=evidence_draft.source_url,
                relevance=evidence_draft.relevance,
                verbatim_quote=quote,
                paraphrase=evidence_draft.paraphrase,
                named_entities=evidence_draft.named_entities,
            )
        )

    quote_rate = (
        (quote_hallucination_count / total_extractions_with_quote)
        if total_extractions_with_quote > 0
        else 0.0
    )
    stats["quote_hallucination_count"] = quote_hallucination_count
    stats["quote_hallucination_rate"] = quote_rate

    if quote_rate > QUOTE_HALLUCINATION_THRESHOLD:
        _logger.error(
            "reader quote hallucination rate exceeded threshold",
            question_id=question_id,
            experiment_id=str(experiment_id),
            quote_hallucination_rate=quote_rate,
            quote_hallucination_count=quote_hallucination_count,
            total_extractions_with_quote=total_extractions_with_quote,
        )

    gap = draft.evidence_gap_note
    out = ReaderOutput(
        question_id=question_id,
        extracted_evidence=final_evidence,
        evidence_gap_note=gap,
    )
    return out, stats


async def _extract_for_question(
    *,
    db: AsyncSession,
    experiment_id: UUID,
    question: ResearchQuestion,
    tavily_results: list[TavilyResult],
    refined_idea: RefinedIdea,
    research_questions: list[ResearchQuestion],
    cache_breakpoints: list[llm_client.CacheBreakpoint] | None | object = _READER_CACHE_BPS_DEFAULT,
) -> tuple[ReaderOutput, dict[str, Any]]:
    if cache_breakpoints is _READER_CACHE_BPS_DEFAULT:
        breakpoints: list[llm_client.CacheBreakpoint] | None = READER_CACHE_BREAKPOINTS
    else:
        breakpoints = cache_breakpoints  # type: ignore[assignment]
    question_id = question.id
    tavily_result_count = len(tavily_results)
    result_dicts = [r.model_dump() for r in tavily_results]
    use_cache = breakpoints is not None
    user_prompt = build_reader_user_prompt(
        refined_idea=refined_idea,
        research_questions=research_questions,
        question_id=question_id,
        question_text=question.question,
        tavily_results=result_dicts,
        for_cache=use_cache,
    )
    cache_breakpoints_used = len(breakpoints) if breakpoints else 0

    try:
        draft, meta = await llm_client.complete_structured(
            db,
            provider=_READER_PROVIDER,
            model=_READER_MODEL,
            prompt_name=PROMPT_NAME,
            system=READER_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=ReaderOutputDraft,
            max_tokens=_READER_MAX_TOKENS,
            temperature=_READER_TEMPERATURE,
            max_retries=3,
            experiment_id=experiment_id,
            phase="reader",
            cache_breakpoints=breakpoints,
        )
        reader_output, stats = _validate_question_output(
            draft,
            tavily_results,
            question_id,
            experiment_id,
            llm_meta=meta,
        )

        _emit_reader_question_complete(
            question_id=question_id,
            experiment_id=experiment_id,
            tavily_result_count=tavily_result_count,
            reader_output=reader_output,
            stats=stats,
        )

        if stats["sentinel_reason"] is None:
            _emit_calibration_field_lengths(
                question_id=question_id,
                experiment_id=experiment_id,
                reader_output=reader_output,
                cache_breakpoints_used=cache_breakpoints_used,
            )

        return reader_output, stats

    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "reader question extraction failed",
            question_id=question_id,
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        stats = _stats_for_sentinel_llm_failure()
        stats["prompt_tokens"] = 0
        stats["completion_tokens"] = 0
        stats["cost_usd"] = Decimal("0")
        stats["latency_ms"] = 0

        reader_output = ReaderOutput(
            question_id=question_id,
            extracted_evidence=[],
            evidence_gap_note=SENTINEL_LLM_FAILURE_MESSAGE,
        )
        _emit_reader_question_complete(
            question_id=question_id,
            experiment_id=experiment_id,
            tavily_result_count=tavily_result_count,
            reader_output=reader_output,
            stats=stats,
        )
        return reader_output, stats


async def execute_reader(
    *,
    experiment_id: UUID,
    research_questions: list[ResearchQuestion],
    search_results_by_question: dict[str, list[TavilyResult]],
    db: AsyncSession,
    settings: Settings,
) -> dict[str, ReaderOutput]:
    """Run Reader for each research question; return outputs keyed by question id.

    Raises:
        ReaderTotalFailure: if every question ends with zero extracted evidence
        (planning doc §8.2).
    """
    refined_idea = await _load_refined_idea_for_reader(db, experiment_id)

    semaphore = asyncio.Semaphore(settings.reader_concurrency_limit)

    async def _bounded(
        question: ResearchQuestion,
    ) -> tuple[ReaderOutput, dict[str, Any]]:
        async with semaphore:
            results = search_results_by_question.get(question.id, [])
            return await _extract_for_question(
                db=db,
                experiment_id=experiment_id,
                question=question,
                tavily_results=results,
                refined_idea=refined_idea,
                research_questions=research_questions,
            )

    task_outcomes: list[
        tuple[ReaderOutput, dict[str, Any]] | Exception
    ] = await asyncio.gather(
        *[_bounded(q) for q in research_questions],
        return_exceptions=True,
    )

    reader_outputs: dict[str, ReaderOutput] = {}
    all_stats: list[dict[str, Any]] = []
    stats_by_question: dict[str, dict[str, Any]] = {}

    for question, outcome in zip(research_questions, task_outcomes, strict=True):
        qid = question.id
        if isinstance(outcome, Exception):
            _logger.warning(
                "reader question task raised",
                question_id=qid,
                experiment_id=str(experiment_id),
                error_type=type(outcome).__name__,
            )
            stats = _stats_for_sentinel_llm_failure()
            reader_output = ReaderOutput(
                question_id=qid,
                extracted_evidence=[],
                evidence_gap_note=SENTINEL_LLM_FAILURE_MESSAGE,
            )
            _emit_reader_question_complete(
                question_id=qid,
                experiment_id=experiment_id,
                tavily_result_count=len(
                    search_results_by_question.get(qid, [])
                ),
                reader_output=reader_output,
                stats=stats,
            )
            reader_outputs[qid] = reader_output
            all_stats.append(stats)
            stats_by_question[qid] = stats
            continue

        reader_output, stats = outcome
        reader_outputs[qid] = reader_output
        all_stats.append(stats)
        stats_by_question[qid] = stats

    total_hallucinated_urls = sum(s["hallucinated_url_count"] for s in all_stats)
    affected_url_questions = [
        qid
        for qid, stats in stats_by_question.items()
        if stats["hallucinated_url_count"] > 0
    ]
    if total_hallucinated_urls > 0:
        _logger.error(
            "reader url hallucination detected",
            experiment_id=str(experiment_id),
            total_hallucinated_urls=total_hallucinated_urls,
            affected_question_ids=affected_url_questions,
        )

    total_quote_hallucinations = sum(
        s["quote_hallucination_count"] for s in all_stats
    )
    affected_quote_questions = [
        qid
        for qid, stats in stats_by_question.items()
        if stats["quote_hallucination_rate"] > QUOTE_HALLUCINATION_THRESHOLD
    ]
    if affected_quote_questions:
        _logger.error(
            "reader quote hallucination rate exceeded",
            experiment_id=str(experiment_id),
            total_quote_hallucinations=total_quote_hallucinations,
            affected_question_ids=affected_quote_questions,
        )

    total_extractions = sum(len(r.extracted_evidence) for r in reader_outputs.values())
    if total_extractions == 0:
        raise ReaderTotalFailure(
            f"Reader produced no evidence for any question "
            f"(experiment_id={experiment_id})"
        )

    return reader_outputs
