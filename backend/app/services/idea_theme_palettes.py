"""Curated per-experiment accent palettes.

The canvas reads one accent token set per experiment (see the frontend
`[data-canvas-accent-scope]` rules). Palettes are designer-picked rather than
LLM-generated: the classifier only chooses a NAME from this set.

Every accent carries at least 4.5:1 contrast against white, so `accent_fg`
is white throughout and small uppercase labels on a filled accent stay legible.
`accent_muted` is translucent (12% of the accent) so the same value works on the
light canvas and in dark mode, matching how the CSS scope derives it.

Values are mirrored in `frontend/lib/theme-palettes.ts` — change both together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

ThemePaletteName = Literal[
    "founder-purple",
    "rose",
    "emerald",
    "amber",
    "sky",
    "crimson",
    "teal",
    "indigo",
]

DEFAULT_THEME_PALETTE: ThemePaletteName = "founder-purple"


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """One accent token set, mapped to an idea domain."""

    name: ThemePaletteName
    display_name: str
    domain: str
    accent: str
    accent_hover: str
    accent_muted: str
    accent_fg: str

    @property
    def accent_ring(self) -> str:
        """Focus ring always tracks the solid accent."""
        return self.accent

    @property
    def preview(self) -> str:
        """Swatch color shown in the consent popup and the canvas control."""
        return self.accent


_PALETTE_LIST: tuple[ThemePalette, ...] = (
    ThemePalette(
        name="founder-purple",
        display_name="Founder Purple",
        domain="Default — anything else, unclear, or multi-domain",
        accent="#7C3AED",
        accent_hover="#6D28D9",
        accent_muted="rgba(124, 58, 237, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="rose",
        display_name="Rose",
        domain="Dating, social, relationships, community",
        accent="#BE185D",
        accent_hover="#9D174D",
        accent_muted="rgba(190, 24, 93, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="emerald",
        display_name="Emerald",
        domain="Fintech, payments, investing, banking, accounting",
        accent="#047857",
        accent_hover="#065F46",
        accent_muted="rgba(4, 120, 87, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="amber",
        display_name="Amber",
        domain="Food, delivery, restaurants, hospitality, groceries",
        accent="#B45309",
        accent_hover="#92400E",
        accent_muted="rgba(180, 83, 9, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="sky",
        display_name="Sky",
        domain="Productivity, SaaS, developer and business tools",
        accent="#0369A1",
        accent_hover="#075985",
        accent_muted="rgba(3, 105, 161, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="crimson",
        display_name="Crimson",
        domain="Gaming, entertainment, streaming, sports",
        accent="#B91C1C",
        accent_hover="#991B1B",
        accent_muted="rgba(185, 28, 28, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="teal",
        display_name="Teal",
        domain="Health, wellness, fitness, medical",
        accent="#0F766E",
        accent_hover="#115E59",
        accent_muted="rgba(15, 118, 110, 0.12)",
        accent_fg="#FFFFFF",
    ),
    ThemePalette(
        name="indigo",
        display_name="Indigo",
        domain="Education, learning, research, courses",
        accent="#4338CA",
        accent_hover="#3730A3",
        accent_muted="rgba(67, 56, 202, 0.12)",
        accent_fg="#FFFFFF",
    ),
)

THEME_PALETTES: dict[str, ThemePalette] = {p.name: p for p in _PALETTE_LIST}

THEME_PALETTE_NAMES: tuple[str, ...] = tuple(THEME_PALETTES)

# Guard against the Literal and the table drifting apart.
assert set(get_args(ThemePaletteName)) == set(THEME_PALETTES), (
    "ThemePaletteName does not match THEME_PALETTES"
)
assert DEFAULT_THEME_PALETTE in THEME_PALETTES


def is_theme_palette(name: str | None) -> bool:
    """True when `name` is one of the curated palettes."""
    return name in THEME_PALETTES


def get_palette(name: str | None) -> ThemePalette:
    """Palette for `name`, falling back to the default for unknown values."""
    return THEME_PALETTES.get(name or "", THEME_PALETTES[DEFAULT_THEME_PALETTE])
