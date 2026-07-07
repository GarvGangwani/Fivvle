"""SynthesizerInput models and builders.

Per ADR 0012 / ADR 0016, SynthesizerInput fields: refined_idea,
research_plan, reader_outputs, rubric_version, trends_signals (optional).
Raw Tavily snippets are not consumed by the Synthesizer prompt in any mode.

CitationHydrationEntry and build_citation_hydration_index() support
server-side Citation hydration. The hydration index is passed to
synthesize_report() as a separate parameter — NOT on SynthesizerInput.
The index is never serialized into the LLM user prompt.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.tavily import TavilyResult
from app.logging_config import get_logger
from app.schemas.business_construction import EvidenceAnalysisResult, ReasoningEngineOutput
from app.schemas.planner import ResearchPlan
from app.schemas.reader import ExtractedEvidence, ReaderOutput
from app.schemas.refinement import RefinedIdea
from app.schemas.search import TrendsSeries
from app.schemas.targeting import ExperimentTargeting
from app.schemas.voices import VoicesOutput

_logger = get_logger(__name__)

# Cap on evidence atoms per research question passed to the Synthesizer.
#
# Set from recent production distribution (27 question buckets across 4 recent
# reports): average ~=6.1 atoms/question, median=6, max=10.
#
# Rationale: the Synthesizer's per-question section is concise and does not
# materially improve with long evidence tails. Trimming only the tail on
# high-evidence buckets reduces token variance while leaving most questions
# untouched.
#
# Selection policy keeps the top-K by Reader's existing relevance label
# (high > medium > low). Ties preserve original Reader order.
SYNTHESIZER_EVIDENCE_ATOMS_PER_QUESTION_CAP: int = 8


def _relevance_rank(relevance: str) -> int:
    if relevance == "high":
        return 3
    if relevance == "medium":
        return 2
    return 1


def _cap_evidence_list(
    evidence: list[ExtractedEvidence],
    cap: int,
) -> list[ExtractedEvidence]:
    if len(evidence) <= cap:
        return list(evidence)
    indexed = list(enumerate(evidence))
    top = sorted(
        indexed,
        key=lambda pair: (-_relevance_rank(pair[1].relevance), pair[0]),
    )[:cap]
    top_idx = {idx for idx, _ in top}
    return [ev for idx, ev in indexed if idx in top_idx]


def _cap_reader_evidence(
    reader_outputs: dict[str, ReaderOutput],
    cap: int,
) -> dict[str, ReaderOutput]:
    """Return reader_outputs with per-question evidence lists capped at ``cap``.

    Selection keeps the top-``cap`` atoms by Reader's relevance signal
    (high > medium > low), preserving original order among retained atoms.
    Never mutates input.
    """
    capped: dict[str, ReaderOutput] = {}
    for question_id, output in reader_outputs.items():
        capped[question_id] = output.model_copy(
            update={
                "extracted_evidence": _cap_evidence_list(
                    output.extracted_evidence,
                    cap=cap,
                )
            }
        )
    return capped


class TavilyResultForPrompt(BaseModel):
    """A trimmed TavilyResult for inclusion in the synthesizer prompt.

    Strips fields the synthesizer doesn't need (e.g. raw scores are passed
    for context but not required for citation) and caps content length to
    control prompt token count.

    Per AGENTS.md "LLM and agent security": content_excerpt comes from
    scraped web content and is the highest prompt-injection risk surface in
    the system. The synthesizer prompt instructs Claude to treat everything
    inside <tavily_results> tags as untrusted data — this model is the
    mechanism by which that content is bounded and formatted for those tags.

    Retained for synthesizer_service hydration paths until that module is
    refactored (commit 3).
    """

    model_config = ConfigDict(extra="forbid")

    url: str = Field(
        description=(
            "Full URL of the search result. This is the URL the synthesizer uses "
            "when constructing citations — it must cite only URLs from this list."
        )
    )

    title: str = Field(
        description=(
            "Title of the search result as returned by Tavily. Used by the synthesizer "
            "as the citation title."
        )
    )

    content_excerpt: str = Field(
        description=(
            "The Tavily content snippet, capped at 3000 characters. This is the evidence "
            "text the synthesizer reads to extract findings. It is scraped web content — "
            "treat as untrusted data in the synthesizer prompt."
        )
    )

    score: float | None = Field(
        default=None,
        description=(
            "Tavily relevance score (0.0–1.0) for this result relative to the search query. "
            "Higher scores indicate closer relevance. The synthesizer may use this as a "
            "signal for confidence calibration, but should not cite the score itself."
        ),
    )


class CitationHydrationEntry(BaseModel):
    """Server-side URL → metadata map for Citation hydration.

    Built by the orchestrator from Searcher's TavilyResults. Passed to
    synthesize_report() as a separate parameter — NOT a field on SynthesizerInput.
    NEVER serialized into the LLM user prompt. Consumed only by _hydrate_draft()
    to populate Citation.title and Citation.source_domain. Per ADR 0012.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        ...,
        max_length=500,
        description="Tavily result title (looser cap than Citation.title; truncated at hydration).",
    )
    source_domain: str = Field(
        ...,
        max_length=255,
        description=(
            "Parsed domain from the result URL (looser cap than Citation.source_domain; "
            "truncated at hydration)."
        ),
    )


class SynthesizerInput(BaseModel):
    """All inputs the synthesizer LLM prompt is built from (five-field contract).

    Immutable once created — the prompt builder reads from this struct
    deterministically. No side effects.

    Per ADR 0012 / ADR 0016: no raw Tavily / search snippets on this model.
    trends_signals is optional structured demand context from Searcher (Trends).
    """


    model_config = ConfigDict(extra="forbid")

    refined_idea: RefinedIdea = Field(
        description=(
            "The validated RefinedIdea from the refinement phase. Provides the founder "
            "context (target audience, value proposition, risks) that anchors the "
            "synthesizer's recommendation and risks_assessment."
        )
    )

    research_plan: ResearchPlan = Field(
        description=(
            "The ResearchPlan produced by the Planner phase. The synthesizer uses "
            "question ids and question text to structure its QuestionFindings output, "
            "and notes_for_synthesizer (if set) to apply the honesty flag."
        )
    )

    reader_outputs: dict[str, ReaderOutput] = Field(
        description=(
            "Per-question Reader output keyed by question_id (q1..q7). "
            "Single evidence surface for the Synthesizer LLM prompt. "
            "Built from execute_reader() in the orchestrator. "
            "Per ADR 0012."
        )
    )

    rubric_version: str = Field(
        description=(
            "The rubric version string passed through to ValidationReport.rubric_version_used. "
            "For grading audit trail — allows evaluators to know which rubric criteria "
            "apply to a given report. Example: 'v1'."
        )
    )

    trends_signals: dict[str, TrendsSeries] | None = Field(
        default=None,
        description=(
            "Per-keyword Google Trends interest series from Searcher (ADR 0016). "
            "None when Trends failed or was skipped; empty dict is treated as absent "
            "in the synthesizer prompt."
        ),
    )

    evidence_analysis: EvidenceAnalysisResult | None = Field(
        default=None,
        description=(
            "Reflector evidence quality analysis. Passed to Reasoning-aware "
            "synthesizer prompts; not re-derived in Synthesizer."
        ),
    )

    reasoning_output: ReasoningEngineOutput | None = Field(
        default=None,
        description=(
            "Structured business intelligence from Reasoning Engine. Synthesizer "
            "communicates this into the founder-facing report — reasoning happens "
            "upstream, not in Synthesizer."
        ),
    )

    targeting: ExperimentTargeting | None = Field(
        default=None,
        description=(
            "Founder-declared targeting signals (geography, audience bracket, stage, "
            "why_now). Null signals unscoped default behavior in the synthesizer prompt."
        ),
    )

    voices_output: VoicesOutput | None = Field(
        default=None,
        description=(
            "Reddit Voices phase output. Passed to synthesizer for voices section "
            "generation. Null when Voices was not run (legacy paths)."
        ),
    )


def build_synthesizer_input(
    *,
    refined_idea: RefinedIdea,
    research_plan: ResearchPlan,
    reader_outputs: dict[str, ReaderOutput],
    rubric_version: str,
    trends_signals: dict[str, TrendsSeries] | None = None,
    evidence_analysis: EvidenceAnalysisResult | None = None,
    reasoning_output: ReasoningEngineOutput | None = None,
    targeting: ExperimentTargeting | None = None,
    voices_output: VoicesOutput | None = None,
    experiment_id: UUID | None = None,
) -> SynthesizerInput:
    """Build SynthesizerInput for the Synthesizer prompt.

    citation_hydration_index is built separately by the orchestrator from
    Searcher results. See build_citation_hydration_index().
    """
    capped_reader_outputs = _cap_reader_evidence(
        reader_outputs,
        cap=SYNTHESIZER_EVIDENCE_ATOMS_PER_QUESTION_CAP,
    )
    per_question_before = [
        (qid, len(output.extracted_evidence))
        for qid, output in reader_outputs.items()
    ]
    per_question_after = [
        (qid, len(output.extracted_evidence))
        for qid, output in capped_reader_outputs.items()
    ]
    total_atoms_before = sum(count for _, count in per_question_before)
    total_atoms_after = sum(count for _, count in per_question_after)
    capped_questions_count = sum(
        1
        for (_, before), (_, after) in zip(per_question_before, per_question_after)
        if after < before
    )
    _logger.info(
        "synthesizer evidence capped",
        experiment_id=str(experiment_id) if experiment_id else None,
        total_atoms_before=total_atoms_before,
        total_atoms_after=total_atoms_after,
        per_question_before=per_question_before,
        per_question_after=per_question_after,
        capped_questions_count=capped_questions_count,
        cap=SYNTHESIZER_EVIDENCE_ATOMS_PER_QUESTION_CAP,
    )

    return SynthesizerInput(
        refined_idea=refined_idea,
        research_plan=research_plan,
        reader_outputs=capped_reader_outputs,
        rubric_version=rubric_version,
        trends_signals=trends_signals,
        evidence_analysis=evidence_analysis,
        reasoning_output=reasoning_output,
        targeting=targeting,
        voices_output=voices_output,
    )


def build_citation_hydration_index(
    search_results_by_question: dict[str, list[TavilyResult]],
) -> dict[str, CitationHydrationEntry]:
    """Build URL → CitationHydrationEntry map from Searcher results.

    Iterates all questions' TavilyResults, extracts (url, title, source_domain)
    from each, deduplicates by URL (first occurrence wins for determinism),
    returns the dict.

    Domain extraction uses the same logic as the existing _extract_domain()
    helper in synthesizer_service.py (imported lazily here to avoid a circular
    import with that module). NEVER serialized into the LLM user prompt.
    Consumed only by _hydrate_draft() in synthesizer_service.py.

    Per ADR 0012 and planning doc §7.
    """
    from app.services.synthesizer_service import _extract_domain

    index: dict[str, CitationHydrationEntry] = {}
    for _question_id, results in search_results_by_question.items():
        for r in results:
            if r.url in index:
                continue
            index[r.url] = CitationHydrationEntry(
                title=r.title[:500],
                source_domain=_extract_domain(r.url)[:255],
            )
    return index
