"""Synthesizer input bridge — packages all phase outputs into a prompt-ready structure.

This module bundles the three inputs that the synthesizer needs into a single,
deterministic, validated structure. Keeping this bridge separate from the
synthesizer service and prompt module has three benefits:

1. The prompt module (synthesizer.py) stays clean — it only reads from
   SynthesizerInput, never from raw TavilyResult dicts.
2. The content-length truncation (TavilyResultForPrompt.content_excerpt at
   1500 chars) lives in one place, making prompt-size budget visible and
   configurable without touching the prompt itself.
3. Tests can construct SynthesizerInput directly without needing real Tavily
   call results.

Per AGENTS.md "Logging hygiene":
- This module constructs a structure that includes scraped Tavily content.
  NEVER log the content of TavilyResultForPrompt — only log counts.

Per AGENTS.md "LLM and agent security":
- The synthesizer prompt wraps Tavily content in <tavily_results> tags with
  explicit instructions to treat that content as untrusted data. This module
  prepares the trimmed content that goes inside those tags. The security
  framing happens in the prompt; this module is just the data shaper.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.tavily import TavilyResult
from app.schemas.planner import ResearchPlan
from app.schemas.refinement import RefinedIdea

# Maximum character length for a Tavily result's content in the synthesizer
# prompt. Tavily returns content snippets that can be several thousand chars.
# Capping at 3000 doubles per-result evidence depth at modest input-token cost.
# With 7 questions × ~10 results × ~3000 chars = ~210,000 chars from results
# alone. That's well within Claude's 200K context window but bounded for cost.
_CONTENT_EXCERPT_MAX_CHARS = 3000


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


class SynthesizerInput(BaseModel):
    """All inputs the synthesizer needs, packaged for prompt building.

    Combines the founder context (RefinedIdea), the research questions
    (ResearchPlan), the search results (per question), and the rubric
    version into a single validated structure.

    Immutable once created — the prompt builder reads from this struct
    deterministically. No side effects.
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

    search_results_by_question: dict[str, list[TavilyResultForPrompt]] = Field(
        description=(
            "Mapping of question_id to trimmed TavilyResults for that question. "
            "Keys are question ids ('q1'..'q7') matching the ResearchPlan questions. "
            "Values are lists of TavilyResultForPrompt with content capped at 3000 chars. "
            "Questions with no results have an empty list."
        )
    )

    rubric_version: str = Field(
        description=(
            "The rubric version string passed through to ValidationReport.rubric_version_used. "
            "For grading audit trail — allows evaluators to know which rubric criteria "
            "apply to a given report. Example: 'v1'."
        )
    )


def build_synthesizer_input(
    refined_idea: RefinedIdea,
    research_plan: ResearchPlan,
    tavily_results: dict[str, list[TavilyResult]],
    rubric_version: str,
) -> SynthesizerInput:
    """Package all phase outputs into a SynthesizerInput for the prompt builder.

    Trims TavilyResult.content to _CONTENT_EXCERPT_MAX_CHARS characters and
    builds TavilyResultForPrompt objects. Questions in the plan that have no
    results in tavily_results get an empty list (the searcher may have had
    partial failures).

    Args:
        refined_idea: Validated RefinedIdea from the refinement phase.
        research_plan: Validated ResearchPlan from the Planner phase.
        tavily_results: Output of execute_search_plan() — maps question_id
            to a list of TavilyResult objects (already deduplicated by the
            searcher service).
        rubric_version: Rubric version string (e.g. "v1") for the report's
            audit trail.

    Returns:
        A fully populated SynthesizerInput ready for the prompt builder.
    """
    trimmed: dict[str, list[TavilyResultForPrompt]] = {}

    for question in research_plan.questions:
        raw_results = tavily_results.get(question.id, [])
        prompt_results: list[TavilyResultForPrompt] = []

        for r in raw_results:
            # Cap content at the max excerpt length. Tavily content snippets
            # can be several KB; we trim to keep prompt size bounded.
            excerpt = r.content[:_CONTENT_EXCERPT_MAX_CHARS]

            prompt_results.append(
                TavilyResultForPrompt(
                    url=r.url,
                    title=r.title,
                    content_excerpt=excerpt,
                    score=r.score,
                )
            )

        trimmed[question.id] = prompt_results

    return SynthesizerInput(
        refined_idea=refined_idea,
        research_plan=research_plan,
        search_results_by_question=trimmed,
        rubric_version=rubric_version,
    )
