"""One-shot classification of an idea into a curated canvas palette."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.llm.prompts.idea_theme import (
    IDEA_THEME_SYSTEM_PROMPT,
    PROMPT_NAME,
    build_idea_theme_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.idea_capture import IdeaThemeOutput
from app.services.idea_theme_palettes import (
    DEFAULT_THEME_PALETTE,
    THEME_PALETTES,
    ThemePaletteName,
)

_logger = get_logger(__name__)

_MAX_THEME_TOKENS = 64

# Cheap classifier — same family as tag_service (ADR 0018).
_THEME_PROVIDER: llm_client.ProviderName = "kimi"
_THEME_MODEL = "kimi-k2.6"


def _normalize_palette(raw: str) -> ThemePaletteName | None:
    candidate = raw.strip().lower()
    if candidate in THEME_PALETTES:
        return cast(ThemePaletteName, candidate)
    return None


async def classify_theme_palette(
    db: AsyncSession,
    idea_text: str,
    *,
    experiment_id: UUID | None = None,
) -> ThemePaletteName:
    """Map idea domain → curated palette name.

    Soft-fail: any error or empty input → founder-purple. Never raises.
    Logs LLMCall with phase=idea_theme / prompt_name=idea_theme_v2.
    """
    text = idea_text.strip()
    if not text:
        return DEFAULT_THEME_PALETTE

    try:
        parsed, _meta = await llm_client.complete_structured(
            db,
            provider=_THEME_PROVIDER,
            model=_THEME_MODEL,
            prompt_name=PROMPT_NAME,
            system=IDEA_THEME_SYSTEM_PROMPT,
            user=build_idea_theme_user_prompt(text),
            response_model=IdeaThemeOutput,
            max_tokens=_MAX_THEME_TOKENS,
            temperature=0.0,
            experiment_id=experiment_id,
            phase="idea_theme",
        )
        palette = _normalize_palette(parsed.theme)
        if palette is None:
            _logger.warning(
                "idea_theme_invalid_value",
                experiment_id=str(experiment_id) if experiment_id else None,
            )
            return DEFAULT_THEME_PALETTE
        return palette
    except Exception as exc:
        _logger.warning(
            "idea_theme_classification_failed",
            experiment_id=str(experiment_id) if experiment_id else None,
            error_type=type(exc).__name__,
        )
        return DEFAULT_THEME_PALETTE
