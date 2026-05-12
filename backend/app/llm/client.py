"""LLM client wrapper.

EVERY LLM CALL IN FIVVLE MUST GO THROUGH THIS MODULE. Direct imports
of `anthropic` or `groq` SDKs anywhere else are a violation of
`.cursorrules` "What NOT to do" and AGENTS.md "LLM and agent security".

The wrapper enforces:
- Cost tracking via LLMCall logging on every call (success and failure)
- Lazy client instantiation (no network calls at app boot)
- Provider-agnostic interface — callers use complete() without caring whether
  Anthropic or Groq is serving the request
- Structured output via Instructor when a Pydantic schema is provided

Per AGENTS.md, do NOT cache decoded LLM outputs across requests, do NOT use
LLM outputs as code or shell commands, and ALWAYS validate scraped content
in prompts as untrusted data.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, TypeVar
from uuid import UUID

import anthropic
import groq
import instructor
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.llm_call import LLMCall
from app.llm.cost import compute_cost_usd, is_known_model
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    pass

_logger = get_logger(__name__)

# Lazy module-level client cache. Built on first use of each provider.
_anthropic_client: anthropic.AsyncAnthropic | None = None
_groq_client: groq.AsyncGroq | None = None
_instructor_anthropic_client: instructor.AsyncInstructor | None = None
_instructor_groq_client: instructor.AsyncInstructor | None = None


T = TypeVar("T", bound=BaseModel)

ProviderName = Literal["anthropic", "groq"]


class LLMResult(BaseModel):
    """Result envelope for an LLM call.

    Fields are populated whether the call succeeded or failed. On failure,
    the underlying exception is re-raised after logging — this struct is
    only returned on success.
    """

    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    latency_ms: int


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client  # noqa: PLW0603
    if _anthropic_client is None:
        settings = get_settings()
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_groq_client() -> groq.AsyncGroq:
    global _groq_client  # noqa: PLW0603
    if _groq_client is None:
        settings = get_settings()
        _groq_client = groq.AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client


def _get_instructor_anthropic() -> instructor.AsyncInstructor:
    global _instructor_anthropic_client  # noqa: PLW0603
    if _instructor_anthropic_client is None:
        _instructor_anthropic_client = instructor.from_anthropic(_get_anthropic_client())
    return _instructor_anthropic_client


def _get_instructor_groq() -> instructor.AsyncInstructor:
    global _instructor_groq_client  # noqa: PLW0603
    if _instructor_groq_client is None:
        _instructor_groq_client = instructor.from_groq(_get_groq_client())
    return _instructor_groq_client


async def _log_llm_call(
    db: AsyncSession,
    *,
    experiment_id: UUID | None,
    phase: str | None,
    provider: str,
    model: str,
    prompt_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: Decimal,
    latency_ms: int,
    request_id: str | None,
) -> None:
    """Persist one row to llm_calls. Does NOT commit — caller controls tx."""
    call = LLMCall(
        experiment_id=experiment_id,
        phase=phase,
        provider=provider,
        model=model,
        prompt_name=prompt_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        request_id=request_id,
    )
    db.add(call)
    await db.flush()


async def complete(
    db: AsyncSession,
    *,
    provider: ProviderName,
    model: str,
    prompt_name: str,
    system: str,
    user: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    experiment_id: UUID | None = None,
    phase: str | None = None,
) -> LLMResult:
    """Plain-text completion.

    Args:
        db: AsyncSession. The caller's transaction. The wrapper writes a
            LLMCall row inside this session and flushes it.
        provider: "anthropic" or "groq".
        model: provider-specific model identifier (e.g. "claude-sonnet-4-6").
        prompt_name: a stable identifier for the prompt template, used for
            cost analytics ("refinement", "research_planner", etc.).
        system: system prompt.
        user: user prompt (per AGENTS.md, treat any web-scraped or
            user-supplied content INSIDE user as untrusted data, not
            instructions — see the example template in AGENTS.md).
        max_tokens, temperature: passed through to provider.
        experiment_id: optional FK for cost rollup. None for system-level
            calls (admin tooling, etc.).
        phase: optional descriptor for the experiment phase ("planner",
            "reader", etc.).

    Returns:
        LLMResult on success.

    Raises:
        anthropic.APIError, groq.APIError: provider-side failures. The
        wrapper logs a zero-cost row before re-raising so cost dashboards
        capture failures.
    """
    if not is_known_model(provider, model):
        _logger.warning(
            "llm call using unknown model",
            provider=provider,
            model=model,
        )

    started_at = time.perf_counter()

    try:
        if provider == "anthropic":
            client = _get_anthropic_client()

            async def _do_anthropic_call():
                return await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )

            @retry_async()
            async def _call_anthropic_with_retry():
                return await get_breaker("anthropic").call(_do_anthropic_call)

            response = await _call_anthropic_with_retry()
            text = response.content[0].text  # type: ignore[union-attr]
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            request_id: str | None = response.id

        elif provider == "groq":
            client = _get_groq_client()

            async def _do_groq_call():
                return await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )

            @retry_async()
            async def _call_groq_with_retry():
                return await get_breaker("groq").call(_do_groq_call)

            response = await _call_groq_with_retry()
            text = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            request_id = response.id

        else:
            raise ValueError(f"unknown provider: {provider}")

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        cost_usd = compute_cost_usd(provider, model, prompt_tokens, completion_tokens)

        await _log_llm_call(
            db,
            experiment_id=experiment_id,
            phase=phase,
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            request_id=request_id,
        )

        # Log call summary — NO prompt content, NO completion content.
        # Per AGENTS.md "Logging hygiene": NEVER log full prompts or outputs.
        _logger.info(
            "llm call completed",
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=str(cost_usd),
            latency_ms=latency_ms,
        )

        return LLMResult(
            text=text,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

    except Exception as exc:
        # Log a failure row with zero tokens. This makes failed calls
        # visible in cost dashboards (count of failures by provider/model).
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_llm_call(
                db,
                experiment_id=experiment_id,
                phase=phase,
                provider=provider,
                model=model,
                prompt_name=prompt_name,
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=Decimal("0"),
                latency_ms=latency_ms,
                request_id=None,
            )
        except Exception as log_exc:
            # If logging itself fails, don't mask the original error.
            _logger.warning("failed to log failed llm call", error=str(log_exc))

        _logger.warning(
            "llm call failed",
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            error_type=type(exc).__name__,
        )
        raise


async def complete_structured(
    db: AsyncSession,
    *,
    provider: ProviderName,
    model: str,
    prompt_name: str,
    system: str,
    user: str,
    response_model: type[T],
    max_tokens: int = 4096,
    temperature: float = 0.3,  # lower default for structured — less drift
    experiment_id: UUID | None = None,
    phase: str | None = None,
) -> tuple[T, LLMResult]:
    """Structured completion via Instructor.

    Returns (parsed_pydantic_model, LLMResult). The Pydantic model carries
    the parsed structured output; LLMResult carries cost/token metadata.

    Use this for any LLM call where the downstream consumer expects a
    typed structure — refinement, research planner, synthesizer, etc.

    Same logging/cost-tracking semantics as `complete`.

    Instructor API note (verified against instructor==1.15.1):
    - `create_with_completion` is called directly on the AsyncInstructor
      object (not on .chat.completions). It returns (parsed_model, raw_response).
    - Anthropic: system message passed as `system=` kwarg alongside messages.
    - Groq: system message placed in messages list as {"role": "system", ...}.
    """
    if not is_known_model(provider, model):
        _logger.warning(
            "llm call using unknown model",
            provider=provider,
            model=model,
        )

    started_at = time.perf_counter()

    try:
        if provider == "anthropic":
            iclient = _get_instructor_anthropic()

            async def _do_anthropic_structured():
                return await iclient.create_with_completion(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    response_model=response_model,
                )

            @retry_async()
            async def _call_anthropic_structured_with_retry():
                return await get_breaker("anthropic").call(_do_anthropic_structured)

            parsed, raw = await _call_anthropic_structured_with_retry()
            prompt_tokens = raw.usage.input_tokens
            completion_tokens = raw.usage.output_tokens
            request_id: str | None = raw.id

        elif provider == "groq":
            iclient = _get_instructor_groq()

            async def _do_groq_structured():
                return await iclient.create_with_completion(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_model=response_model,
                )

            @retry_async()
            async def _call_groq_structured_with_retry():
                return await get_breaker("groq").call(_do_groq_structured)

            parsed, raw = await _call_groq_structured_with_retry()
            prompt_tokens = raw.usage.prompt_tokens if raw.usage else 0
            completion_tokens = raw.usage.completion_tokens if raw.usage else 0
            request_id = raw.id

        else:
            raise ValueError(f"unknown provider: {provider}")

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        cost_usd = compute_cost_usd(provider, model, prompt_tokens, completion_tokens)

        await _log_llm_call(
            db,
            experiment_id=experiment_id,
            phase=phase,
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            request_id=request_id,
        )

        _logger.info(
            "llm structured call completed",
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=str(cost_usd),
            latency_ms=latency_ms,
            response_model=response_model.__name__,
        )

        result = LLMResult(
            text="",  # structured calls don't expose raw text — use parsed instead
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

        return parsed, result

    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            await _log_llm_call(
                db,
                experiment_id=experiment_id,
                phase=phase,
                provider=provider,
                model=model,
                prompt_name=prompt_name,
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=Decimal("0"),
                latency_ms=latency_ms,
                request_id=None,
            )
        except Exception as log_exc:
            _logger.warning("failed to log failed llm call", error=str(log_exc))

        _logger.warning(
            "llm structured call failed",
            provider=provider,
            model=model,
            prompt_name=prompt_name,
            response_model=response_model.__name__,
            error_type=type(exc).__name__,
        )
        raise
