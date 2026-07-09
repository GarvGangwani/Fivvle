"""Experiment category tag generation and validation."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from instructor.core.exceptions import InstructorRetryException
from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.config import get_settings
from app.db.models.experiment import Experiment
from app.llm.prompts.tag_generator import (
    PROMPT_NAME,
    TAG_GENERATOR_SYSTEM_PROMPT,
    TAG_VOCABULARY,
    build_tag_generator_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.refinement import RefinedIdea
from app.schemas.tags import TagGeneratorOutput

_logger = get_logger(__name__)

_TAG_VOCABULARY_SET = frozenset(TAG_VOCABULARY)
_MAX_TAG_TOKENS = 256

# Kimi K2.6 per ADR 0018 — ~200–400 tokens/call ≈ $0.0001–0.0003 (not Sonnet).
_TAG_PROVIDER: llm_client.ProviderName = "kimi"
_TAG_MODEL = "kimi-k2.6"


def _is_json_shape_error(exc: InstructorRetryException) -> bool:
    """True if Instructor retries were exhausted due to malformed JSON output."""
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "json_invalid",
            "invalid json",
            "jsondecodeerror",
            "key must be a string",
            "expecting value",
            "expecting property name",
        )
    )


def build_refined_idea_text(refined: RefinedIdea) -> str:
    """Concatenate key refined-idea fields for tag classification."""
    parts = [
        refined.refined_one_liner,
        refined.target_audience,
        refined.value_proposition,
        refined.headline,
    ]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def validate_tags(tags: list[str]) -> list[str]:
    """Normalize and validate tags against vocabulary. Raises ValueError if invalid."""
    normalized: list[str] = []
    for tag in tags:
        candidate = tag.strip().upper()
        if candidate not in _TAG_VOCABULARY_SET:
            raise ValueError(f"Unknown tag: {tag}")
        if candidate not in normalized:
            normalized.append(candidate)
    if len(normalized) > 3:
        raise ValueError("At most 3 tags allowed")
    if "B2B" in normalized and "B2C" in normalized:
        raise ValueError("B2B and B2C cannot be combined — use B2B2C")
    return normalized


async def generate_tags(
    db: AsyncSession,
    refined_idea_text: str,
    experiment_id: UUID | None = None,
) -> list[str]:
    """Generate 2–3 category tags for an experiment from its refined idea.

    Returns empty list on failure — caller decides UI fallback.
    Never raises to the caller. Cost tracked as phase=refinement.
    Primary provider: Kimi K2.6; Anthropic fallback only on JSON-shape errors.
    """
    text = refined_idea_text.strip()
    if not text:
        return []

    settings = get_settings()

    async def _complete(
        provider: llm_client.ProviderName,
        model: str,
    ) -> tuple[TagGeneratorOutput, llm_client.LLMResult]:
        return await llm_client.complete_structured(
            db,
            provider=provider,
            model=model,
            prompt_name=PROMPT_NAME,
            system=TAG_GENERATOR_SYSTEM_PROMPT,
            user=build_tag_generator_user_prompt(text),
            response_model=TagGeneratorOutput,
            max_tokens=_MAX_TAG_TOKENS,
            temperature=0.2,
            experiment_id=experiment_id,
            phase="refinement",
        )

    try:
        try:
            parsed, meta = await _complete(_TAG_PROVIDER, _TAG_MODEL)
        except InstructorRetryException as exc:
            should_fallback = (
                settings.synthesizer_fallback_enabled
                and _is_json_shape_error(exc)
            )
            if not should_fallback:
                raise
            _logger.warning(
                "tag generation kimi failed with JSON error, falling back to Anthropic",
                experiment_id=str(experiment_id) if experiment_id else None,
                error_type=type(exc).__name__,
            )
            parsed, meta = await _complete(
                cast(
                    llm_client.ProviderName,
                    settings.synthesizer_fallback_provider,
                ),
                settings.synthesizer_fallback_model,
            )

        validated = validate_tags(parsed.tags)
        if len(validated) < 2:
            _logger.warning(
                "tag generation returned fewer than 2 valid tags",
                experiment_id=str(experiment_id) if experiment_id else None,
                token_count=meta.total_tokens,
            )
            return []
        _logger.info(
            "tag generation completed",
            experiment_id=str(experiment_id) if experiment_id else None,
            tag_count=len(validated),
            token_count=meta.total_tokens,
        )
        return validated[:3]
    except Exception:
        _logger.warning(
            "tag generation failed — returning empty list",
            experiment_id=str(experiment_id) if experiment_id else None,
            exc_info=True,
        )
        return []


async def persist_experiment_tags(
    db: AsyncSession,
    experiment: Experiment,
    refined: RefinedIdea,
) -> None:
    """Generate and persist tags after refinement. Failures leave tags unchanged or []."""
    experiment.tags = await generate_tags(
        db,
        build_refined_idea_text(refined),
        experiment.id,
    )
