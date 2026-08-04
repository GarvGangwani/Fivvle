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

from collections.abc import Callable
from uuid import UUID

from instructor.core.exceptions import InstructorRetryException
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.experiment import Experiment
from app.llm.prompts.refinement import (
    PROMPT_NAME,
    PROMPT_NAME_V5_CHAT,
    REFINEMENT_SYSTEM_PROMPT,
    REFINEMENT_V2_CHAT_SYSTEM_PROMPT,
    build_refinement_user_prompt,
    build_refinement_v2_chat_user_prompt,
)
from app.utils.experiment_naming import apply_llm_name_if_unset
from app.services.tag_service import persist_experiment_tags
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea, RefinementTurnDecision

_logger = get_logger(__name__)

REFINEMENT_CHAT_CACHE_BREAKPOINTS: list[llm_client.CacheBreakpoint] = [
    llm_client.CacheBreakpoint(position="system_end", ttl="1h"),
]

# Model/provider defaults live in Settings (refinement_provider/refinement_model).
# Beta ships Haiku across all phases; override via env without code changes.

# Per .cursorrules "Required timeouts": 60s for refinement LLM calls.
_REFINEMENT_MAX_TOKENS = 1024  # RefinedIdea output is small; cap prevents runaway cost.
# Rail clarifying turns should stay short (question + options). Full idea
# regeneration is discouraged by the rail prompt; 512 still fits a rare update.
_RAIL_REFINE_MAX_TOKENS = 512

_MAX_GRACEFUL_RETRIES = 1  # Service-level retry budget on ValidationError.
# Each retry is one extra LLM call; cost depends on Settings refinement_model.
# See docs/llm-schema-calibration.md.

_REFINEMENT_PROMPT_NAME_RETRY = "refinement_v1_retry"

PROMPT_NAME_V2_CHAT_RETRY = "refinement_v2_chat_retry"


def _format_error_loc(loc: object) -> str:
    if not isinstance(loc, tuple) or not loc:
        return "field"
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        else:
            parts.append(str(item))
    head = parts[0]
    tail = "".join(parts[1:])
    return head + tail


def _validation_error_from_refinement_failure(exc: BaseException) -> ValidationError | None:
    if isinstance(exc, ValidationError):
        return exc
    if isinstance(exc, InstructorRetryException):
        for att in reversed(exc.failed_attempts or ()):
            inner = att.exception
            if isinstance(inner, ValidationError):
                return inner
        if isinstance(exc.__cause__, ValidationError):
            return exc.__cause__
    return None


def _length_retry_user_suffix(val_err: ValidationError) -> str | None:
    lines: list[str] = []
    for err in val_err.errors():
        if err.get("type") != "string_too_long":
            return None
        loc = err.get("loc")
        if not isinstance(loc, tuple):
            return None
        ctx = err.get("ctx")
        if not isinstance(ctx, dict):
            return None
        max_len = ctx.get("max_length")
        inp = err.get("input")
        if max_len is None or not isinstance(inp, str):
            return None
        field_label = _format_error_loc(loc)
        lines.append(f"- {field_label} was {len(inp)} chars (limit: {max_len})")
    if not lines:
        return None
    return (
        "Your previous response failed validation:\n"
        + "\n".join(lines)
        + "\n\n"
        "Rewrite ONLY those specific fields under their limits.\n"
        "Keep all other fields identical to your previous response.\n"
        "Do not shorten by removing specifics — tighten phrasing."
    )


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
        pydantic.ValidationError: Schema constraint violation when not recoverable
            via the one-shot length retry, or when the retry also fails validation.

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

    settings = get_settings()

    try:
        parsed, meta = await llm_client.complete_structured(
            db,
            provider=settings.refinement_provider,
            model=settings.refinement_model,
            prompt_name=PROMPT_NAME,
            system=REFINEMENT_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=RefinedIdea,
            max_tokens=_REFINEMENT_MAX_TOKENS,
            temperature=0.4,  # slight warmth for creative headline/CTA variation
            max_retries=0,
            experiment_id=experiment_id,
            phase="refinement",
        )
    except Exception as exc:
        val_err = _validation_error_from_refinement_failure(exc)
        if val_err is None:
            raise

        suffix = _length_retry_user_suffix(val_err)
        if suffix is None:
            raise exc

        overflow_fields = [
            _format_error_loc(e["loc"])
            for e in val_err.errors()
            if e.get("type") == "string_too_long"
            and isinstance(e.get("loc"), tuple)
        ]
        _logger.info(
            "refinement validation retry triggered",
            overflow_fields=overflow_fields,
            attempt=2,
            experiment_id=str(experiment_id) if experiment_id else None,
        )
        retry_user = f"{user_prompt}\n\n{suffix}"
        try:
            parsed, meta = await llm_client.complete_structured(
                db,
                provider=settings.refinement_provider,
                model=settings.refinement_model,
                prompt_name=_REFINEMENT_PROMPT_NAME_RETRY,
                system=REFINEMENT_SYSTEM_PROMPT,
                user=retry_user,
                response_model=RefinedIdea,
                max_tokens=_REFINEMENT_MAX_TOKENS,
                temperature=0.4,
                max_retries=0,
                experiment_id=experiment_id,
                phase="refinement",
            )
        except Exception as retry_exc:
            _logger.warning(
                "refinement validation retry also failed",
                error_type=type(retry_exc).__name__,
                experiment_id=str(experiment_id) if experiment_id else None,
            )
            raise retry_exc

        _logger.info(
            "refinement validation retry succeeded",
            experiment_id=str(experiment_id) if experiment_id else None,
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


async def run_turn(
    db: AsyncSession,
    experiment: Experiment,
    chat_history: list[tuple[str, str]],
    latest_message: str,
    *,
    bump_refinement_count: bool = True,
    prompt_name: str | None = None,
    system_prompt: str | None = None,
    user_prompt_builder: Callable[..., str] | None = None,
    max_tokens: int | None = None,
) -> RefinementTurnDecision:
    """Run one refinement turn. Always returns a clarify decision.

    Optional ``prompt_name`` / ``system_prompt`` / ``user_prompt_builder`` override
    phase-panel defaults (used by the universal-chat refine sub-agent).
    Optional ``max_tokens`` overrides the default structured-output budget
    (rail clarifying turns use a tighter cap).

    Side effects (in-place on experiment, no commit — caller commits):
    - When bump_refinement_count is True:
      - clarifying_dimension == "pivot_resolution": reset refinement_count to 0
      - otherwise: increment refinement_count by 1
    - When bump_refinement_count is False (retry/edit): leave refinement_count alone
    - When refined_idea is present: write WIP to experiment.refined_idea_current
      (does NOT set experiment.refined_idea or change status — user owns finalize).
    """
    turn_count = experiment.refinement_count

    _logger.info(
        "refinement chat turn started",
        experiment_id=str(experiment.id),
        turn_count=turn_count,
        history_length=len(chat_history),
        latest_message_length=len(latest_message),
        bump_refinement_count=bump_refinement_count,
    )

    settings = get_settings()

    build_user = user_prompt_builder or build_refinement_v2_chat_user_prompt
    current_wip = (
        experiment.refined_idea_current
        if isinstance(experiment.refined_idea_current, dict)
        else None
    )
    user_prompt = build_user(
        chat_history=chat_history,
        latest_message=latest_message,
        turn_count=turn_count,
        max_clarifying_turns=settings.refinement_max_clarifying_turns,
        min_turns_before_finalize=settings.refinement_min_clarifying_turns_before_finalize,
        finalized_refined_idea=(
            experiment.refined_idea
            if isinstance(experiment.refined_idea, dict)
            else None
        ),
        current_wip_idea=current_wip,
    )

    token_budget = max_tokens if max_tokens is not None else _REFINEMENT_MAX_TOKENS

    parsed, meta = await llm_client.complete_structured(
        db,
        provider=settings.refinement_provider,
        model=settings.refinement_model,
        prompt_name=prompt_name or PROMPT_NAME_V5_CHAT,
        system=system_prompt or REFINEMENT_V2_CHAT_SYSTEM_PROMPT,
        user=user_prompt,
        response_model=RefinementTurnDecision,
        max_tokens=token_budget,
        temperature=0.4,
        max_retries=6,
        experiment_id=experiment.id,
        phase="refinement_chat",
        cache_breakpoints=REFINEMENT_CHAT_CACHE_BREAKPOINTS,
    )

    if bump_refinement_count:
        if parsed.clarifying_dimension == "pivot_resolution":
            experiment.refinement_count = 0
        else:
            experiment.refinement_count = turn_count + 1

    if parsed.refined_idea is not None:
        experiment.refined_idea_current = parsed.refined_idea.model_dump()
        experiment.refined_idea_updated_at = func.clock_timestamp()
        apply_llm_name_if_unset(experiment, parsed.refined_idea)
        await persist_experiment_tags(db, experiment, parsed.refined_idea)
        if parsed.targeting is not None:
            if parsed.targeting.target_geography is not None:
                experiment.target_geography = (
                    parsed.targeting.target_geography.strip() or None
                )
            if parsed.targeting.audience_bracket is not None:
                experiment.audience_bracket = (
                    parsed.targeting.audience_bracket.strip() or None
                )
            if parsed.targeting.stage is not None:
                experiment.stage = parsed.targeting.stage
            if parsed.targeting.why_now is not None:
                experiment.why_now = parsed.targeting.why_now.strip() or None

    _logger.info(
        "refinement chat turn completed",
        experiment_id=str(experiment.id),
        decision=parsed.decision,
        clarifying_dimension=parsed.clarifying_dimension,
        has_questions=bool(parsed.clarifying_questions),
        has_wip_refined_idea=parsed.refined_idea is not None,
        refinement_count=experiment.refinement_count,
        bump_refinement_count=bump_refinement_count,
        targeting_geography_present=(
            parsed.targeting is not None
            and parsed.targeting.target_geography is not None
        ),
        targeting_stage_present=(
            parsed.targeting is not None and parsed.targeting.stage is not None
        ),
        prompt_tokens=meta.prompt_tokens,
        completion_tokens=meta.completion_tokens,
        latency_ms=meta.latency_ms,
        max_tokens=token_budget,
        cost_usd=str(meta.cost_usd),
    )

    return parsed.model_copy(update={"reasoning_trace": ""})
