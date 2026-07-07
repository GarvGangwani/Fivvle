"""Synthesizer service — wraps the LLM report-synthesis call.

Single public function: synthesize_report().

Called by the research engine orchestrator after Reader has produced structured
evidence per question. Takes SynthesizerInput (four-field contract per ADR 0012)
and a citation_hydration_index for server-side URL → title/domain joining.

Two-step process (B2.3-fix + B3 Reader hand-off):
  1. Call Claude with response_model=ValidationReportDraft — the LLM emits
     citations as URL strings only (not full Citation objects), cutting ~30%
     of output tokens.
  2. Validate every draft URL is in the Reader evidence allow-list; then
     hydrate to a ValidationReport using citation_hydration_index. If the LLM
     emits a URL not in allowed_urls, raise SynthesizerHallucinatedCitation.

Per .cursorrules:
- This module imports complete_structured from app.llm.client. It does NOT
  import anthropic directly — that would violate AGENTS.md "LLM and agent security".
- LLMCall logging is handled by the client wrapper; this service does not write
  to LLMCall itself.
- Exceptions from complete_structured() propagate to the caller.

Per AGENTS.md "Logging hygiene":
- NEVER log ValidationReport content (it contains LLM-generated text derived
  from scraped web content and founder-submitted data).
- NEVER log SynthesizerInput content.
- Log only safe metadata: counts, flags, recommendation enum value, cost,
  field lengths (calibration), never verbatim field values.

NOTE on max_tokens:
  Raised from 8192 to 16384 in B2.3-fix. The synthesizer produces the largest
  structured output in the system — a full ValidationReport with 5-7
  QuestionFindings, each with 1-5 Findings, each with 1-3 URL strings, plus
  competitors, signals, and narrative fields. 16384 provides a safety margin
  even with the URL-only citation optimization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from urllib.parse import urlparse
from uuid import UUID

from instructor.core.exceptions import InstructorRetryException
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.llm.prompts.synthesizer import (
    PROMPT_NAME_V8_CACHED,
    SYNTHESIZER_SYSTEM_PROMPT,
    build_synthesizer_v8_user_prompt,
)

PROMPT_NAME = PROMPT_NAME_V8_CACHED
from app.logging_config import get_logger
from app.schemas.validation_report import (
    Citation,
    CompetitorMention,
    Finding,
    QuestionFindings,
    ValidationReport,
    ValidationReportDraft,
)
from app.schemas.business_construction import BusinessConstructionArtifact
from app.services.synthesizer_input import CitationHydrationEntry, SynthesizerInput

_logger = get_logger(__name__)

SYNTHESIZER_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="user_zone_a_end", ttl="1h"),
    llm_client.CacheBreakpoint(position="user_zone_b_end", ttl="5m"),
]

_SYNTH_CACHE_BPS_DEFAULT = object()

# Model/provider defaults live in Settings (synthesizer_provider/synthesizer_model).
# Beta ships Haiku across all phases; override via env without code changes.

# 16384 tokens for the synthesizer — safety margin after the URL-only citation
# optimization. Even with the ~30% output-token reduction from Draft citations,
# this headroom ensures a full 7-question report never truncates.
_SYNTHESIZER_MAX_TOKENS = 16384

# temperature=0.3 — this is evidence-led synthesis, not creative writing.
# Low temperature reduces hallucination drift while leaving enough for
# natural language variation in the narrative fields.
_SYNTHESIZER_TEMPERATURE = 0.3

# 3 total attempts — Kimi K2.6 tool-mode JSON can produce malformed output
# on large payloads (>25K chars). One extra retry over the default gives
# the model another shot before invoking the Anthropic fallback (Fix 3).
_SYNTHESIZER_MAX_RETRIES = 3


def _is_json_shape_error(exc: InstructorRetryException) -> bool:
    """True if the retry exception was caused by malformed JSON output."""
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "json_invalid",
            "invalid json",
            "jsondecodeerror",
            "key must be a string",
            "expecting value",
            "expecting property name",
        )
    )


def _kimi_attempt_prompt_tokens(exc: InstructorRetryException) -> int | None:
    usage = exc.total_usage
    if usage is None:
        return None
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    if isinstance(prompt_tokens, int):
        return prompt_tokens
    input_tokens = getattr(usage, "input_tokens", None)
    if isinstance(input_tokens, int):
        return input_tokens
    return None


class SynthesizerHallucinatedCitation(Exception):  # noqa: N818
    """Raised when the synthesizer emits a citation URL not in Reader evidence,

    or when hydration cannot resolve a URL that passed the allow-list guard.
    Hard quality / implementation failure — the orchestrator maps this to
    RESEARCH_FAILED (phase synthesizer).
    """

    def __init__(
        self,
        url: str,
        *,
        experiment_id: UUID | None = None,
        detail: str | None = None,
    ) -> None:
        self.url = url
        self.experiment_id = experiment_id
        if detail is not None:
            message = detail
        else:
            message = (
                f"Synthesizer emitted a citation URL not present in Reader "
                f"validated evidence URLs: {url!r}. This is a hallucination failure "
                f"— the LLM cited a source URL not drawn from extracted evidence."
            )
        super().__init__(message)


def _extract_domain(url: str) -> str:
    """Extract the bare domain from a URL, stripping scheme and www. prefix.

    Uses stdlib urllib.parse — no new dependencies.

    Examples:
        "https://www.reddit.com/r/sysadmin/..." → "reddit.com"
        "https://techcrunch.com/2024/..."       → "techcrunch.com"
        "http://www.g2.com/products/..."        → "g2.com"

    Returns at most 100 chars to satisfy Citation.source_domain constraint.
    """
    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc[:100]


def _assert_draft_citations_allowlisted(
    draft: ValidationReportDraft,
    allowed_urls: set[str],
    experiment_id: UUID | None,
) -> None:
    """Hard-fail if any draft citation URL is not from Reader extracted evidence."""
    for qi, qf_draft in enumerate(draft.questions_and_findings):
        for fi, f_draft in enumerate(qf_draft.findings):
            for url in f_draft.citations:
                if url not in allowed_urls:
                    raise SynthesizerHallucinatedCitation(
                        url,
                        experiment_id=experiment_id,
                        detail=(
                            f"Hallucinated citation URL {url!r} in "
                            f"questions_and_findings[{qi}].findings[{fi}].citations"
                        ),
                    )

    for ci, c_draft in enumerate(draft.competitors):
        for url in c_draft.citations:
            if url not in allowed_urls:
                raise SynthesizerHallucinatedCitation(
                    url,
                    experiment_id=experiment_id,
                    detail=(
                        f"Hallucinated citation URL {url!r} in "
                        f"competitors[{ci}].citations"
                    ),
                )


def _hydrate_draft(
    draft: ValidationReportDraft,
    citation_hydration_index: dict[str, CitationHydrationEntry],
) -> ValidationReport:
    """Hydrate URL-string citations using the orchestrator-built index.

    Raises:
        SynthesizerHallucinatedCitation: if a URL is missing from the index
            after passing the allow-list guard (implementation bug).
    """
    accessed_at = datetime.now(UTC)

    def _resolve_url(url: str) -> Citation:
        if url not in citation_hydration_index:
            raise SynthesizerHallucinatedCitation(
                url,
                experiment_id=None,
                detail=(
                    "hydration index missing URL that passed URL guard; "
                    "orchestrator/Searcher bug"
                ),
            )
        entry = citation_hydration_index[url]
        return Citation(
            url=url,
            title=entry.title[:300],
            source_domain=entry.source_domain[:100],
            accessed_at=accessed_at,
        )

    hydrated_qfs: list[QuestionFindings] = []
    for qf_draft in draft.questions_and_findings:
        hydrated_findings: list[Finding] = []
        for f_draft in qf_draft.findings:
            hydrated_findings.append(
                Finding(
                    question_id=f_draft.question_id,
                    claim=f_draft.claim,
                    evidence_summary=f_draft.evidence_summary,
                    citations=[_resolve_url(url) for url in f_draft.citations],
                    confidence=f_draft.confidence,
                    confidence_rationale=f_draft.confidence_rationale,
                )
            )
        hydrated_qfs.append(
            QuestionFindings(
                question_id=qf_draft.question_id,
                question=qf_draft.question,
                findings=hydrated_findings,
                evidence_gap=qf_draft.evidence_gap,
                score=qf_draft.score,
            )
        )

    hydrated_competitors: list[CompetitorMention] = []
    for c_draft in draft.competitors:
        hydrated_competitors.append(
            CompetitorMention(
                name=c_draft.name,
                description=c_draft.description,
                positioning_vs_idea=c_draft.positioning_vs_idea,
                citations=[_resolve_url(url) for url in c_draft.citations],
            )
        )

    return ValidationReport(
        executive_summary=draft.executive_summary,
        questions_and_findings=hydrated_qfs,
        competitors=hydrated_competitors,
        market_signals=draft.market_signals,
        distribution_signals=draft.distribution_signals,
        regulatory_signals=draft.regulatory_signals,
        risks_assessment=draft.risks_assessment,
        overall_recommendation=draft.overall_recommendation,
        recommendation_rationale=draft.recommendation_rationale,
        research_limitations=draft.research_limitations,
        voices=draft.voices,
        rubric_version_used=draft.rubric_version_used,
        section_scores=draft.section_scores,
        overall_score=draft.overall_score,
    )


async def synthesize_report(
    db: AsyncSession,
    synth_input: SynthesizerInput,
    citation_hydration_index: dict[str, CitationHydrationEntry],
    experiment_id: UUID | None = None,
    cache_breakpoints: list[llm_client.CacheBreakpoint] | None | object = _SYNTH_CACHE_BPS_DEFAULT,
) -> ValidationReport:
    """Call Claude to synthesize a ValidationReport from Reader evidence.

    Builds the synthesizer user prompt from SynthesizerInput, calls Claude via
    the structured LLM client (response_model=ValidationReportDraft), validates
    citation URLs against Reader evidence, and hydrates the draft using
    citation_hydration_index.

    Args:
        db: AsyncSession from the caller's context. The LLM client wrapper
            writes a LLMCall row inside this session for cost tracking.
        synth_input: Four-field input from build_synthesizer_input().
        citation_hydration_index: URL → metadata from Searcher results; not
            sent to the LLM. Used only in _hydrate_draft().
        experiment_id: FK for LLMCall cost rollup. Pass the Experiment.id if
            available; None is valid for script-level calls.
        cache_breakpoints: Anthropic user-zone cache breakpoints; defaults to
            :data:`SYNTHESIZER_CACHE_BREAKPOINTS`. Pass ``None`` to disable caching.

    Returns:
        Parsed and validated ValidationReport with full Citation objects.

    Raises:
        SynthesizerHallucinatedCitation: LLM emitted a URL not in Reader evidence,
            or hydration index inconsistent with allow-list.
        anthropic.APIError: provider-side failure (network, rate limit, etc.).
        instructor.exceptions.InstructorRetryException: Instructor failed to parse
            a valid ValidationReportDraft after its retry budget.
        pydantic.ValidationError: Schema constraint violation in the parsed output.

    All exceptions propagate to the caller. The orchestrator wraps them in
    ResearchEngineFailure with phase="synthesizer" context.
    """
    question_count = len(synth_input.research_plan.questions)
    total_extracted_evidence_in_input = sum(
        len(ro.extracted_evidence) for ro in synth_input.reader_outputs.values()
    )
    questions_with_gap_note = sum(
        1 for ro in synth_input.reader_outputs.values() if ro.evidence_gap_note is not None
    )
    sentinel_question_count = sum(
        1
        for ro in synth_input.reader_outputs.values()
        if len(ro.extracted_evidence) == 0 and ro.evidence_gap_note is not None
    )

    allowed_urls: set[str] = {
        ev.source_url
        for ro in synth_input.reader_outputs.values()
        for ev in ro.extracted_evidence
    }

    has_synthesizer_notes = synth_input.research_plan.notes_for_synthesizer is not None

    _logger.info(
        "synthesizer started",
        question_count=question_count,
        total_extracted_evidence_in_input=total_extracted_evidence_in_input,
        questions_with_gap_note=questions_with_gap_note,
        sentinel_question_count=sentinel_question_count,
        has_synthesizer_notes_from_planner=has_synthesizer_notes,
        rubric_version=synth_input.rubric_version,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    if cache_breakpoints is _SYNTH_CACHE_BPS_DEFAULT:
        breakpoints: list[llm_client.CacheBreakpoint] | None = SYNTHESIZER_CACHE_BREAKPOINTS
    else:
        breakpoints = cache_breakpoints  # type: ignore[assignment]
    use_cache = breakpoints is not None
    user_prompt = build_synthesizer_v8_user_prompt(synth_input, for_cache=use_cache)
    cache_breakpoints_used = len(breakpoints) if breakpoints else 0

    settings = get_settings()

    async def _complete_draft(
        provider: llm_client.ProviderName,
        model: str,
    ) -> tuple[ValidationReportDraft, llm_client.LLMResult]:
        return await llm_client.complete_structured(
            db,
            provider=provider,
            model=model,
            prompt_name=PROMPT_NAME,
            system=SYNTHESIZER_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=ValidationReportDraft,
            max_tokens=_SYNTHESIZER_MAX_TOKENS,
            temperature=_SYNTHESIZER_TEMPERATURE,
            max_retries=_SYNTHESIZER_MAX_RETRIES,
            experiment_id=experiment_id,
            phase="synthesizer",
            cache_breakpoints=breakpoints,
        )

    kimi_exc: InstructorRetryException | None = None
    draft: ValidationReportDraft
    meta: llm_client.LLMResult
    try:
        draft, meta = await _complete_draft(
            cast(llm_client.ProviderName, settings.synthesizer_provider),
            settings.synthesizer_model,
        )
    except InstructorRetryException as exc:
        kimi_exc = exc
        should_fallback = (
            settings.synthesizer_provider == "kimi"
            and settings.synthesizer_fallback_enabled
            and _is_json_shape_error(exc)
        )
        if not should_fallback:
            raise

        _logger.warning(
            "synthesizer kimi failed with JSON error, falling back to Anthropic",
            experiment_id=str(experiment_id) if experiment_id else None,
            error_type=type(exc).__name__,
            kimi_prompt_tokens_attempted=_kimi_attempt_prompt_tokens(exc),
        )

        try:
            draft, meta = await _complete_draft(
                cast(llm_client.ProviderName, settings.synthesizer_fallback_provider),
                settings.synthesizer_fallback_model,
            )
        except Exception:
            raise kimi_exc from None

        _logger.info(
            "synthesizer anthropic fallback succeeded",
            experiment_id=str(experiment_id) if experiment_id else None,
            provider=settings.synthesizer_fallback_provider,
            completion_tokens=meta.completion_tokens,
        )

    _assert_draft_citations_allowlisted(draft, allowed_urls, experiment_id)

    report = _hydrate_draft(draft, citation_hydration_index)

    if (
        synth_input.reasoning_output is not None
        and synth_input.evidence_analysis is not None
    ):
        report = report.model_copy(
            update={
                "business_construction": BusinessConstructionArtifact(
                    reasoning=synth_input.reasoning_output,
                    evidence_analysis=synth_input.evidence_analysis,
                )
            }
        )

    _logger.debug(
        "synthesizer field length distribution",
        experiment_id=str(experiment_id) if experiment_id else None,
        cache_breakpoints_used=cache_breakpoints_used,
        executive_summary_length=len(report.executive_summary),
        market_signals_length=len(report.market_signals),
        distribution_signals_length=(
            len(report.distribution_signals) if report.distribution_signals else 0
        ),
        regulatory_signals_length=(
            len(report.regulatory_signals) if report.regulatory_signals else 0
        ),
        risks_assessment_length=len(report.risks_assessment),
        recommendation_rationale_length=len(report.recommendation_rationale),
        research_limitations_length=len(report.research_limitations),
        questions_and_findings_count=len(report.questions_and_findings),
        competitors_count=len(report.competitors),
        finding_count_total=sum(
            len(qf.findings) for qf in report.questions_and_findings
        ),
        finding_claim_lengths=[
            len(f.claim)
            for qf in report.questions_and_findings
            for f in qf.findings
        ],
        finding_evidence_summary_lengths=[
            len(f.evidence_summary)
            for qf in report.questions_and_findings
            for f in qf.findings
        ],
        finding_confidence_rationale_lengths=[
            len(f.confidence_rationale)
            for qf in report.questions_and_findings
            for f in qf.findings
        ],
        evidence_gap_lengths=[
            len(qf.evidence_gap) if qf.evidence_gap else 0
            for qf in report.questions_and_findings
        ],
        citation_count_total=sum(
            len(f.citations)
            for qf in report.questions_and_findings
            for f in qf.findings
        )
        + sum(len(c.citations) for c in report.competitors),
    )

    _logger.info(
        "synthesizer complete",
        experiment_id=str(experiment_id) if experiment_id else None,
        phase="synthesizer",
        prompt_name=PROMPT_NAME,
        total_extracted_evidence_in_input=total_extracted_evidence_in_input,
        questions_with_gap_note=questions_with_gap_note,
        sentinel_question_count=sentinel_question_count,
        finding_count=sum(len(qf.findings) for qf in report.questions_and_findings),
        competitor_count=len(report.competitors),
        total_citation_count=sum(
            len(f.citations)
            for qf in report.questions_and_findings
            for f in qf.findings
        )
        + sum(len(c.citations) for c in report.competitors),
        cost_usd=str(meta.cost_usd),
        prompt_tokens=meta.prompt_tokens,
        completion_tokens=meta.completion_tokens,
        latency_ms=meta.latency_ms,
        recommendation=report.overall_recommendation,
    )

    return report
