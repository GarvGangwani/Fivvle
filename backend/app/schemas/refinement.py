"""Pydantic output schema for the AI idea-refinement call.

This model represents the structured output returned by the refinement LLM call,
referenced by USER_FLOW Stage 2, Step 2.2. It is the shape stored in
Experiment.refined_idea (JSONB column) after a successful refinement.

Per ARCHITECTURE.md Class Diagram: Experiment.refined_idea is JSON — this model
defines the exact shape of that JSON. Match field names exactly; the frontend
reads these keys when rendering the refinement review form (FE3).

Used as the response_model argument to llm_client.complete_structured() — Instructor
passes the Field() descriptions to Claude as part of the structured output prompt.
Every description should be precise enough that Claude produces the correct output
even without reading the full system prompt.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Per-item constraint for the risks list: each risk is a single sentence, max 200 chars.
_RiskStr = Annotated[str, Field(min_length=1, max_length=200)]


class RefinedIdea(BaseModel):
    """Structured output of the refinement LLM call (USER_FLOW Stage 2).

    Every field carries a description used by Instructor to guide Claude
    toward the correct output. Constraints are enforced by Pydantic at parse
    time — any violation raises ValidationError before the result reaches the
    service layer. The endpoint layer (wired in B1-wire) is responsible for
    translating that into an HTTP 422.
    """

    model_config = ConfigDict(extra="forbid")

    refined_one_liner: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description=(
                "A single, crisp sentence that captures what the product does and for whom. "
                "It must be self-contained — someone who has never heard of the idea should "
                "fully understand it after reading this once. No jargon, no filler words. "
                "Maximum 200 characters."
            ),
        ),
    ]

    target_audience: Annotated[
        str,
        Field(
            min_length=1,
            max_length=300,
            description=(
                "A vivid, specific portrait of the primary user. Go beyond job titles and "
                "demographic brackets. Describe the person in their context: their role, "
                "their specific situation, the exact frustration they feel. Example: "
                "'nurses on night shifts at understaffed regional hospitals who spend 40 "
                "minutes per shift writing manual handoff notes', not 'healthcare workers'. "
                "Maximum 300 characters."
            ),
        ),
    ]

    value_proposition: Annotated[
        str,
        Field(
            min_length=1,
            max_length=400,
            description=(
                "The concrete outcome this product delivers to the target audience. "
                "State the change that happens for the user, not the features you ship. "
                "'Reduces shift handoff time from 40 minutes to 5 minutes' is a value "
                "proposition. 'An intelligent platform that streamlines workflows' is not. "
                "Maximum 400 characters."
            ),
        ),
    ]

    risks: Annotated[
        list[_RiskStr],
        Field(
            min_length=3,
            max_length=5,
            description=(
                "3–5 specific, investigable risks or open questions. These are NOT generic "
                "startup risks ('market risk', 'execution risk'). Each is a concrete "
                "question that a market research engine can actually look up: 'Are nurses "
                "at understaffed hospitals already using Dragon or Nuance for handoff notes?', "
                "'Is the 40-minute handoff claim consistent across hospital sizes or only in "
                "high-acuity units?'. Each item is one sentence, max 200 characters."
            ),
        ),
    ]

    headline: Annotated[
        str,
        Field(
            min_length=1,
            max_length=80,
            description=(
                "Landing page hero headline. Concrete, benefit-first. "
                "Do NOT use: Revolutionize, Unlock, Transform, Empower, Next-level, "
                "Game-changing, Seamless, Powerful, Cutting-edge. "
                "State the actual benefit in plain language. Maximum 80 characters."
            ),
        ),
    ]

    subheadline: Annotated[
        str,
        Field(
            min_length=1,
            max_length=160,
            description=(
                "One supporting sentence that expands the headline with specifics. "
                "Should answer either 'how does it work?' or 'exactly who is this for?'. "
                "Adds the detail the headline can't fit at 80 characters. Maximum 160 characters."
            ),
        ),
    ]

    cta_text: Annotated[
        str,
        Field(
            min_length=1,
            max_length=30,
            description=(
                "Call-to-action button label. Action-oriented, specific to the offer. "
                "Examples: 'Join the waitlist', 'Get early access', 'See how it works'. "
                "Not: 'Click here', 'Submit', 'Learn more'. Maximum 30 characters."
            ),
        ),
    ]
