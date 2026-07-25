/**
 * Design-tab helpers for Launch — page_json deep merges only.
 * Does not touch copy_json or section sync (that stays in landing-copy-sync).
 */

import type { PageJson } from "@/lib/types";
import type { ColorMode, UserColorPalette } from "@/lib/color-palettes";
import { inferColorModeFromPalette } from "@/lib/color-palettes";
import type { PageBranding } from "@/lib/branding";

const HEX_RE = /^#([0-9a-fA-F]{6})$/;

export function isValidHex(value: string): boolean {
  return HEX_RE.test(value.trim());
}

/** Normalize user hex input to #rrggbb or null if invalid. */
export function normalizeHex(value: string): string | null {
  const raw = value.trim();
  const withHash = raw.startsWith("#") ? raw : `#${raw}`;
  if (!isValidHex(withHash)) return null;
  return withHash.toLowerCase();
}

/**
 * Apply palette (+ optional mode) onto page_json, mirroring theme_* colors
 * for consumers that still read page.theme.
 */
export function applyColorPaletteToPage(
  page: PageJson,
  palette: UserColorPalette,
  colorMode?: ColorMode,
): PageJson {
  const mode = colorMode ?? inferColorModeFromPalette(palette);
  return {
    ...page,
    color_mode: mode,
    color_palette: {
      preset: palette.preset,
      accent: palette.accent,
      background: palette.background,
      foreground: palette.foreground,
    },
    theme: {
      ...(page.theme ?? {}),
      accent_color: palette.accent,
      background_color: palette.background,
      text_color: palette.foreground,
      primary_color: page.theme?.primary_color ?? palette.accent,
    },
  };
}

/** Flip color_mode only — leave palette preset/hexes unchanged. */
export function applyColorModeToPage(
  page: PageJson,
  colorMode: ColorMode,
): PageJson {
  return { ...page, color_mode: colorMode };
}

/** Shallow-merge branding onto page_json. */
export function applyBrandingPatch(
  page: PageJson,
  branding: Partial<PageBranding>,
  projectName: string,
): PageJson {
  return {
    ...page,
    branding: {
      ...(page.branding as PageBranding | undefined),
      ...branding,
      logo_alt: projectName,
    },
  };
}

export type PaletteHistoryEntry = {
  color_mode?: ColorMode;
  color_palette: UserColorPalette;
};

export const PALETTE_HISTORY_LIMIT = 20;
