import type { CanvasAccentOverride } from "@/components/experiment/canvas-accent";

/**
 * Curated per-experiment canvas palettes.
 *
 * Mirrors `backend/app/services/idea_theme_palettes.py` — the backend owns
 * validation and classification, this map owns rendering. Change both together.
 *
 * `muted` stays translucent so a single value reads correctly on the light canvas
 * and in dark mode, matching how the CSS scope derives it.
 */
export type ThemePaletteName =
  | "founder-purple"
  | "rose"
  | "emerald"
  | "amber"
  | "sky"
  | "crimson"
  | "teal"
  | "indigo";

export type ThemePalette = {
  name: ThemePaletteName;
  displayName: string;
  domain: string;
  accent: string;
  hover: string;
  muted: string;
  fg: string;
};

export const DEFAULT_PALETTE_NAME: ThemePaletteName = "founder-purple";

export const THEME_PALETTES: readonly ThemePalette[] = [
  {
    name: "founder-purple",
    displayName: "Founder Purple",
    domain: "Default",
    accent: "#7C3AED",
    hover: "#6D28D9",
    muted: "rgba(124, 58, 237, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "rose",
    displayName: "Rose",
    domain: "Dating, social, community",
    accent: "#BE185D",
    hover: "#9D174D",
    muted: "rgba(190, 24, 93, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "emerald",
    displayName: "Emerald",
    domain: "Fintech, payments, investing",
    accent: "#047857",
    hover: "#065F46",
    muted: "rgba(4, 120, 87, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "amber",
    displayName: "Amber",
    domain: "Food, delivery, hospitality",
    accent: "#B45309",
    hover: "#92400E",
    muted: "rgba(180, 83, 9, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "sky",
    displayName: "Sky",
    domain: "Productivity, SaaS, tools",
    accent: "#0369A1",
    hover: "#075985",
    muted: "rgba(3, 105, 161, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "crimson",
    displayName: "Crimson",
    domain: "Gaming, entertainment, sports",
    accent: "#B91C1C",
    hover: "#991B1B",
    muted: "rgba(185, 28, 28, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "teal",
    displayName: "Teal",
    domain: "Health, wellness, fitness",
    accent: "#0F766E",
    hover: "#115E59",
    muted: "rgba(15, 118, 110, 0.12)",
    fg: "#FFFFFF",
  },
  {
    name: "indigo",
    displayName: "Indigo",
    domain: "Education, learning, research",
    accent: "#4338CA",
    hover: "#3730A3",
    muted: "rgba(67, 56, 202, 0.12)",
    fg: "#FFFFFF",
  },
] as const;

const PALETTE_BY_NAME = new Map<string, ThemePalette>(
  THEME_PALETTES.map((p) => [p.name, p]),
);

export function isThemePaletteName(
  value: string | null | undefined,
): value is ThemePaletteName {
  return value != null && PALETTE_BY_NAME.has(value);
}

export function getThemePalette(
  name: string | null | undefined,
): ThemePalette {
  return (
    PALETTE_BY_NAME.get(name ?? "") ??
    PALETTE_BY_NAME.get(DEFAULT_PALETTE_NAME)!
  );
}

/**
 * Accent token overrides for the canvas wrapper.
 * Returns null for the default palette so the canvas simply inherits :root.
 */
export function paletteAccentOverride(
  name: string | null | undefined,
): CanvasAccentOverride | null {
  if (!isThemePaletteName(name) || name === DEFAULT_PALETTE_NAME) return null;

  const palette = getThemePalette(name);
  return {
    accent: palette.accent,
    hover: palette.hover,
    muted: palette.muted,
    fg: palette.fg,
  };
}
