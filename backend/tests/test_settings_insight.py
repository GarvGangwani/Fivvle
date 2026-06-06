"""Regression tests for insight LLM settings fields in Settings."""

from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.fixture
def _clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSIGHT_PROVIDER", raising=False)
    monkeypatch.delenv("INSIGHT_MODEL", raising=False)
    get_settings.cache_clear()


def test_settings_insight_provider_default_kimi(_clear_settings_cache: None) -> None:
    settings = get_settings()
    assert settings.insight_provider == "kimi"


def test_settings_insight_model_default_kimi_k26(_clear_settings_cache: None) -> None:
    settings = get_settings()
    assert settings.insight_model == "kimi-k2.6"


def test_settings_existing_synthesizer_fields_unchanged(_clear_settings_cache: None) -> None:
    settings = get_settings()
    assert settings.synthesizer_provider
    assert settings.synthesizer_model
