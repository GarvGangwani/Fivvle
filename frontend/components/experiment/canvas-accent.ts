import type { CSSProperties } from "react";

/**
 * Per-experiment canvas accent override.
 * Set on the experiment canvas wrapper only — dashboard / nav / list stay on
 * :root Fivvle purple. PR2 will pass curated theme accents from idea_theme.
 */
export type CanvasAccentOverride = {
  /** Solid accent (maps to --fv-accent). Required. */
  accent: string;
  /** Optional explicit companions; otherwise derived from accent on the wrapper. */
  hover?: string;
  muted?: string;
  fg?: string;
  brandSoft?: string;
  brandDeep?: string;
  gradientEnd?: string;
};

export const CANVAS_ACCENT_SCOPE_ATTR = "data-canvas-accent-scope";

/**
 * Portal target that inherits the experiment canvas accent override.
 * Falls back to document.body when not on an experiment page.
 * Client-only — call it after mount.
 */
export function getCanvasAccentPortalTarget(): HTMLElement {
  const scope = document.querySelector<HTMLElement>(
    `[${CANVAS_ACCENT_SCOPE_ATTR}]`,
  );
  return scope ?? document.body;
}

/**
 * CSS custom-property overrides for a canvas-scoped wrapper.
 *
 * Only `--fv-accent` (plus any explicitly supplied companions) is set inline.
 * Every derived token is re-declared per theme by the `[data-canvas-accent-scope]`
 * rules in globals.css, which is what makes hovers, soft fills, tinted panels and
 * shadows follow the canvas accent instead of the :root purple.
 */
export function canvasAccentCssVars(
  override: CanvasAccentOverride | string | null | undefined,
): CSSProperties | undefined {
  if (override == null || override === "") return undefined;

  const tokens: CanvasAccentOverride =
    typeof override === "string" ? { accent: override } : override;

  if (!tokens.accent.trim()) return undefined;

  const vars: Record<string, string> = { "--fv-accent": tokens.accent.trim() };

  if (tokens.hover) vars["--fv-accent-hover"] = tokens.hover;
  if (tokens.muted) vars["--fv-accent-muted"] = tokens.muted;
  if (tokens.gradientEnd) vars["--fv-accent-gradient-end"] = tokens.gradientEnd;
  if (tokens.brandSoft) vars["--fv-brand-soft"] = tokens.brandSoft;
  if (tokens.brandDeep) vars["--fv-brand-deep"] = tokens.brandDeep;
  if (tokens.fg) {
    vars["--fv-accent-fg"] = tokens.fg;
    vars["--fv-on-accent"] = tokens.fg;
  }

  return vars as CSSProperties;
}

/**
 * Mirrors the canvas accent onto <html> for the lifetime of the canvas.
 *
 * The canvas-route chrome (side rail, its active-phase pill) renders in the
 * shell, above the canvas wrapper, so it cannot inherit the wrapper scope. Since
 * that rail only exists on an experiment page, mirroring here themes it too, and
 * removing the property on unmount returns dashboard chrome to platform purple.
 * Setting `--fv-accent` on <html> also recomputes the :root-derived companions,
 * because substitution reads the cascaded value on the element.
 *
 * @returns cleanup that restores the platform accent.
 */
export function applyRouteAccent(
  override: CanvasAccentOverride | string | null | undefined,
): () => void {
  if (typeof document === "undefined") return () => {};

  const vars = canvasAccentCssVars(override);
  if (!vars) return () => {};

  const root = document.documentElement;
  const entries = Object.entries(vars as Record<string, string>);
  for (const [prop, value] of entries) root.style.setProperty(prop, value);

  return () => {
    for (const [prop] of entries) root.style.removeProperty(prop);
  };
}
