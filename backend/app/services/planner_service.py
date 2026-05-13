"""Planner service — wraps the LLM research-planning call.

Single public function: plan_research().

Called by the research engine (Cloud Function) after the refinement phase
has produced a RefinedIdea. Produces a ResearchPlan with 5-7 research
questions that the Searcher phase executes against Tavily.

Per .cursorrules:
- This module imports complete_structured from app.llm.client. It does NOT
  import anthropic directly — that would violate AGENTS.md "LLM and agent security".
- LLMCall logging is handled by the client wrapper; this service does not write
  to LLMCall itself.
- Exceptions from complete_structured() propagate to the caller.

Per AGENTS.md "Logging hygiene":
- NEVER log RefinedIdea content (user-derived text).
- NEVER log the prompt body.
- Log only safe metadata: counts, flags, experiment_id, cost.

NOTE on the db parameter:
  complete_structured() requires an AsyncSession as its first argument because
  the LLM client wrapper writes a LLMCall row (for cost tracking) inside the
  caller's transaction. Pass the session from the calling context.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.llm.prompts.planner import (
    PLANNER_SYSTEM_PROMPT,
    PROMPT_NAME,
    build_planner_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.planner import ResearchPlan
from app.schemas.refinement import RefinedIdea

_logger = get_logger(__name__)

# Claude Sonnet 4.6 — matches refinement_service.py. Per .cursorrules:
# "Do not downgrade models to save pennies. Use Claude for all research phases."
_PLANNER_MODEL = "claude-sonnet-4-6"
_PLANNER_PROVIDER = "anthropic"

# Planner output is larger than refinement (5-7 questions × rationale + queries).
# 2048 tokens provides headroom without runaway cost.
_PLANNER_MAX_TOKENS = 2048

# Vague-idea detection: these substrings in target_audience or value_proposition
# indicate the RefinedIdea is underspecified and the planner should apply honesty rules.
_VAGUE_MARKERS: tuple[str, ...] = (
    "undefined",
    "not specified",
    "to be defined",
    "not yet defined",
    "not defined",
)


async def plan_research(
    db: AsyncSession,
    refined_idea: RefinedIdea,
    experiment_id: UUID | None = None,
) -> ResearchPlan:
    """Call Claude to produce a ResearchPlan from a validated RefinedIdea.

    Generates 5-7 research questions covering at least 4 research dimensions,
    with at least 3 questions downstream of the risks stated in the RefinedIdea.
    Vague ideas trigger the planner's honesty mechanism (minimum 5 questions,
    notes_for_synthesizer populated with an investigability warning).

    Args:
        db: AsyncSession from the caller's context. The LLM client wrapper
            writes a LLMCall row inside this session for cost tracking.
        refined_idea: Validated RefinedIdea from the refinement phase.
            Treated as untrusted input by the prompt builder (wrapped in XML
            tags per AGENTS.md).
        experiment_id: FK for LLMCall cost rollup. Pass the Experiment.id if
            available; None is valid for script-level calls.

    Returns:
        Parsed and validated ResearchPlan.

    Raises:
        anthropic.APIError: provider-side failure (network, rate limit, etc.).
        instructor.exceptions.InstructorRetryException: Instructor failed to parse
            a valid ResearchPlan after its retry budget.
        pydantic.ValidationError: Schema constraint violation in the parsed output.

    All exceptions propagate to the caller.
    """
    # Compute vague-idea flag from safe metadata only (field lengths, presence
    # of known placeholder strings). Never log the field content itself.
    audience_lower = refined_idea.target_audience.lower()
    vp_lower = refined_idea.value_proposition.lower()
    has_vague_audience = any(m in audience_lower for m in _VAGUE_MARKERS) or any(
        m in vp_lower for m in _VAGUE_MARKERS
    )

    _logger.info(
        "planner started",
        has_vague_audience=has_vague_audience,
        risk_count=len(refined_idea.risks),
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    user_prompt = build_planner_user_prompt(refined_idea)

    parsed, meta = await llm_client.complete_structured(
        db,
        provider=_PLANNER_PROVIDER,
        model=_PLANNER_MODEL,
        prompt_name=PROMPT_NAME,
        system=PLANNER_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=ResearchPlan,
        max_tokens=_PLANNER_MAX_TOKENS,
        temperature=0.5,  # mild creativity for question framing
        max_retries=1,  # 1 retry = 2 total attempts; caps worst-case cost
        experiment_id=experiment_id,
        phase="planner",
    )

    total_search_query_count = sum(len(q.search_queries) for q in parsed.questions)

    _logger.info(
        "planner completed",
        question_count=len(parsed.questions),
        total_search_query_count=total_search_query_count,
        has_synthesizer_notes=parsed.notes_for_synthesizer is not None,
        cost_usd=str(meta.cost_usd),
        prompt_tokens=meta.prompt_tokens,
        completion_tokens=meta.completion_tokens,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    return parsed
