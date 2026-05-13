"""ValidationReport schema — the contract for the research engine output.

This schema is the data contract that founder-facing landing pages, insight
reports, and admin tools all consume. It is designed for the FINAL 5-phase
research engine shape (B3), not just the 3-phase B2 POC. The B2 synthesizer
fills it from raw Tavily results; B3's reader fills the same shape from
per-question extracted evidence. The schema itself does not change between
B2 and B3.

Two-tier design (added in B2.3-fix):
  Draft types (FindingDraft, CompetitorMentionDraft, QuestionFindingsDraft,
  ValidationReportDraft) are the LLM-facing shapes. The LLM emits URL strings
  for citations instead of full Citation objects. This cuts ~30% of output
  tokens by eliminating title/domain/timestamp re-emission.

  Final types (Finding, CompetitorMention, QuestionFindings, ValidationReport)
  are the persisted shapes with full Citation objects. The synthesizer service
  hydrates Draft → Final after parsing, by joining each URL back to its
  matching TavilyResultForPrompt in the SynthesizerInput. The frontend
  contract is unchanged — callers always receive final types.

Per AGENTS.md "Input and output handling":
- LLM-generated content rendered in the frontend must be treated as
  untrusted text. This schema is the boundary where we enforce that all
  LLM output is parsed and validated before reaching any consumer.

Per AGENTS.md "LLM and agent security":
- Every Finding requires citations (1-3). This is the structural anti-
  hallucination guardrail: if the synthesizer cannot back a claim with a
  citation from the provided search results, it cannot produce a Finding.

Per .cursorrules "Research Engine Quality":
- Citations are non-negotiable. Every claim has a source URL.
- Specificity over summary: Finding.claim and evidence_summary must be
  concrete enough to carry named entities, numbers, or direct quotes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Citation(BaseModel):
    """A single source cited by a Finding or CompetitorMention.

    url is validated to start with http:// or https:// — the synthesizer
    MUST NOT cite URLs that were not in the Tavily results, so the URL
    format guardrail is a secondary check; the primary guardrail is in
    the synthesizer prompt (cite only URLs appearing in <tavily_results>).
    """

    model_config = ConfigDict(extra="forbid")

    url: Annotated[
        str,
        Field(
            min_length=10,
            max_length=2000,
            description=(
                "The full URL of the cited source. Must start with http:// or https://. "
                "Must be a URL that appeared in the <tavily_results> provided to the "
                "synthesizer — the synthesizer MUST NOT fabricate URLs."
            ),
        ),
    ]

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description=(
                "The title of the cited source as returned by Tavily. Use the exact "
                "title from the search result where possible."
            ),
        ),
    ]

    source_domain: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description=(
                "The registered domain extracted from the URL for display and grouping "
                "(e.g. 'reddit.com', 'techcrunch.com', 'g2.com'). Used by the frontend "
                "to group citations by source and display source badges."
            ),
        ),
    ]

    accessed_at: Annotated[
        datetime,
        Field(
            description=(
                "ISO 8601 timestamp of when the Tavily search fetched this result. "
                "Set to the time the searcher phase ran, not the publication date."
            ),
        ),
    ]

    @field_validator("url")
    @classmethod
    def _url_must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(
                f"Citation URL must start with http:// or https://; got: {v!r}"
            )
        return v


class Finding(BaseModel):
    """A single piece of evidence answering a research question.

    One ResearchQuestion produces 2-5 Findings. Each Finding is a single
    substantive, evidence-backed claim with 1-3 supporting citations.

    The citations list constraint (min=1) is the structural anti-hallucination
    guardrail: every claim must cite at least one source from the Tavily results.
    A synthesizer that cannot back a claim cannot produce a Finding for it.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: Annotated[
        str,
        Field(
            pattern=r"^q[1-7]$",
            description=(
                "The id of the ResearchQuestion this Finding answers. Must match "
                "ResearchQuestion.id exactly (one of q1–q7). This is the cross-phase "
                "reference that links findings to questions in the planner output."
            ),
        ),
    ]

    claim: Annotated[
        str,
        Field(
            min_length=10,
            max_length=500,
            description=(
                "1-2 sentences stating the substantive, evidence-backed claim this "
                "Finding makes. Be concrete and specific — quote numbers, name companies, "
                "reference actual user complaints where the evidence allows. Do NOT write "
                "generic summaries like 'the market is large' or 'users want this'. "
                "Maximum 500 characters."
            ),
        ),
    ]

    evidence_summary: Annotated[
        str,
        Field(
            min_length=10,
            max_length=800,
            description=(
                "1-3 sentences describing what the cited sources actually say. Paraphrase "
                "the evidence rather than quoting verbatim unless a direct quote is "
                "especially significant. Name the specific source type when possible "
                "('a 2024 Gartner report', 'three r/operations posts', 'Guru's pricing page'). "
                "Maximum 800 characters."
            ),
        ),
    ]

    citations: Annotated[
        list[Citation],
        Field(
            min_length=1,
            max_length=3,
            description=(
                "1-3 Citations supporting this finding. NEVER zero — every claim requires "
                "at least one source URL from the provided <tavily_results>. Include 2-3 "
                "citations when multiple independent sources corroborate the claim. "
                "Do NOT include more than 3 — focus on the strongest sources."
            ),
        ),
    ]

    confidence: Literal["high", "medium", "low"]

    confidence_rationale: Annotated[
        str,
        Field(
            min_length=5,
            max_length=250,
            description=(
                "1 sentence explaining why this confidence level was assigned. "
                "Be specific: 'Backed by two Gartner reports and one r/operations thread' "
                "not 'multiple sources agree'. Default toward lower confidence — "
                "founders are best served by honest calibration. Maximum 250 characters."
            ),
        ),
    ]


class QuestionFindings(BaseModel):
    """All findings for one research question.

    One entry per ResearchQuestion in the ResearchPlan. question_id and
    question are restated here for ergonomic frontend rendering — consumers
    don't need to join against the planner output to display the report.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: Annotated[
        str,
        Field(
            pattern=r"^q[1-7]$",
            description=(
                "The ResearchQuestion.id this block answers. One of q1–q7. Must match "
                "a question id in the corresponding ResearchPlan."
            ),
        ),
    ]

    question: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description=(
                "Restatement of the ResearchQuestion.question text for ergonomic frontend "
                "rendering. The frontend can display the full report without loading the "
                "planner's ResearchPlan separately. Maximum 300 characters."
            ),
        ),
    ]

    findings: Annotated[
        list[Finding],
        Field(
            min_length=1,
            max_length=5,
            description=(
                "2-5 Findings that collectively answer this question. If only 1 Finding "
                "can be supported by evidence, use 1. Do not pad with speculative findings. "
                "Each Finding must have at least 1 citation. Maximum 5 findings per question."
            ),
        ),
    ]

    evidence_gap: Annotated[
        str | None,
        Field(
            default=None,
            max_length=400,
            description=(
                "If a meaningful sub-dimension of this question went unanswered by the "
                "available evidence, note it here in 1-2 sentences. Null if the question "
                "is sufficiently covered by the findings. This is the per-question honesty "
                "channel — use it rather than omitting the gap silently. Maximum 400 chars."
            ),
        ),
    ]


class CompetitorMention(BaseModel):
    """A named competitor or substitute surfaced by the research.

    Aggregated across all findings. Only include companies or products that
    actually appeared in the Tavily search results — the synthesizer MUST NOT
    invent competitor names that don't appear in the provided evidence.
    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=150,
            description=(
                "The precise name of the competitor, product, or service as it appears "
                "in the cited sources. Do not paraphrase or generalize — use the exact "
                "brand or product name (e.g. 'Guru', 'Beehiiv Boosts', not 'knowledge "
                "management tools')."
            ),
        ),
    ]

    description: Annotated[
        str,
        Field(
            min_length=5,
            max_length=300,
            description=(
                "1 sentence describing what this competitor does. Factual summary based "
                "on the cited sources, not invented description. Maximum 300 characters."
            ),
        ),
    ]

    positioning_vs_idea: Annotated[
        str,
        Field(
            min_length=5,
            max_length=400,
            description=(
                "1-2 sentences on how this competitor overlaps with or differs from the "
                "founder's refined idea. Anchor to the specific wedge or differentiator "
                "in the RefinedIdea — not a generic 'they compete in the same space' "
                "statement. Maximum 400 characters."
            ),
        ),
    ]

    citations: Annotated[
        list[Citation],
        Field(
            min_length=1,
            max_length=2,
            description=(
                "1-2 Citations confirming this competitor's existence and positioning. "
                "NEVER zero — every CompetitorMention requires at least one source URL "
                "from <tavily_results>. The synthesizer MUST NOT name companies that "
                "cannot be cited from the provided search results."
            ),
        ),
    ]


class ValidationReport(BaseModel):
    """The full research report for one founder idea.

    Schema-stable across B2 (3-phase Planner+Searcher+Synthesizer) and
    B3 (5-phase with Reader+Reflector added). The B2 synthesizer fills
    this schema directly from raw Tavily results. B3's reader fills the
    same schema from per-question extracted evidence. The schema does not
    change between phases — only the evidence quality improves.

    Per .cursorrules: "citations are non-negotiable — every claim has a
    source URL." The citation constraints on Finding (1-3 required) and
    CompetitorMention (1-2 required) are the structural enforcement of
    this rule.

    Per AGENTS.md "LLM and agent security": this output is LLM-generated
    text that has been parsed and validated. Downstream consumers MUST
    treat field values as untrusted text (use plain text rendering, NOT
    dangerouslySetInnerHTML) — the schema validation removes structural
    violations but cannot sanitize content.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: Annotated[
        str,
        Field(
            min_length=50,
            max_length=2000,
            description=(
                "3-5 sentences summarizing the key findings, competitive reality, and "
                "recommendation. Evidence-led — no fluff. Opens with the most important "
                "finding, not a restatement of the idea. Founders should be able to read "
                "this alone and know whether to proceed, iterate, pivot, or kill. "
                "Maximum 2000 characters."
            ),
        ),
    ]

    questions_and_findings: Annotated[
        list[QuestionFindings],
        Field(
            min_length=5,
            max_length=7,
            description=(
                "One QuestionFindings entry per ResearchQuestion in the plan. Must contain "
                "exactly the same number of entries as the planner produced questions "
                "(5-7). Each entry contains 1-5 Findings with citations."
            ),
        ),
    ]

    competitors: Annotated[
        list[CompetitorMention],
        Field(
            min_length=0,
            max_length=6,
            description=(
                "0-6 named competitors or substitutes surfaced across all findings. "
                "Aggregated from the findings — only include companies that appeared "
                "in the Tavily results with at least one citation. An empty list is "
                "valid and preferred over fabricating competitors."
            ),
        ),
    ]

    market_signals: Annotated[
        str,
        Field(
            min_length=10,
            max_length=1500,
            description=(
                "2-4 sentences on market size, growth rate, or demand signals from the "
                "research. Cite specific figures or sources when they exist in the findings. "
                "If no meaningful market-size evidence was found, say so explicitly: "
                "'The searches returned no reliable market-size data for this niche.' "
                "Do NOT fabricate TAM figures. Maximum 1500 characters."
            ),
        ),
    ]

    distribution_signals: Annotated[
        str | None,
        Field(
            default=None,
            max_length=1500,
            description=(
                "2-4 sentences on acquisition channels, growth mechanics, or distribution "
                "strategies evidenced in the findings. Null if the searches returned no "
                "meaningful distribution signal for this idea. Maximum 1500 characters."
            ),
        ),
    ]

    regulatory_signals: Annotated[
        str | None,
        Field(
            default=None,
            max_length=1000,
            description=(
                "2-4 sentences on legal, compliance, licensing, or regulatory constraints "
                "evidenced in the findings. Null if the idea has no apparent regulatory "
                "dimension (e.g. a plain productivity SaaS with no financial, health, or "
                "legal angle). Do not manufacture regulatory concerns. Maximum 1000 chars."
            ),
        ),
    ]

    risks_assessment: Annotated[
        str,
        Field(
            min_length=50,
            max_length=2500,
            description=(
                "3-5 sentences that explicitly address each of the 3-5 risks listed in "
                "the RefinedIdea — confirmed, refuted, or unaddressed by the findings. "
                "Reference the question_ids that investigated each risk. This is the "
                "direct answer to what the founder was most worried about. Maximum 2500 chars."
            ),
        ),
    ]

    overall_recommendation: Literal[
        "proceed", "iterate", "pivot", "kill", "too_vague_to_recommend"
    ]

    recommendation_rationale: Annotated[
        str,
        Field(
            min_length=50,
            max_length=2000,
            description=(
                "3-5 sentences explaining the recommendation, anchored to specific findings "
                "by question_id and evidence. Not 'the market looks good' but 'q4 findings "
                "cite NerdWallet's $X ARR alongside subscriber count data showing WTP in the "
                "personal finance newsletter category'. Maximum 2000 characters."
            ),
        ),
    ]

    research_limitations: Annotated[
        str,
        Field(
            min_length=10,
            max_length=800,
            description=(
                "1-3 sentences on what couldn't be answered and why. If certain dimensions "
                "were investigated but evidence was thin, say so. If certain dimensions "
                "weren't investigated at all, say so. This is the synthesizer's honesty "
                "channel. For too_vague_to_recommend reports, this field is the primary "
                "content — the whole report IS a limitations note. Maximum 800 characters."
            ),
        ),
    ]

    rubric_version_used: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description=(
                "The rubric version used for evaluation and grading. Passed through from "
                "the orchestrator to the synthesizer and stored in the report for audit "
                "trail — so graders know which rubric criteria apply to this report. "
                "Example: 'v1'. Maximum 50 characters."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _validate_question_ids_unique(self) -> "ValidationReport":
        """Reject a ValidationReport where two QuestionFindings share the same question_id."""
        ids = [qf.question_id for qf in self.questions_and_findings]
        if len(ids) != len(set(ids)):
            seen: set[str] = set()
            duplicates: list[str] = []
            for qid in ids:
                if qid in seen:
                    duplicates.append(qid)
                seen.add(qid)
            raise ValueError(
                f"Duplicate question_ids in questions_and_findings: {duplicates}"
            )
        return self


# ---------------------------------------------------------------------------
# Draft types — LLM-facing shapes with URL-string citations (B2.3-fix)
#
# The LLM emits citations as plain URL strings rather than full Citation
# objects. This eliminates ~30% of synthesizer output tokens (no re-emitting
# title/domain/timestamp). The synthesizer service hydrates Draft → Final by
# joining each URL back to the matching TavilyResultForPrompt in the input.
#
# All char-limit and count constraints are kept identical to the final types
# so schema enforcement applies equally to LLM output and persisted data.
# ---------------------------------------------------------------------------

# Reusable item type for URL strings inside Draft citation lists.
_DraftCitationUrl = Annotated[str, Field(min_length=10, max_length=2000)]


class FindingDraft(BaseModel):
    """LLM-facing shape for a Finding — citations are URL strings, not Citation objects.

    Mirrors Finding exactly except citations: list[str] (URL strings, 1-3 items).
    The synthesizer service hydrates these URLs to full Citation objects after
    parsing by joining against the SynthesizerInput search results.

    Char limits and count constraints are identical to Finding so the schema
    enforcement is equally strict on both the LLM output and the persisted form.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: Annotated[
        str,
        Field(
            pattern=r"^q[1-7]$",
            description="The id of the ResearchQuestion this Finding answers (q1–q7).",
        ),
    ]

    claim: Annotated[
        str,
        Field(
            min_length=10,
            max_length=500,
            description=(
                "1-2 sentences stating the substantive, evidence-backed claim. "
                "Be concrete — quote numbers, name companies, reference user complaints. "
                "Maximum 500 characters."
            ),
        ),
    ]

    evidence_summary: Annotated[
        str,
        Field(
            min_length=10,
            max_length=800,
            description=(
                "1-3 sentences on what the cited sources actually say. "
                "Name the specific source type when possible. Maximum 800 characters."
            ),
        ),
    ]

    citations: Annotated[
        list[_DraftCitationUrl],
        Field(
            min_length=1,
            max_length=3,
            description=(
                "1-3 URL strings from <tavily_results> supporting this finding. "
                "NEVER zero — every claim requires at least one source URL. "
                "Each URL must start with http:// or https://. "
                "Do NOT include more than 3 — focus on the strongest sources."
            ),
        ),
    ]

    confidence: Literal["high", "medium", "low"]

    confidence_rationale: Annotated[
        str,
        Field(
            min_length=5,
            max_length=250,
            description=(
                "1 sentence explaining the confidence level. Be specific. "
                "Maximum 250 characters."
            ),
        ),
    ]

    @field_validator("citations")
    @classmethod
    def _urls_must_be_http(cls, v: list[str]) -> list[str]:
        for url in v:
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(
                    f"Citation URL must start with http:// or https://; got: {url!r}"
                )
        return v


class CompetitorMentionDraft(BaseModel):
    """LLM-facing shape for a CompetitorMention — citations are URL strings.

    Mirrors CompetitorMention except citations: list[str] (URL strings, 1-2 items).
    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=150,
            description="Exact brand or product name as it appears in cited sources.",
        ),
    ]

    description: Annotated[
        str,
        Field(
            min_length=5,
            max_length=300,
            description="1 sentence describing what this competitor does. Maximum 300 characters.",
        ),
    ]

    positioning_vs_idea: Annotated[
        str,
        Field(
            min_length=5,
            max_length=400,
            description=(
                "1-2 sentences on how this competitor overlaps with or differs from "
                "the founder's idea. Maximum 400 characters."
            ),
        ),
    ]

    citations: Annotated[
        list[_DraftCitationUrl],
        Field(
            min_length=1,
            max_length=2,
            description=(
                "1-2 URL strings from <tavily_results> confirming this competitor. "
                "NEVER zero. Each URL must start with http:// or https://."
            ),
        ),
    ]

    @field_validator("citations")
    @classmethod
    def _urls_must_be_http(cls, v: list[str]) -> list[str]:
        for url in v:
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(
                    f"Citation URL must start with http:// or https://; got: {url!r}"
                )
        return v


class QuestionFindingsDraft(BaseModel):
    """LLM-facing shape for QuestionFindings — uses FindingDraft."""

    model_config = ConfigDict(extra="forbid")

    question_id: Annotated[
        str,
        Field(
            pattern=r"^q[1-7]$",
            description="The ResearchQuestion.id this block answers (q1–q7).",
        ),
    ]

    question: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description="Restatement of the question text for ergonomic frontend rendering.",
        ),
    ]

    findings: Annotated[
        list[FindingDraft],
        Field(
            min_length=1,
            max_length=5,
            description="2-5 FindingDraft items that collectively answer this question.",
        ),
    ]

    evidence_gap: Annotated[
        str | None,
        Field(
            default=None,
            max_length=400,
            description=(
                "1-2 sentences on an unanswered dimension. Null if covered. "
                "Maximum 400 characters."
            ),
        ),
    ]


class ValidationReportDraft(BaseModel):
    """LLM-facing shape for ValidationReport — citations are URL strings throughout.

    The synthesizer LLM parses its output into this model. The synthesizer
    service then hydrates it to a ValidationReport with full Citation objects
    by joining each URL back to the SynthesizerInput search results. Callers
    always receive the final ValidationReport; this type never leaves the
    synthesizer service.

    All field constraints (char limits, list lengths, literals) are identical
    to ValidationReport so the LLM is equally constrained in both forms.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: Annotated[
        str,
        Field(
            min_length=50,
            max_length=2000,
            description="3-5 sentences summarizing findings and recommendation. Maximum 2000 chars.",
        ),
    ]

    questions_and_findings: Annotated[
        list[QuestionFindingsDraft],
        Field(
            min_length=5,
            max_length=7,
            description="One QuestionFindingsDraft entry per ResearchQuestion (5-7 items).",
        ),
    ]

    competitors: Annotated[
        list[CompetitorMentionDraft],
        Field(
            min_length=0,
            max_length=6,
            description=(
                "0-6 named competitors from the Tavily results. "
                "An empty list is preferred over fabricated competitors."
            ),
        ),
    ]

    market_signals: Annotated[
        str,
        Field(
            min_length=10,
            max_length=1500,
            description="2-4 sentences on market size or demand signals. Maximum 1500 chars.",
        ),
    ]

    distribution_signals: Annotated[
        str | None,
        Field(default=None, max_length=1500),
    ]

    regulatory_signals: Annotated[
        str | None,
        Field(default=None, max_length=1000),
    ]

    risks_assessment: Annotated[
        str,
        Field(
            min_length=50,
            max_length=2500,
            description=(
                "3-5 sentences addressing each RefinedIdea risk. Maximum 2500 chars."
            ),
        ),
    ]

    overall_recommendation: Literal[
        "proceed", "iterate", "pivot", "kill", "too_vague_to_recommend"
    ]

    recommendation_rationale: Annotated[
        str,
        Field(
            min_length=50,
            max_length=2000,
            description="3-5 sentences anchored to specific question_ids. Maximum 2000 chars.",
        ),
    ]

    research_limitations: Annotated[
        str,
        Field(
            min_length=10,
            max_length=800,
            description="1-3 sentences on what couldn't be answered. Maximum 800 chars.",
        ),
    ]

    rubric_version_used: Annotated[
        str,
        Field(min_length=1, max_length=50),
    ]

    @model_validator(mode="after")
    def _validate_question_ids_unique(self) -> "ValidationReportDraft":
        """Reject a ValidationReportDraft where two QuestionFindingsDraft share question_id."""
        ids = [qf.question_id for qf in self.questions_and_findings]
        if len(ids) != len(set(ids)):
            seen: set[str] = set()
            duplicates: list[str] = []
            for qid in ids:
                if qid in seen:
                    duplicates.append(qid)
                seen.add(qid)
            raise ValueError(
                f"Duplicate question_ids in questions_and_findings: {duplicates}"
            )
        return self
