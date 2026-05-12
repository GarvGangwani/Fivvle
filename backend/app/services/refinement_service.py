"""Refinement service — wraps the LLM idea-refinement call.

Single public function: refine_idea().

Called by the Experiment service during idea submission (POST /experiments) and
by the regeneration endpoint (POST /experiments/{id}/refine). Both call sites are
wired in B1-wire; this module is the LLM layer only.

Per .cursorrules:
- This module imports complete_structured from app.llm.client. It does NOT
  import anthropic directly — that would violate AGENTS.md "LLM and agent security".
- LLMCall logging is handled by the client wrapper; this service does not write
  to LLMCall itself.
- Exceptions from complete_structured() propagate to the caller. This layer does
  NOT translate them to HTTP errors — that is the router's responsibility (B1-wire).

Per AGENTS.md "Logging hygiene":
- NEVER log raw_idea content (user-supplied text).
- Log experiment_id and idea character count instead.
- NEVER log LLM prompt content.

NOTE on the db parameter:
  complete_structured() requires an AsyncSession as its first argument because
  the LLM client wrapper writes a LLMCall row (for cost tracking) inside the
  caller's transaction. The session is passed from the router via Depends(get_session)
  and threaded down to this service. This follows the standard FastAPI session-per-
  request pattern established in app.db.session.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.llm.prompts.refinement import (
    PROMPT_NAME,
    REFINEMENT_SYSTEM_PROMPT,
    build_refinement_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea

_logger = get_logger(__name__)

# Claude Sonnet 4.6 — "best balance of speed and intelligence" per cost.py.
# Refinement is a user-facing synchronous call (5-10s budget per USER_FLOW Step 2.2).
# Use Sonnet, not Haiku: quality matters here — the refinement output seeds both
# market research questions and the landing page copy.
_REFINEMENT_MODEL = "claude-sonnet-4-6"
_REFINEMENT_PROVIDER = "anthropic"

# Per .cursorrules "Required timeouts": 60s for refinement LLM calls.
_REFINEMENT_MAX_TOKENS = 1024  # RefinedIdea output is small; cap prevents runaway cost.


async def refine_idea(
    db: AsyncSession,
    raw_idea: str,
    previous_refinement: RefinedIdea | None = None,
    feedback: str | None = None,
    experiment_id: UUID | None = None,
) -> RefinedIdea:
    """Call Claude to refine a founder's raw idea into a structured RefinedIdea.

    Handles both first-pass refinement and regeneration (when previous_refinement
    and optional feedback are supplied). Both cases go through the same structured
    LLM call — the prompt builder constructs the appropriate user turn.

    Args:
        db: AsyncSession from the caller's request context. The LLM client wrapper
            writes a LLMCall row inside this session for cost tracking.
        raw_idea: The founder's submitted text. Treated as untrusted user input by
            the prompt builder (wrapped in XML tags per AGENTS.md).
        previous_refinement: Prior RefinedIdea, if this is a regeneration call.
            None for first-pass refinement.
        feedback: Optional text the founder typed when clicking "Refine again".
            Only meaningful when previous_refinement is provided.
        experiment_id: FK for LLMCall cost rollup. Pass the Experiment.id if
            the experiment row exists; None is valid (e.g., before the DB write).

    Returns:
        Parsed and validated RefinedIdea.

    Raises:
        anthropic.APIError: provider-side failure (network, rate limit, etc.).
        instructor.exceptions.InstructorRetryException: Instructor failed to parse
            a valid RefinedIdea after its retry budget (usually means the model
            output violated a schema constraint).
        pydantic.ValidationError: Should not normally occur after Instructor's parse,
            but surfaced here for completeness.

    All exceptions propagate to the caller. The endpoint layer (B1-wire) translates
    them to appropriate HTTP 5xx responses.
    """
    is_regeneration = previous_refinement is not None

    _logger.info(
        "refinement started",
        idea_length=len(raw_idea),
        is_regeneration=is_regeneration,
        has_feedback=feedback is not None,
        experiment_id=str(experiment_id) if experiment_id else None,
    )

    user_prompt = build_refinement_user_prompt(
        raw_idea=raw_idea,
        previous_refinement=previous_refinement,
        feedback=feedback,
    )

    parsed, meta = await llm_client.complete_structured(
        db,
        provider=_REFINEMENT_PROVIDER,
        model=_REFINEMENT_MODEL,
        prompt_name=PROMPT_NAME,
        system=REFINEMENT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=RefinedIdea,
        max_tokens=_REFINEMENT_MAX_TOKENS,
        temperature=0.4,  # slight warmth for creative headline/CTA variation
        max_retries=1,  # 1 retry = 2 total attempts; caps worst-case cost on schema-validation retries
        experiment_id=experiment_id,
        phase="refinement",
    )

    _logger.info(
        "refinement completed",
        one_liner_length=len(parsed.refined_one_liner),
        audience_length=len(parsed.target_audience),
        risk_count=len(parsed.risks),
        headline_length=len(parsed.headline),
        is_regeneration=is_regeneration,
        experiment_id=str(experiment_id) if experiment_id else None,
        prompt_tokens=meta.prompt_tokens,
        completion_tokens=meta.completion_tokens,
        cost_usd=str(meta.cost_usd),
    )

    return parsed
