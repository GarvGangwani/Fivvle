"""Pydantic output schema for the research-engine Planner phase.

Represents the structured output returned by plan_research() — a ResearchPlan
containing 5-7 ResearchQuestions with stable ids, rationale, and Tavily-ready
search queries.

Per ARCHITECTURE.md Sequence Diagram 8b, Phase 1 (Planner):
    plan(refined_idea) → 5-7 research questions

Used as the response_model argument to llm_client.complete_structured().
Instructor passes the Field() descriptions to Claude as part of the prompt.
Every description must be precise enough to guide correct output.

Per AGENTS.md "LLM and agent security" and AGENTS.md "Logging hygiene":
- Never log ResearchPlan content — only log counts and metadata.
- ResearchQuestion.search_queries are Tavily inputs, not executed here.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Per-item constraint for search_queries: each query max 120 chars.
_QueryStr = Annotated[str, Field(min_length=1, max_length=120)]


class ResearchQuestion(BaseModel):
    """A single research question in a ResearchPlan.

    id is a stable cross-phase reference (q1–q7). The Searcher, Reader,
    Reflector, and Synthesizer phases all address questions by their id.
    """

    model_config = ConfigDict(extra="forbid")

    id: Annotated[
        str,
        Field(
            pattern=r"^q[1-7]$",
            description=(
                "Stable identifier for this question. Must be one of: q1, q2, q3, q4, "
                "q5, q6, q7. All ids within a ResearchPlan must be unique. This id is "
                "used as the cross-phase reference — the Searcher, Reader, Reflector, "
                "and Synthesizer each address questions by this id."
            ),
        ),
    ]

    question: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description=(
                "The research question itself, stated as a single sentence. Must be sharp "
                "and concrete — specific enough that a Tavily search would return relevant "
                "results. Not a generic category ('what is the competitive landscape?') "
                "but a pointed question ('does Notion AI's policy-bot feature already cover "
                "what this idea proposes?'). Maximum 300 characters."
            ),
        ),
    ]

    rationale: Annotated[
        str,
        Field(
            min_length=1,
            max_length=400,
            description=(
                "1-2 sentences explaining why this specific question matters for THIS idea, "
                "and why it is investigable from public web sources. The rationale must name "
                "the specific risk or dimension it addresses and explain how Tavily searches "
                "could surface evidence. Do not write generic rationale that applies to any "
                "startup — it must be tailored to this idea. Maximum 400 characters."
            ),
        ),
    ]

    search_queries: Annotated[
        list[_QueryStr],
        Field(
            min_length=1,
            max_length=3,
            description=(
                "1-3 Tavily-ready search queries for this question. Each query: 3-8 words, "
                "concrete entity names where relevant (e.g. 'Notion AI policy bot Slack' not "
                "'AI bots in workplace'), no quotation marks, no site: filters, no operators. "
                "Queries must be diverse — three paraphrases of the same query are wasteful; "
                "three queries approaching the question from different angles (one for direct "
                "competitors, one for user complaints, one for industry analysis) are valuable. "
                "If one query covers the question fully, one is sufficient. Max 3 queries, "
                "each max 120 characters."
            ),
        ),
    ]


class ResearchPlan(BaseModel):
    """Structured output of the Planner phase (ARCHITECTURE.md Sequence 8b, Phase 1).

    Contains 5-7 ResearchQuestions that collectively span at least 4 research
    dimensions (market size, competition, willingness-to-pay, distribution, technical
    feasibility, regulatory, supply-side). The Searcher phase uses search_queries;
    the Synthesizer consumes questions and notes_for_synthesizer.
    """

    model_config = ConfigDict(extra="forbid")

    questions: Annotated[
        list[ResearchQuestion],
        Field(
            min_length=5,
            max_length=7,
            description=(
                "5-7 ResearchQuestion items. Must cover at least 4 distinct research "
                "dimensions from: market size/growth, named competitors and positioning, "
                "willingness-to-pay evidence, distribution/acquisition channels, technical "
                "feasibility, regulatory/legal constraints, supply-side dynamics. Do not "
                "cluster multiple questions on the same dimension. At least 3 questions "
                "must be directly downstream of the risks stated in the RefinedIdea."
            ),
        ),
    ]

    notes_for_synthesizer: Annotated[
        str | None,
        Field(
            default=None,
            max_length=600,
            description=(
                "Optional planner-level observations for the Synthesizer phase. Use this "
                "when the idea has meaningful investigability limits (e.g. 'founder's idea "
                "is vague — synthesizer should flag investigability limits rather than "
                "fabricating findings'). Leave null if the idea is specific and well-defined. "
                "Maximum 600 characters."
            ),
        ),
    ]

    @model_validator(mode="after")
    def _unique_question_ids(self) -> ResearchPlan:
        """Reject a ResearchPlan where two questions share the same id.

        Duplicate ids would cause cross-phase references to become ambiguous —
        the Searcher and Reader phases address questions by id.
        """
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            seen: set[str] = set()
            duplicates: list[str] = []
            for qid in ids:
                if qid in seen:
                    duplicates.append(qid)
                seen.add(qid)
            raise ValueError(f"Duplicate question ids in ResearchPlan: {duplicates}")
        return self
