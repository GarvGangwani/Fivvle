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
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast
from uuid import UUID

import anthropic
import groq
import instructor
from openai import AsyncOpenAI
from instructor.core.hooks import Hooks
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.cost.category import resolve_cost_category_from_phase
from app.db.models.llm_call import LLMCall
from app.db.session_lock import lock_for
from app.llm.cost import compute_anthropic_cached_cost_usd, compute_cost_usd, is_known_model
from app.logging_config import get_logger
from app.reliability.circuit_breakers import get_breaker
from app.reliability.retry import retry_async

if TYPE_CHECKING:
    pass

_logger = get_logger(__name__)

# Lazy module-level client cache. Built on first use of each provider.
_anthropic_client: anthropic.AsyncAnthropic | None = None
_groq_client: groq.AsyncGroq | None = None
_kimi_client: AsyncOpenAI | None = None
_instructor_anthropic_client: instructor.AsyncInstructor | None = None
_instructor_groq_client: instructor.AsyncInstructor | None = None
_instructor_kimi_client: instructor.AsyncInstructor | None = None


T = TypeVar("T", bound=BaseModel)

ProviderName = Literal["anthropic", "groq", "kimi"]

# Callers that use ``cache_breakpoints`` with ``user_zone_a_end`` / ``user_zone_b_end``
# must join user zones with this exact separator (Zone A | Zone B | Zone C).
USER_CACHE_ZONE_BOUNDARY = "<<<FIVVLE_USER_CACHE_BOUNDARY>>>"


class CacheBreakpoint(BaseModel):
    """Declares where to attach Anthropic ``cache_control`` for prompt caching."""

    model_config = ConfigDict(extra="forbid")

    position: Literal["system_end", "user_zone_a_end", "user_zone_b_end"] = Field(
        ...,
        description="Semantic anchor for the cache marker (not a numeric block index).",
    )
    ttl: Literal["5m", "1h"] = Field(
        ...,
        description="Anthropic ephemeral cache TTL for this breakpoint.",
    )


def _cache_control_payload(ttl: Literal["5m", "1h"]) -> dict[str, str]:
    return {"type": "ephemeral", "ttl": ttl}


def _is_nonempty_user_text(text: str) -> bool:
    return bool(text.strip())


def _merge_cache_control_cascade(
    existing: dict[str, str], incoming: dict[str, str]
) -> dict[str, str]:
    """Combine cache markers when multiple breakpoints land on one text block.

    Anthropic allows one ``cache_control`` per text block. When an empty zone is
    dropped and its marker shifts backward, merge with any marker already on
    the target block: prefer ``1h`` if either TTL is ``1h``, else keep the
    cascaded (incoming) marker.
    """
    et = existing.get("ttl")
    it = incoming.get("ttl")
    if et == "1h" or it == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return dict(incoming)


def _drop_empty_user_text_blocks(
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove whitespace-only user text blocks before sending to Anthropic.

    Empty zone blocks are dropped before send; their ``cache_control`` markers
    cascade to the previous non-empty block (merged via
    ``_merge_cache_control_cascade``). Markers whose block has no prior
    non-empty block are omitted.
    """
    result: list[dict[str, Any]] = []
    for block in blocks:
        text = block.get("text", "")
        if not isinstance(text, str):
            text = ""
        if _is_nonempty_user_text(text):
            result.append(dict(block))
            continue
        incoming_cc = block.get("cache_control")
        if isinstance(incoming_cc, dict) and result:
            prev = result[-1]
            prev_cc = prev.get("cache_control")
            if isinstance(prev_cc, dict):
                prev = dict(prev)
                prev["cache_control"] = _merge_cache_control_cascade(prev_cc, incoming_cc)
                result[-1] = prev
            else:
                prev = dict(prev)
                prev["cache_control"] = dict(incoming_cc)
                result[-1] = prev
    return result


def _validate_cache_breakpoints(breakpoints: list[CacheBreakpoint]) -> None:
    seen: set[str] = set()
    for bp in breakpoints:
        if bp.position in seen:
            raise ValueError(f"duplicate cache breakpoint position: {bp.position}")
        seen.add(bp.position)
    pos = seen
    if "user_zone_b_end" in pos and "user_zone_a_end" not in pos:
        raise ValueError("user_zone_b_end requires user_zone_a_end")


def _split_user_zones_for_cache(
    user: str, *, need_zone_a: bool, need_zone_b: bool
) -> list[str]:
    parts = user.split(USER_CACHE_ZONE_BOUNDARY)
    if need_zone_b:
        if len(parts) != 3:
            raise ValueError(
                "user must split into 3 zones via USER_CACHE_ZONE_BOUNDARY "
                "when user_zone_a_end and user_zone_b_end are both requested"
            )
        return parts
    if need_zone_a:
        if len(parts) != 2:
            raise ValueError(
                "user must split into 2 zones via USER_CACHE_ZONE_BOUNDARY "
                "when only user_zone_a_end is requested"
            )
        return parts
    return [user]


def _anthropic_structured_system_and_messages(
    *,
    system: str,
    user: str,
    cache_breakpoints: list[CacheBreakpoint] | None,
) -> tuple[Any, list[dict[str, Any]]]:
    """Build ``system`` and ``messages`` for Instructor / Anthropic structured calls.

    Empty user zone segments (whitespace-only text blocks) are removed before
    send so Anthropic never receives empty text content blocks. Any
    ``cache_control`` on a dropped block is merged onto the previous non-empty
    block (see ``_drop_empty_user_text_blocks``).
    """
    if not cache_breakpoints:
        return system, [{"role": "user", "content": user}]

    _validate_cache_breakpoints(cache_breakpoints)
    by_pos = {bp.position: bp for bp in cache_breakpoints}

    need_a = "user_zone_a_end" in by_pos
    need_b = "user_zone_b_end" in by_pos
    user_parts = _split_user_zones_for_cache(user, need_zone_a=need_a, need_zone_b=need_b)

    sys_out: Any
    if "system_end" in by_pos:
        ttl = cast(Literal["5m", "1h"], by_pos["system_end"].ttl)
        sys_out = [
            {
                "type": "text",
                "text": system,
                "cache_control": _cache_control_payload(ttl),
            }
        ]
    else:
        sys_out = system

    if not need_a:
        return sys_out, [{"role": "user", "content": user}]

    user_blocks: list[dict[str, Any]] = []
    if need_b:
        ua, ub, uc = user_parts[0], user_parts[1], user_parts[2]
        user_blocks.append(
            {
                "type": "text",
                "text": ua,
                "cache_control": _cache_control_payload(
                    cast(Literal["5m", "1h"], by_pos["user_zone_a_end"].ttl)
                ),
            }
        )
        user_blocks.append(
            {
                "type": "text",
                "text": ub,
                "cache_control": _cache_control_payload(
                    cast(Literal["5m", "1h"], by_pos["user_zone_b_end"].ttl)
                ),
            }
        )
        user_blocks.append({"type": "text", "text": uc})
    else:
        ua, rest = user_parts[0], user_parts[1]
        user_blocks.append(
            {
                "type": "text",
                "text": ua,
                "cache_control": _cache_control_payload(
                    cast(Literal["5m", "1h"], by_pos["user_zone_a_end"].ttl)
                ),
            }
        )
        user_blocks.append({"type": "text", "text": rest})

    user_blocks = _drop_empty_user_text_blocks(user_blocks)
    return sys_out, [{"role": "user", "content": user_blocks}]


def _usage_int_attr(usage: object, name: str) -> int:
    """Anthropic Usage fields appear on real responses but must not treat MagicMocks as counts."""
    v = getattr(usage, name, 0)
    return int(v) if isinstance(v, int) else 0


def _anthropic_usage_accumulator_fields(usage: object) -> tuple[int, int, int, int, int]:
    """(uncached_tail, cache_read, create_total, create_5m, create_1h)."""
    uncached = _usage_int_attr(usage, "input_tokens")
    cache_read = _usage_int_attr(usage, "cache_read_input_tokens")
    create_total = _usage_int_attr(usage, "cache_creation_input_tokens")
    cc_obj = getattr(usage, "cache_creation", None)
    if cc_obj is not None and not isinstance(cc_obj, int):
        c5 = _usage_int_attr(cc_obj, "ephemeral_5m_input_tokens")
        c1 = _usage_int_attr(cc_obj, "ephemeral_1h_input_tokens")
    elif create_total > 0:
        c5, c1 = create_total, 0
    else:
        c5, c1 = 0, 0
    if create_total == 0:
        create_total = c5 + c1
    return uncached, cache_read, create_total, c5, c1


def _extract_kimi_cached_tokens(usage: object) -> int:
    """Return cached input tokens from a Moonshot Kimi usage object.

    Cache-hit tokens surface at usage.prompt_tokens_details.cached_tokens
    (OpenAI-compatible shape). Missing on cache-miss calls and on calls
    below Moonshot's 1024-token cache minimum. Returns 0 in either case.
    """
    details = getattr(usage, "prompt_tokens_details", None)
    if details is None:
        return 0
    return getattr(details, "cached_tokens", 0) or 0


def _request_id_from_response(response: object | None) -> str | None:
    if response is None:
        return None
    rid = getattr(response, "id", None)
    if rid is None:
        return None
    return str(rid)


def _failure_metrics_for_structured_call(
    *,
    provider: ProviderName,
    model: str,
    exc: Exception,
    usage_state: dict[str, Any],
    cache_breakpoints: list[CacheBreakpoint] | None,
) -> tuple[int, int, Decimal, int | None, int | None, str | None]:
    """Best-effort token/cost extraction when ``complete_structured`` fails."""
    from instructor.core.exceptions import InstructorRetryException

    prompt_tokens = 0
    completion_tokens = 0
    cached_in: int | None = None
    cached_create: int | None = None
    request_id: str | None = None
    cost_usd = Decimal("0")

    kind = usage_state.get("kind")
    acc = usage_state.get("acc")
    if isinstance(acc, dict) and acc.get("attempts", 0) > 0:
        if kind == "anthropic":
            unc_t = acc["uncached_tail"]
            cread = acc["cache_read"]
            c5 = acc["create_5m"]
            c1 = acc["create_1h"]
            ctot = acc["create_total"]
            completion_tokens = acc["completion_tokens"]
            prompt_tokens = unc_t + cread + ctot
            cost_usd = compute_anthropic_cached_cost_usd(
                model,
                uncached_tail_input_tokens=unc_t,
                cache_read_input_tokens=cread,
                cache_creation_ephemeral_5m=c5,
                cache_creation_ephemeral_1h=c1,
                completion_tokens=completion_tokens,
            )
            if cache_breakpoints is not None or cread > 0 or ctot > 0:
                cached_in = cread
                cached_create = ctot
        elif kind in ("groq", "kimi"):
            prompt_tokens = acc["prompt_tokens"]
            completion_tokens = acc["completion_tokens"]
            if kind == "kimi":
                kimi_cached = acc.get("cached_input_tokens", 0)
                cached_in = kimi_cached if kimi_cached else None
                cost_usd = compute_cost_usd(
                    provider,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    cached_input_tokens=cached_in,
                )
            else:
                cost_usd = compute_cost_usd(
                    provider, model, prompt_tokens, completion_tokens
                )
        request_id = usage_state.get("request_id")
        if request_id is not None:
            request_id = str(request_id)
        return prompt_tokens, completion_tokens, cost_usd, cached_in, cached_create, request_id

    if isinstance(exc, InstructorRetryException):
        request_id = _request_id_from_response(exc.last_completion)
        usage = exc.total_usage
        if usage is not None:
            if provider == "anthropic":
                unc_t, cread, ctot, c5, c1 = _anthropic_usage_accumulator_fields(usage)
                completion_tokens = _usage_int_attr(usage, "output_tokens")
                prompt_tokens = unc_t + cread + ctot
                cost_usd = compute_anthropic_cached_cost_usd(
                    model,
                    uncached_tail_input_tokens=unc_t,
                    cache_read_input_tokens=cread,
                    cache_creation_ephemeral_5m=c5,
                    cache_creation_ephemeral_1h=c1,
                    completion_tokens=completion_tokens,
                )
                if cache_breakpoints is not None or cread > 0 or ctot > 0:
                    cached_in = cread
                    cached_create = ctot
            else:
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                if provider == "kimi":
                    kimi_cached = _extract_kimi_cached_tokens(usage)
                    cached_in = kimi_cached if kimi_cached else None
                    cost_usd = compute_cost_usd(
                        provider,
                        model,
                        prompt_tokens,
                        completion_tokens,
                        cached_input_tokens=cached_in,
                    )
                else:
                    cost_usd = compute_cost_usd(
                        provider, model, prompt_tokens, completion_tokens
                    )

    return prompt_tokens, completion_tokens, cost_usd, cached_in, cached_create, request_id


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


def _get_kimi_client() -> AsyncOpenAI:
    global _kimi_client  # noqa: PLW0603
    if _kimi_client is None:
        settings = get_settings()
        _kimi_client = AsyncOpenAI(
            api_key=settings.moonshot_api_key,
            base_url="https://api.moonshot.ai/v1",
        )
    return _kimi_client


def _get_instructor_kimi() -> instructor.AsyncInstructor:
    global _instructor_kimi_client  # noqa: PLW0603
    if _instructor_kimi_client is None:
        _instructor_kimi_client = instructor.from_openai(_get_kimi_client())
    return _instructor_kimi_client


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
    cached_input_tokens: int | None = None,
    cache_creation_input_tokens: int | None = None,
) -> None:
    """Persist one row to llm_calls. Does NOT commit — caller controls tx."""
    call = LLMCall(
        experiment_id=experiment_id,
        phase=phase,
        cost_category=resolve_cost_category_from_phase(phase).value,
        provider=provider,
        model=model,
        prompt_name=prompt_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        request_id=request_id,
    )
    async with lock_for(db):
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

        elif provider == "kimi":
            client = _get_kimi_client()

            async def _do_kimi_call():
                # Kimi K2.6 constraints (verified 2026-05): thinking must be disabled (Instructor tool_choice incompat); when thinking off, temperature must be exactly 0.6.
                # Drop empty system: Moonshot rejects empty role=system; Anthropic accepts it (caching). Kimi-only behavior.
                msgs = []
                if system and system.strip():
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": user})
                return await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.6,
                    extra_body={"thinking": {"type": "disabled"}},
                    messages=msgs,
                )

            @retry_async()
            async def _call_kimi_with_retry():
                return await get_breaker("kimi").call(_do_kimi_call)

            response = await _call_kimi_with_retry()
            text = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            request_id = response.id
            kimi_cached_in = (
                _extract_kimi_cached_tokens(response.usage) if response.usage else 0
            )
            kimi_logged_cached_in = kimi_cached_in if kimi_cached_in else None

        else:
            raise ValueError(f"unknown provider: {provider}")

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if provider == "kimi":
            cost_usd = compute_cost_usd(
                provider,
                model,
                prompt_tokens,
                completion_tokens,
                cached_input_tokens=kimi_logged_cached_in,
            )
        else:
            cost_usd = compute_cost_usd(provider, model, prompt_tokens, completion_tokens)

        log_kwargs: dict[str, Any] = {}
        if provider == "kimi":
            # Moonshot Kimi does not surface cache-creation cost via API — creation
            # is billed on their dashboard only. This column stays NULL for Kimi calls.
            log_kwargs["cached_input_tokens"] = kimi_logged_cached_in
            log_kwargs["cache_creation_input_tokens"] = None

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
            **log_kwargs,
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


ImageMediaType = Literal["image/png", "image/jpeg", "image/webp"]


async def complete_with_image(
    db: AsyncSession,
    *,
    provider: ProviderName,
    model: str,
    prompt_name: str,
    system: str,
    user_text: str,
    image_base64: str,
    media_type: ImageMediaType,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    experiment_id: UUID | None = None,
    phase: str | None = None,
) -> LLMResult:
    """Vision completion for a single image (Anthropic or Kimi/Moonshot)."""
    if provider not in ("anthropic", "kimi"):
        raise ValueError("complete_with_image supports anthropic and kimi only")

    if not is_known_model(provider, model):
        _logger.warning(
            "llm vision call using unknown model",
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
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_base64,
                                    },
                                },
                                {"type": "text", "text": user_text},
                            ],
                        }
                    ],
                )

            @retry_async()
            async def _call_anthropic_with_retry():
                return await get_breaker("anthropic").call(_do_anthropic_call)

            response = await _call_anthropic_with_retry()
            text = response.content[0].text  # type: ignore[union-attr]
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            request_id: str | None = response.id
        else:
            client = _get_kimi_client()
            data_url = f"data:{media_type};base64,{image_base64}"
            user_content: list[dict[str, object]] = [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": user_text},
            ]
            msgs: list[dict[str, object]] = []
            if system and system.strip():
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": user_content})

            async def _do_kimi_call():
                return await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.6,
                    extra_body={"thinking": {"type": "disabled"}},
                    messages=msgs,  # type: ignore[arg-type]
                )

            @retry_async()
            async def _call_kimi_with_retry():
                return await get_breaker("kimi").call(_do_kimi_call)

            response = await _call_kimi_with_retry()
            text = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = (
                response.usage.completion_tokens if response.usage else 0
            )
            request_id = response.id
            kimi_cached_in = (
                _extract_kimi_cached_tokens(response.usage) if response.usage else 0
            )
            kimi_logged_cached_in = kimi_cached_in if kimi_cached_in else None

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if provider == "kimi":
            cost_usd = compute_cost_usd(
                provider,
                model,
                prompt_tokens,
                completion_tokens,
                cached_input_tokens=kimi_logged_cached_in,
            )
        else:
            cost_usd = compute_cost_usd(provider, model, prompt_tokens, completion_tokens)

        vision_log_kwargs: dict[str, Any] = {}
        if provider == "kimi":
            # Moonshot Kimi does not surface cache-creation cost via API — creation
            # is billed on their dashboard only. This column stays NULL for Kimi calls.
            vision_log_kwargs["cached_input_tokens"] = kimi_logged_cached_in
            vision_log_kwargs["cache_creation_input_tokens"] = None

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
            **vision_log_kwargs,
        )

        _logger.info(
            "llm vision call completed",
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
            _logger.warning("failed to log failed llm vision call", error=str(log_exc))

        _logger.warning(
            "llm vision call failed",
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
    max_retries: int = 3,
    experiment_id: UUID | None = None,
    phase: str | None = None,
    cache_breakpoints: list[CacheBreakpoint] | None = None,
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

    Anthropic prompt caching: optional ``cache_breakpoints`` attaches ephemeral
    cache markers per ADR 0014. User zones requiring two or three splits use
    ``USER_CACHE_ZONE_BOUNDARY`` embedded in ``user``. Empty zone blocks are
    dropped before send; their cache markers cascade to the previous non-empty
    block (see ``_anthropic_structured_system_and_messages``).
    """
    if not is_known_model(provider, model):
        _logger.warning(
            "llm call using unknown model",
            provider=provider,
            model=model,
        )

    started_at = time.perf_counter()

    logged_cached_in: int | None = None
    logged_cached_create: int | None = None
    usage_state: dict[str, Any] = {}

    try:
        if provider == "anthropic":
            iclient = _get_instructor_anthropic()

            sys_payload, msgs_payload = _anthropic_structured_system_and_messages(
                system=system,
                user=user,
                cache_breakpoints=cache_breakpoints,
            )

            # Accumulate usage across all Instructor attempts (schema retries are
            # billed by Anthropic on every attempt, not just the final success).
            _usage_acc: dict[str, int] = {
                "uncached_tail": 0,
                "cache_read": 0,
                "create_total": 0,
                "create_5m": 0,
                "create_1h": 0,
                "completion_tokens": 0,
                "attempts": 0,
            }
            usage_state["kind"] = "anthropic"
            usage_state["acc"] = _usage_acc

            def _accumulate_anthropic_usage(response: object) -> None:
                _usage_acc["attempts"] += 1
                rid = getattr(response, "id", None)
                if rid is not None:
                    usage_state["request_id"] = rid
                usage = getattr(response, "usage", None)
                if usage is None:
                    return
                unc, cr, ct, c5, c1 = _anthropic_usage_accumulator_fields(usage)
                _usage_acc["uncached_tail"] += unc
                _usage_acc["cache_read"] += cr
                _usage_acc["create_total"] += ct
                _usage_acc["create_5m"] += c5
                _usage_acc["create_1h"] += c1
                _usage_acc["completion_tokens"] += _usage_int_attr(usage, "output_tokens")

            call_hooks = Hooks()
            call_hooks.on("completion:response", _accumulate_anthropic_usage)

            async def _do_anthropic_structured():
                return await iclient.create_with_completion(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    max_retries=max_retries,
                    system=sys_payload,
                    messages=msgs_payload,
                    response_model=response_model,
                    hooks=call_hooks,
                )

            @retry_async()
            async def _call_anthropic_structured_with_retry():
                return await get_breaker("anthropic").call(_do_anthropic_structured)

            parsed, raw = await _call_anthropic_structured_with_retry()
            # Use accumulated totals so schema retries are included in cost.
            # Fall back to the final response when hooks never fired (e.g. mocks
            # in tests that don't simulate the Instructor callback loop).
            if _usage_acc["attempts"] > 0:
                unc_t = _usage_acc["uncached_tail"]
                cread = _usage_acc["cache_read"]
                c5 = _usage_acc["create_5m"]
                c1 = _usage_acc["create_1h"]
                ctot = _usage_acc["create_total"]
                completion_tokens = _usage_acc["completion_tokens"]
            else:
                usage = raw.usage
                unc_t, cread, ctot, c5, c1 = _anthropic_usage_accumulator_fields(usage)
                completion_tokens = _usage_int_attr(usage, "output_tokens")

            prompt_tokens = unc_t + cread + ctot
            cost_usd = compute_anthropic_cached_cost_usd(
                model,
                uncached_tail_input_tokens=unc_t,
                cache_read_input_tokens=cread,
                cache_creation_ephemeral_5m=c5,
                cache_creation_ephemeral_1h=c1,
                completion_tokens=completion_tokens,
            )

            if cache_breakpoints is not None or cread > 0 or ctot > 0:
                logged_cached_in = cread
                logged_cached_create = ctot

            request_id: str | None = raw.id
            usage_state["request_id"] = request_id
            instructor_attempts = _usage_acc["attempts"]

        elif provider == "groq":
            iclient = _get_instructor_groq()

            _usage_acc = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "attempts": 0,
            }
            usage_state["kind"] = "groq"
            usage_state["acc"] = _usage_acc

            def _accumulate_groq_usage(response: object) -> None:
                _usage_acc["attempts"] += 1
                rid = getattr(response, "id", None)
                if rid is not None:
                    usage_state["request_id"] = rid
                usage = getattr(response, "usage", None)
                if usage is not None:
                    _usage_acc["prompt_tokens"] += getattr(usage, "prompt_tokens", 0)
                    _usage_acc["completion_tokens"] += getattr(
                        usage, "completion_tokens", 0
                    )

            call_hooks = Hooks()
            call_hooks.on("completion:response", _accumulate_groq_usage)

            async def _do_groq_structured():
                return await iclient.create_with_completion(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    max_retries=max_retries,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_model=response_model,
                    hooks=call_hooks,
                )

            @retry_async()
            async def _call_groq_structured_with_retry():
                return await get_breaker("groq").call(_do_groq_structured)

            parsed, raw = await _call_groq_structured_with_retry()
            if _usage_acc["attempts"] > 0:
                prompt_tokens = _usage_acc["prompt_tokens"]
                completion_tokens = _usage_acc["completion_tokens"]
            else:
                prompt_tokens = raw.usage.prompt_tokens if raw.usage else 0
                completion_tokens = raw.usage.completion_tokens if raw.usage else 0
            cost_usd = compute_cost_usd(provider, model, prompt_tokens, completion_tokens)
            request_id = raw.id
            usage_state["request_id"] = request_id
            instructor_attempts = _usage_acc["attempts"]

        elif provider == "kimi":
            iclient = _get_instructor_kimi()

            _usage_acc = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cached_input_tokens": 0,
                "attempts": 0,
            }
            usage_state["kind"] = "kimi"
            usage_state["acc"] = _usage_acc

            def _accumulate_kimi_usage(response: object) -> None:
                _usage_acc["attempts"] += 1
                rid = getattr(response, "id", None)
                if rid is not None:
                    usage_state["request_id"] = rid
                usage = getattr(response, "usage", None)
                if usage is not None:
                    _usage_acc["prompt_tokens"] += getattr(usage, "prompt_tokens", 0)
                    _usage_acc["completion_tokens"] += getattr(
                        usage, "completion_tokens", 0
                    )
                    _usage_acc["cached_input_tokens"] += _extract_kimi_cached_tokens(
                        usage
                    )

            call_hooks = Hooks()
            call_hooks.on("completion:response", _accumulate_kimi_usage)

            async def _do_kimi_structured():
                # Kimi K2.6 constraints (verified 2026-05): thinking must be disabled (Instructor tool_choice incompat); when thinking off, temperature must be exactly 0.6.
                # Drop empty system: Moonshot rejects empty role=system; Anthropic accepts it (caching). Kimi-only behavior.
                msgs = []
                if system and system.strip():
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": user})
                return await iclient.create_with_completion(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.6,
                    extra_body={"thinking": {"type": "disabled"}},
                    max_retries=max_retries,
                    messages=msgs,
                    response_model=response_model,
                    hooks=call_hooks,
                )

            @retry_async()
            async def _call_kimi_structured_with_retry():
                return await get_breaker("kimi").call(_do_kimi_structured)

            parsed, raw = await _call_kimi_structured_with_retry()
            if _usage_acc["attempts"] > 0:
                prompt_tokens = _usage_acc["prompt_tokens"]
                completion_tokens = _usage_acc["completion_tokens"]
                kimi_cached_total = _usage_acc["cached_input_tokens"]
            else:
                prompt_tokens = raw.usage.prompt_tokens if raw.usage else 0
                completion_tokens = raw.usage.completion_tokens if raw.usage else 0
                kimi_cached_total = (
                    _extract_kimi_cached_tokens(raw.usage) if raw.usage else 0
                )
            logged_cached_in = kimi_cached_total if kimi_cached_total else None
            # Moonshot Kimi does not surface cache-creation cost via API — creation
            # is billed on their dashboard only. This column stays NULL for Kimi calls.
            logged_cached_create = None
            cost_usd = compute_cost_usd(
                provider,
                model,
                prompt_tokens,
                completion_tokens,
                cached_input_tokens=logged_cached_in,
            )
            request_id = raw.id
            usage_state["request_id"] = request_id
            instructor_attempts = _usage_acc["attempts"]

        else:
            raise ValueError(f"unknown provider: {provider}")

        latency_ms = int((time.perf_counter() - started_at) * 1000)

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
            cached_input_tokens=logged_cached_in,
            cache_creation_input_tokens=logged_cached_create,
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
            instructor_attempts=instructor_attempts,
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
        (
            fail_prompt_tokens,
            fail_completion_tokens,
            fail_cost_usd,
            fail_cached_in,
            fail_cached_create,
            fail_request_id,
        ) = _failure_metrics_for_structured_call(
            provider=provider,
            model=model,
            exc=exc,
            usage_state=usage_state,
            cache_breakpoints=cache_breakpoints,
        )
        try:
            await _log_llm_call(
                db,
                experiment_id=experiment_id,
                phase=phase,
                provider=provider,
                model=model,
                prompt_name=prompt_name,
                prompt_tokens=fail_prompt_tokens,
                completion_tokens=fail_completion_tokens,
                cost_usd=fail_cost_usd,
                latency_ms=latency_ms,
                request_id=fail_request_id,
                cached_input_tokens=fail_cached_in,
                cache_creation_input_tokens=fail_cached_create,
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
            prompt_tokens=fail_prompt_tokens,
            completion_tokens=fail_completion_tokens,
            cost_usd=str(fail_cost_usd),
        )
        raise
