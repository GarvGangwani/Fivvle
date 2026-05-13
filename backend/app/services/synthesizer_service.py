"""Synthesizer service — wraps the LLM report-synthesis call.

Single public function: synthesize_report().

Called by the research engine orchestrator after the searcher phase has
returned Tavily results. Takes a SynthesizerInput (already packaged by
build_synthesizer_input()) and returns a fully validated ValidationReport.

Two-step process (B2.3-fix):
  1. Call Claude with response_model=ValidationReportDraft — the LLM emits
     citations as URL strings only (not full Citation objects), cutting ~30%
     of output tokens.
  2. Hydrate the draft to a ValidationReport by joining each URL back to the
     matching TavilyResultForPrompt in the SynthesizerInput. If the LLM
     emits a URL that was NOT in the input results, raise
     SynthesizerHallucinatedCitation — that is a hard quality failure.

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
- Log only safe metadata: counts, flags, recommendation enum value, cost.

NOTE on max_tokens:
  Raised from 8192 to 16384 in B2.3-fix. The synthesizer produces the largest
  structured output in the system — a full ValidationReport with 5-7
  QuestionFindings, each with 1-5 Findings, each with 1-3 URL strings, plus
  competitors, signals, and narrative fields. 16384 provides a safety margin
  even with the URL-only citation optimization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.llm.prompts.synthesizer import (
    PROMPT_NAME,
    SYNTHESIZER_SYSTEM_PROMPT,
    build_synthesizer_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.validation_report import (
    Citation,
    CompetitorMention,
    Finding,
    QuestionFindings,
    ValidationReport,
    ValidationReportDraft,
)
from app.services.synthesizer_input import SynthesizerInput, TavilyResultForPrompt

_logger = get_logger(__name__)

# Claude Sonnet 4.6 — per .cursorrules: "Do not downgrade models to save pennies.
# Use Claude for all research phases." The synthesizer is the highest-stakes call
# in the pipeline — quality is the priority.
_SYNTHESIZER_MODEL = "claude-sonnet-4-6"
_SYNTHESIZER_PROVIDER = "anthropic"

# 16384 tokens for the synthesizer — safety margin after the URL-only citation
# optimization. Even with the ~30% output-token reduction from Draft citations,
# this headroom ensures a full 7-question report never truncates.
_SYNTHESIZER_MAX_TOKENS = 16384

# temperature=0.3 — this is evidence-led synthesis, not creative writing.
# Low temperature reduces hallucination drift while leaving enough for
# natural language variation in the narrative fields.
_SYNTHESIZER_TEMPERATURE = 0.3


class SynthesizerHallucinatedCitation(Exception):
    """Raised when the synthesizer LLM emits a URL not present in the input results.

    This is a hard quality failure. The synthesizer must only cite URLs that
    appeared in the provided <tavily_results> sections. Any URL not found in
    the SynthesizerInput results is a hallucination — the LLM fabricated a
    source it was not given.

    The research engine orchestrator wraps this in ResearchEngineFailure
    with phase="synthesizer".
    """

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(
            f"Synthesizer emitted a citation URL not found in input results: {url!r}. "
            f"This is a hallucination failure — the LLM cited a source it was not given."
        )


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


def _build_url_index(
    synth_input: SynthesizerInput,
) -> dict[str, TavilyResultForPrompt]:
    """Build a flat URL → TavilyResultForPrompt lookup from all question results.

    Used by _hydrate_draft to match each LLM-emitted URL back to its source
    metadata. All questions are merged into one flat dict because the LLM
    may cite a result from any question's search, and we only need the URL
    match for hydration (not the originating question).
    """
    index: dict[str, TavilyResultForPrompt] = {}
    for results in synth_input.search_results_by_question.values():
        for r in results:
            index[r.url] = r
    return index


def _hydrate_draft(
    draft: ValidationReportDraft,
    synth_input: SynthesizerInput,
) -> ValidationReport:
    """Hydrate URL-string citations in a ValidationReportDraft to full Citation objects.

    Walks every FindingDraft.citations and CompetitorMentionDraft.citations list,
    looks each URL up in the SynthesizerInput search results, and builds a full
    Citation (url, title, source_domain, accessed_at=now).

    Raises:
        SynthesizerHallucinatedCitation: if any URL emitted by the LLM does
            not appear in the SynthesizerInput results. This means the LLM
            fabricated a URL that was not provided to it — a hard failure.
    """
    url_index = _build_url_index(synth_input)
    accessed_at = datetime.now(tz=timezone.utc)

    def _resolve_url(url: str) -> Citation:
        if url not in url_index:
            raise SynthesizerHallucinatedCitation(url=url)
        r = url_index[url]
        return Citation(
            url=url,
            title=r.title,
            source_domain=_extract_domain(url),
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
        rubric_version_used=draft.rubric_version_used,
    )


async def synthesize_report(
    db: AsyncSession,
    synth_input: SynthesizerInput,
    experiment_id: UUID | None = None,
) -> ValidationReport:
    """Call Claude to synthesize a ValidationReport from Tavily evidence.

    Builds the synthesizer user prompt from the SynthesizerInput, calls
    Claude via the structured LLM client (response_model=ValidationReportDraft),
    and hydrates the draft to a ValidationReport with full Citation objects.

    Args:
        db: AsyncSession from the caller's context. The LLM client wrapper
            writes a LLMCall row inside this session for cost tracking.
        synth_input: Packaged inputs from build_synthesizer_input() — includes
            the RefinedIdea, ResearchPlan, trimmed Tavily results, and rubric version.
        experiment_id: FK for LLMCall cost rollup. Pass the Experiment.id if
            available; None is valid for script-level calls.

    Returns:
        Parsed and validated ValidationReport with full Citation objects.

    Raises:
        SynthesizerHallucinatedCitation: LLM emitted a URL not in input results.
        anthropic.APIError: provider-side failure (network, rate limit, etc.).
        instructor.exceptions.InstructorRetryException: Instructor failed to parse
            a valid ValidationReportDraft after its retry budget.
        pydantic.ValidationError: Schema constraint violation in the parsed output.

    All exceptions propagate to the caller. The orchestrator (research_engine.py)
    wraps them in ResearchEngineFailure with phase="synthesizer" context.
    """
    question_count = len(synth_input.research_plan.questions)
    total_search_results = sum(
        len(results)
        for results in synth_input.search_results_by_question.values()
    )
    has_synthesizer_notes = synth_input.research_plan.notes_for_synthesizer is not None

    _logger.info(
        "synthesizer started",
        question_count=question_count,
        total_search_results_count=total_search_results,
        has_synthesizer_notes_from_planner=has_synthesizer_notes,
        rubric_version=synth_input.rubric_version,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    user_prompt = build_synthesizer_user_prompt(synth_input)

    draft, meta = await llm_client.complete_structured(
        db,
        provider=_SYNTHESIZER_PROVIDER,
        model=_SYNTHESIZER_MODEL,
        prompt_name=PROMPT_NAME,
        system=SYNTHESIZER_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=ValidationReportDraft,
        max_tokens=_SYNTHESIZER_MAX_TOKENS,
        temperature=_SYNTHESIZER_TEMPERATURE,
        max_retries=2,
        experiment_id=experiment_id,
        phase="synthesizer",
    )

    # Hydrate URL-string citations to full Citation objects.
    # Raises SynthesizerHallucinatedCitation if any URL is not in the input.
    parsed = _hydrate_draft(draft, synth_input)

    # Aggregate citation count across all findings for logging.
    total_finding_count = sum(
        len(qf.findings) for qf in parsed.questions_and_findings
    )
    total_citation_count = sum(
        len(f.citations)
        for qf in parsed.questions_and_findings
        for f in qf.findings
    )

    # Log aggregates only — NEVER log report content, field text, or idea content.
    _logger.info(
        "synthesizer completed",
        recommendation=parsed.overall_recommendation,
        finding_count=total_finding_count,
        competitor_count=len(parsed.competitors),
        total_citation_count=total_citation_count,
        question_count=len(parsed.questions_and_findings),
        cost_usd=str(meta.cost_usd),
        prompt_tokens=meta.prompt_tokens,
        completion_tokens=meta.completion_tokens,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    return parsed
