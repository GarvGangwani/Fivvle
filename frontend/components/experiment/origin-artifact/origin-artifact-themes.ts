/** Origin Artifact palette — classified once at capture, then frozen. */
export type OriginArtifactTheme = "violet" | "pink" | "green" | "orange";

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

export const ORIGIN_THEME_TOKENS: Record<
  OriginArtifactTheme,
  OriginArtifactThemeTokens
> = {
  violet: {
    tint: "#F1ECFE",
    highlight: "#B197FC",
    link: "#6D28D9",
  },
  pink: {
    tint: "#FDEAF2",
    highlight: "#FF80B5",
    link: "#FF4D9D",
  },
  green: {
    tint: "#E9F7EE",
    highlight: "#6EE7A8",
    link: "#0F8A54",
  },
  orange: {
    tint: "#FEEFE3",
    highlight: "#FDBA74",
    link: "#DD5B12",
  },
};

export const ORIGIN_ARTIFACT_THEMES: OriginArtifactTheme[] = [
  "violet",
  "pink",
  "green",
  "orange",
];

export function isOriginArtifactTheme(
  value: string | null | undefined,
): value is OriginArtifactTheme {
  return (
    value === "violet" ||
    value === "pink" ||
    value === "green" ||
    value === "orange"
  );
}
