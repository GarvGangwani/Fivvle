"""Rubric for grading ValidationReports produced by the research engine.

Each ValidationReport is scored against five criteria. Scores run 1–5 per criterion;
definitions below are the canonical guide a human grader uses when filling out a
ValidationReportEval.

RUBRIC_VERSION is incremented when criterion definitions change. Historical scores
are only comparable within the same rubric version — record the version alongside
every scored eval run so regressions are detectable.

---

CRITERION DEFINITIONS

citation_quality
    Are claims backed by specific, relevant source URLs from Tavily results?

    Score 5 — every non-trivial claim has a URL; URLs resolve to sources that
    actually support the claim; no paraphrasing misrepresents the source.

    Score 3 — most claims are cited but 1–2 findings lack any source; or some
    citations exist but are only loosely related to the claim they support.

    Score 1 — multiple findings have no citations; or citations are bulk-listed
    at the bottom without linking to specific claims; or URLs are hallucinated
    (do not exist or do not support the stated finding).

    Watch for: claims that read as authoritative but have no URL; citations that
    point to a source's homepage rather than the specific page with the evidence.

specificity
    Do findings include concrete numbers, named competitors, real user complaints,
    specific market sizes, and named studies — or are they generic summaries?

    Score 5 — "According to Sensor Tower Q3 2024, MyFitnessPal has 200M downloads
    with a 14-day D30 retention of 8%" is a 5. "The fitness app market is large
    and competitive" is a 1.

    Score 3 — some concrete numbers and named entities, but key claims remain at
    summary level ("many competitors exist", "significant market opportunity").

    Score 1 — entirely generic; no named companies, no figures, no specific
    evidence; reads like a GPT summary of publicly available startup advice.

    Watch for: round market-size numbers with no source ("$10B market") that the
    engine may have confabulated; competitor lists that are missing obvious players.

investigability
    Did the research engine chase the specific risks and open questions surfaced
    by the refinement step — or did it generate generic startup commentary?

    Score 5 — the research questions map directly onto the 3–5 risks in the
    RefinedIdea; each question is answered (or acknowledged as unanswerable from
    available data) by at least one finding with a citation.

    Score 3 — some questions address refinement risks, but 1–2 questions are
    generic ("what is the competitive landscape?") that any idea would generate,
    diluting the specific insight the founder needs.

    Score 1 — questions bear no relationship to the specific risks identified in
    refinement; findings read as generic market research for the broad category
    rather than targeted investigation of the stated hypotheses.

    Watch for: a planner that generates 6 questions about "market size" for an
    idea whose refinement risks were about regulatory or distribution blockers —
    that is an investigability failure.

coverage
    Do the 5–7 research questions span the meaningful dimensions of the idea, or
    do they cluster on one dimension?

    Score 5 — questions cover at least 4 of the following where applicable:
    market size/growth, named competitors and their positioning, willingness-to-pay
    evidence, distribution/acquisition channels, technical feasibility, regulatory
    or legal constraints, supply-side dynamics (for marketplaces).

    Score 3 — 3 out of the applicable dimensions are covered; remaining questions
    are variations on a single theme (e.g., three competitor-landscape questions
    with no WTP or distribution question).

    Score 1 — questions are almost entirely about one dimension (typically
    "is this market big?" or "who are competitors?") with no investigation of
    distribution, pricing, or regulatory context.

    Watch for: a report that thoroughly covers competitors but has zero findings
    about how the founder would actually acquire customers — that's a coverage gap
    that will lead founders to overestimate viability.

honesty
    When sources contradict, evidence is thin, or the idea is too vague to
    research, does the report say so — or does it fabricate confident findings?

    Score 5 — the report explicitly notes when evidence is limited or conflicting;
    confidently-stated claims are backed by citations; for the deliberately-vague
    eval idea (vague-ai-productivity), the report explicitly states the idea is
    too vague to research without sharpening rather than inventing findings.

    Score 3 — most claims are honest but 1–2 findings are stated with more
    confidence than the cited evidence supports; thin evidence is not flagged.

    Score 1 — the report fabricates specific competitors, market sizes, or user
    quotes with no citations; or for the vague idea, generates authoritative
    findings as if the product were well-defined.

    Watch for: competitor names that cannot be found in any search result; market
    size figures that differ significantly from the cited source; "users report..."
    claims without any source.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

RUBRIC_VERSION = "v1"


class RubricScore(BaseModel):
    """Score from 1 (poor) to 5 (excellent) for a single rubric criterion."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=1, le=5)
    justification: str = Field(
        min_length=1,
        description=(
            "1–3 sentences explaining the score. Reference specific findings or "
            "missing evidence from the report — not generic statements about the criterion."
        ),
    )


class ValidationReportEval(BaseModel):
    """Full eval result for one ValidationReport graded against the rubric.

    Fill one of these per idea per eval run. Store results alongside the
    ValidationReport JSON and the RUBRIC_VERSION so historical comparisons
    remain valid.
    """

    model_config = ConfigDict(extra="forbid")

    idea_id: str = Field(
        description="The EvalIdea.id this report was graded against (e.g. 'slack-hr-bot')."
    )
    citation_quality: RubricScore
    specificity: RubricScore
    investigability: RubricScore
    coverage: RubricScore
    honesty: RubricScore
    overall_notes: str = Field(
        min_length=1,
        description=(
            "2–4 sentence holistic assessment. What did the report do well? "
            "What is the single biggest improvement needed before this prompt ships?"
        ),
    )
