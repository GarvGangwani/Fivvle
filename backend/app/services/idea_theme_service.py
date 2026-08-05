"""One-shot classification of an idea into an Origin Artifact theme."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import app.llm.client as llm_client
from app.llm.prompts.idea_theme import (
    IDEA_THEME_SYSTEM_PROMPT,
    IDEA_THEME_VALUES,
    PROMPT_NAME,
    build_idea_theme_user_prompt,
)
from app.logging_config import get_logger
from app.schemas.idea_capture import IdeaTheme, IdeaThemeOutput

_logger = get_logger(__name__)

_MAX_THEME_TOKENS = 64
_DEFAULT_THEME: IdeaTheme = "violet"

# Cheap classifier — same family as tag_service (ADR 0018).
_THEME_PROVIDER: llm_client.ProviderName = "kimi"
_THEME_MODEL = "kimi-k2.6"

_THEME_SET = frozenset(IDEA_THEME_VALUES)


def _normalize_theme(raw: str) -> IdeaTheme | None:
    candidate = raw.strip().lower()
    if candidate in _THEME_SET:
        return cast(IdeaTheme, candidate)
    return None


async def classify_idea_theme(
    db: AsyncSession,
    idea_text: str,
    *,
    experiment_id: UUID | None = None,
) -> IdeaTheme:
    """Map idea domain → Origin Artifact palette.

    Soft-fail: any error or empty input → violet. Never raises.
    Logs LLMCall with phase=idea_theme / prompt_name=idea_theme_v1.
    """
    text = idea_text.strip()
    if not text:
        return _DEFAULT_THEME

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
        theme = _normalize_theme(parsed.theme)
        if theme is None:
            _logger.warning(
                "idea_theme_invalid_value",
                experiment_id=str(experiment_id) if experiment_id else None,
            )
            return _DEFAULT_THEME
        return theme
    except Exception as exc:
        _logger.warning(
            "idea_theme_classification_failed",
            experiment_id=str(experiment_id) if experiment_id else None,
            error_type=type(exc).__name__,
        )
        return _DEFAULT_THEME
