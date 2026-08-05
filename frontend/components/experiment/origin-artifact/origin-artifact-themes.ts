/** Fixed near-black — never themed (borders, shadow, body text, mono labels). */
export const ORIGIN_INK = "#0A0A0A";

export type OriginArtifactThemeTokens = {
  /** Very light card background tint. */
  tint: string;
  /** Solid mid-saturation block behind the eyebrow text. */
  highlight: string;
  /** More saturated accent for VIEW ORIGINAL and chip thumbnail borders. */
  link: string;
};

/**
 * Artifact fills, derived from the accent in scope rather than a frozen palette,
 * so the artifact follows the experiment's canvas theme like the rest of the
 * canvas. `color-mix` is substituted on the element, which is why these resolve
 * against the canvas accent and not the :root platform purple.
 */
export const ORIGIN_ACCENT_TOKENS: OriginArtifactThemeTokens = {
  tint: "color-mix(in srgb, var(--fv-accent) 9%, #ffffff)",
  highlight: "color-mix(in srgb, var(--fv-accent) 50%, #ffffff)",
  link: "color-mix(in srgb, var(--fv-accent) 88%, #000000)",
};
