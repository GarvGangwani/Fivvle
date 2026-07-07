"""Reader schema — per-question evidence extraction output contract.

The Reader phase sits between the Searcher and Reasoning Engine. Given raw
Tavily results for one research question, the Reader LLM extracts structured
evidence atoms (ExtractedEvidence) that downstream analysis and reasoning
consume. Reader owns evidence only — no recommendations or summaries.

Evidence atoms are normalized to :class:`~app.schemas.business_construction.EvidenceAtom`
via :func:`~app.services.evidence_atoms.collect_evidence_atoms` before Reflector
analysis and Reasoning Engine stages.

Two-tier design (mirrors the Draft-vs-Final pattern in validation_report.py,
per planning doc §4.5 and ADR 0010):

  Draft types (ExtractedEvidenceDraft, ReaderOutputDraft) are the LLM-facing
  shapes. The LLM emits source_url as a plain string. No cross-reference
  checks occur here — Pydantic validates format only.

  Final types (ExtractedEvidence, ReaderOutput) are the post-validation shapes
  produced by the reader service after two post-parse checks:
    1. URL hallucination guard: source_url must appear in the provided Tavily
       result URLs (planning doc §8.4).
    2. Quote substring guard: verbatim_quote, if non-null, must be an exact
       substring of the corresponding TavilyResult.content (planning doc §4.2).
  If the quote substring check fails, the service nulls verbatim_quote and
  increments quote_hallucination_count rather than dropping the evidence item.
  If the URL check fails, the evidence item is dropped entirely.
  The field shapes of Draft and Final are identical; the distinction is
  semantic (not-yet-validated vs validated).

All char-limit caps are first-pass estimates per docs/llm-schema-calibration.md
and MUST be re-calibrated to observed-max + 10–15% after the first 20 real
Reader runs per docs/calibration/procedure.md. Do not treat them as final.

Per AGENTS.md "LLM and agent security":
  - LLM outputs MUST be parsed via Pydantic before any downstream use.
  - NEVER pass Reader output as code, shell commands, or SQL.

Per AGENTS.md "Logging hygiene":
  - NEVER log verbatim_quote, paraphrase, or source content.
  - Log only aggregate metadata: question_id, result counts, error types.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedEvidenceDraft(BaseModel):
    """LLM-facing shape for one evidence atom extracted from a Tavily result.

    One ExtractedEvidenceDraft per Tavily result that contains useful
    information for the research question. Results with no relevant content
    produce no entry — the LLM skips them.

    source_url is validated to start with http:// or https:// (format check
    only). The reader service performs the post-parse URL cross-reference
    check (source_url must appear in the provided Tavily result URLs) after
    parsing, per planning doc §8.4 and ADR 0010.
    """

    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(
        ...,
        max_length=2000,
        description=(
            "The exact URL of the Tavily result this evidence comes from. "
            "MUST be a URL that appeared in the <tavily_results> provided — "
            "do NOT fabricate URLs or cite sources not in the provided results. "
            "Must start with http:// or https://. Maximum 2000 characters."
        ),
    )

    relevance: Literal["high", "medium", "low"] = Field(
        ...,
        description=(
            "How directly relevant this source is to the research question. "
            "Use 'high' when the source directly addresses the question with "
            "concrete data, named entities, or specific claims. Use 'medium' "
            "when the source is related but only partially answers the question. "
            "Use 'low' when the source is only tangentially relevant but still "
            "worth extracting. Do not produce an evidence item for results with "
            "no relevant content — skip those results entirely."
        ),
    )

    verbatim_quote: str | None = Field(
        None,
        max_length=600,
        description=(
            "An exact verbatim substring copied from the source's content. "
            "ONLY set this field if you can copy the exact phrase character-for-"
            "character from the provided content. Do NOT paraphrase and label it "
            "a quote — that is a hallucination. If no quotable phrase exists, "
            "leave this null. When set, this must be an exact match to text in "
            "the source content (the system verifies this). Maximum 600 characters."
        ),
    )

    paraphrase: str = Field(
        ...,
        max_length=600,
        description=(
            "1–3 sentences summarising what this specific source says about the "
            "research question. Be concrete: name numbers, company names, "
            "subreddits, year of data. Do NOT write generic summaries. "
            "Example of good paraphrase: 'Guru's G2 page (as of 2024) shows 847 "
            "reviews averaging 4.5 stars — the most-reviewed knowledge-management "
            "tool in the Slack integration category.' "
            "Example of bad paraphrase: 'The market is large and growing.' "
            "Maximum 600 characters."
        ),
    )

    named_entities: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Specific named entities found in this source that are relevant to the "
            "research question: company names, product names, dollar figures, "
            "percentages, subreddit names, regulatory body names, named studies. "
            "Do NOT include generic terms like 'a company' or 'the platform'. "
            "Each item must be a specific, named entity. Maximum 10 items, each "
            "maximum 100 characters."
        ),
    )

    @field_validator("source_url")
    @classmethod
    def _source_url_must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(
                f"source_url must start with http:// or https://; got: {v!r}"
            )
        return v

    @field_validator("named_entities")
    @classmethod
    def _named_entities_item_length(cls, v: list[str]) -> list[str]:
        for item in v:
            if len(item) > 100:
                raise ValueError(
                    f"each named_entity item must be at most 100 characters; "
                    f"got item of length {len(item)}: {item[:40]!r}..."
                )
        return v


class ExtractedEvidence(BaseModel):
    """Post-validation shape for one evidence atom.

    Produced by the reader service from ExtractedEvidenceDraft after:
      1. URL cross-reference check: source_url confirmed to exist in the
         provided Tavily result URLs (planning doc §8.4).
      2. Quote substring check: verbatim_quote, if non-null, confirmed as
         an exact substring of the corresponding TavilyResult.content
         (planning doc §4.2). On failure, verbatim_quote is nulled and
         quote_hallucination_count is incremented; the evidence item is kept.

    Field shapes are identical to ExtractedEvidenceDraft. The distinction
    is semantic: ExtractedEvidence is a validated, trusted evidence atom.
    This type is what the Synthesizer ingests.
    """

    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(
        ...,
        max_length=2000,
        description=(
            "The exact URL of the Tavily result this evidence comes from. "
            "Validated by the reader service against the provided Tavily results. "
            "Must start with http:// or https://. Maximum 2000 characters."
        ),
    )

    relevance: Literal["high", "medium", "low"] = Field(
        ...,
        description=(
            "How directly relevant this source is to the research question. "
            "'high' = directly addresses the question with concrete data. "
            "'medium' = related but only partially answers. "
            "'low' = tangentially relevant but still extractable signal."
        ),
    )

    verbatim_quote: str | None = Field(
        None,
        max_length=600,
        description=(
            "An exact verbatim substring from the source's content, confirmed "
            "by the reader service as an exact substring match. Null if no "
            "quotable phrase existed or if the quote failed substring validation "
            "(in which case verbatim_quote was nulled by the service and "
            "quote_hallucination_count was incremented). Maximum 600 characters."
        ),
    )

    paraphrase: str = Field(
        ...,
        max_length=600,
        description=(
            "1–3 sentences summarising what this source says about the research "
            "question. Concrete, named-entity-rich. Maximum 600 characters."
        ),
    )

    named_entities: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Specific named entities from this source relevant to the question: "
            "company names, products, figures, subreddits, regulatory bodies. "
            "Maximum 10 items, each maximum 100 characters."
        ),
    )

    @field_validator("source_url")
    @classmethod
    def _source_url_must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(
                f"source_url must start with http:// or https://; got: {v!r}"
            )
        return v

    @field_validator("named_entities")
    @classmethod
    def _named_entities_item_length(cls, v: list[str]) -> list[str]:
        for item in v:
            if len(item) > 100:
                raise ValueError(
                    f"each named_entity item must be at most 100 characters; "
                    f"got item of length {len(item)}: {item[:40]!r}..."
                )
        return v


class ReaderOutputDraft(BaseModel):
    """LLM-facing shape for per-question Reader output.

    The LLM emits one ReaderOutputDraft per research question via a
    per-question LLM call (per ADR 0011). The reader service performs
    post-parse URL validation and quote-substring validation on each
    ReaderOutputDraft before producing a ReaderOutput.

    extracted_evidence is capped at 10 items because Tavily returns at
    most 10 results per query by default (planning doc §4.3). If the LLM
    skips all results (no relevant content), extracted_evidence is empty
    and evidence_gap_note describes what was missing.

    All caps are first-pass estimates; re-calibrate after 20 real runs
    per docs/llm-schema-calibration.md and docs/calibration/procedure.md.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(
        ...,
        description=(
            "The id of the research question this output covers. One of q1–q7 "
            "as assigned by the Planner phase. Copy this exactly from the "
            "<research_question> tag in the user prompt — do not invent or "
            "modify it."
        ),
    )

    extracted_evidence: list[ExtractedEvidenceDraft] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "0–10 ExtractedEvidence items, one per Tavily result that contains "
            "useful information for this research question. Skip results with no "
            "relevant content — do not produce an item for them. If NO results "
            "contain useful content, produce an empty list here and describe the "
            "gap in evidence_gap_note. Maximum 10 items (Tavily returns at most "
            "10 results per query)."
        ),
    )

    evidence_gap_note: str | None = Field(
        None,
        max_length=400,
        description=(
            "1–2 sentences describing what this question could NOT find evidence "
            "for, and why. Set this when the search results did not contain useful "
            "content for the question — either because results were off-topic, "
            "or because no results were returned. Null if the question is "
            "sufficiently covered by the extracted_evidence items. "
            "Maximum 400 characters."
        ),
    )


class ReaderOutput(BaseModel):
    """Post-validation shape for per-question Reader output.

    Produced by the reader service from ReaderOutputDraft after URL
    cross-reference and quote-substring validation on each evidence item.
    The orchestrator collects ReaderOutput objects into
    dict[str, ReaderOutput] (keyed by question_id) before passing them
    to the Synthesizer (planning doc §4.4, ADR 0010).

    On per-question LLM failure, the reader service produces a sentinel
    ReaderOutput with extracted_evidence=[] and evidence_gap_note set
    to a standard failure message (planning doc §8.1).

    All caps are first-pass estimates; re-calibrate after 20 real runs
    per docs/llm-schema-calibration.md and docs/calibration/procedure.md.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(
        ...,
        description=(
            "The id of the research question this output covers. One of q1–q7. "
            "Used by the orchestrator as the key in dict[str, ReaderOutput]."
        ),
    )

    extracted_evidence: list[ExtractedEvidence] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "0–10 validated ExtractedEvidence items for this question. "
            "Empty when no useful evidence was found or when the LLM call "
            "failed (sentinel path). Maximum 10 items."
        ),
    )

    evidence_gap_note: str | None = Field(
        None,
        max_length=400,
        description=(
            "1–2 sentences on what this question could not find evidence for. "
            "Non-null when extracted_evidence is empty or sparse. "
            "Set to the standard sentinel message on LLM call failure. "
            "Null if the question is sufficiently covered. Maximum 400 characters."
        ),
    )
