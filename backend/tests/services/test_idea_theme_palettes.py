"""Guards on the curated canvas palettes.

Palettes are shipped colors, not generated ones — these tests exist so a future
edit cannot introduce an accent that makes canvas labels illegible.
"""

from __future__ import annotations

import re

import pytest

from app.services.idea_theme_palettes import (
    DEFAULT_THEME_PALETTE,
    THEME_PALETTE_NAMES,
    THEME_PALETTES,
    get_palette,
    is_theme_palette,
)

_MUTED_RE = re.compile(r"^rgba\(\d{1,3}, \d{1,3}, \d{1,3}, 0\.\d+\)$")


def _channel(value: int) -> float:
    srgb = value / 255
    return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(fg: str, bg: str) -> float:
    light, dark = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_default_palette_is_founder_purple() -> None:
    assert DEFAULT_THEME_PALETTE == "founder-purple"
    assert THEME_PALETTES[DEFAULT_THEME_PALETTE].accent == "#7C3AED"


def test_eight_palettes_with_unique_accents() -> None:
    assert len(THEME_PALETTE_NAMES) == 8
    accents = [p.accent for p in THEME_PALETTES.values()]
    assert len(set(accents)) == len(accents)


@pytest.mark.parametrize("name", THEME_PALETTE_NAMES)
def test_palette_foreground_meets_aa_contrast(name: str) -> None:
    palette = THEME_PALETTES[name]
    assert _contrast(palette.accent_fg, palette.accent) >= 4.5


@pytest.mark.parametrize("name", THEME_PALETTE_NAMES)
def test_palette_hover_is_darker_than_accent(name: str) -> None:
    palette = THEME_PALETTES[name]
    assert _luminance(palette.accent_hover) < _luminance(palette.accent)


@pytest.mark.parametrize("name", THEME_PALETTE_NAMES)
def test_palette_muted_is_translucent(name: str) -> None:
    """Muted must stay translucent so one value works in light and dark mode."""
    assert _MUTED_RE.match(THEME_PALETTES[name].accent_muted)


@pytest.mark.parametrize("name", THEME_PALETTE_NAMES)
def test_palette_metadata_present(name: str) -> None:
    palette = THEME_PALETTES[name]
    assert palette.display_name.strip()
    assert palette.domain.strip()
    assert palette.preview == palette.accent
    assert palette.accent_ring == palette.accent


def test_validation_helpers() -> None:
    assert is_theme_palette("emerald") is True
    assert is_theme_palette("chartreuse") is False
    assert is_theme_palette(None) is False
    assert get_palette("emerald").name == "emerald"
    assert get_palette("chartreuse").name == DEFAULT_THEME_PALETTE
    assert get_palette(None).name == DEFAULT_THEME_PALETTE
