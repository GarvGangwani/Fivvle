import type { LandingPageV2Spec } from "@/lib/landing-page-v2-types";

export interface RuntimeThemeTokens {
  "--lp-accent": string;
  "--lp-accent-soft": string;
  "--lp-accent-contrast": string;
  "--lp-bg": string;
  "--lp-surface": string;
  "--lp-text": string;
  "--lp-text-muted": string;
  "--lp-border": string;
  "--lp-font-display": string;
  "--lp-font-body": string;
  "--lp-radius": string;
  "--lp-card-shadow": string;
  "--lp-card-border": string;
  "--lp-card-bg": string;
  "--lp-cta-weight": string;
}

const ACCENTS: Record<
  LandingPageV2Spec["design_tokens"]["accent_family"],
  { primary: string; soft: string; contrast: string }
> = {
  indigo: { primary: "#4f46e5", soft: "#eef2ff", contrast: "#ffffff" },
  emerald: { primary: "#059669", soft: "#ecfdf5", contrast: "#ffffff" },
  amber: { primary: "#d97706", soft: "#fffbeb", contrast: "#1c1917" },
  rose: { primary: "#e11d48", soft: "#fff1f2", contrast: "#ffffff" },
  slate: { primary: "#475569", soft: "#f1f5f9", contrast: "#ffffff" },
  cyan: { primary: "#0891b2", soft: "#ecfeff", contrast: "#ffffff" },
};

const TYPOGRAPHY: Record<string, { display: string; body: string; radius: string }> = {
  bold_editorial: {
    display: "Georgia, 'Times New Roman', serif",
    body: "Inter, system-ui, sans-serif",
    radius: "0.25rem",
  },
  minimal_sans: {
    display: "Inter, system-ui, sans-serif",
    body: "Inter, system-ui, sans-serif",
    radius: "0.125rem",
  },
  technical_mono: {
    display: "'JetBrains Mono', ui-monospace, monospace",
    body: "Inter, system-ui, sans-serif",
    radius: "0.375rem",
  },
  friendly_rounded: {
    display: "Inter, system-ui, sans-serif",
    body: "Inter, system-ui, sans-serif",
    radius: "1rem",
  },
};

function cardTokens(
  style: LandingPageV2Spec["design_tokens"]["card_style"],
  dark: boolean,
) {
  switch (style) {
    case "elevated":
      return {
        shadow: dark ? "0 16px 48px rgba(0,0,0,0.4)" : "0 16px 48px rgba(15,23,42,0.1)",
        border: "transparent",
        bg: dark ? "#1e293b" : "#ffffff",
      };
    case "outline":
      return { shadow: "none", border: dark ? "#334155" : "#e2e8f0", bg: "transparent" };
    case "glass":
      return {
        shadow: "none",
        border: dark ? "rgba(255,255,255,0.1)" : "rgba(15,23,42,0.08)",
        bg: dark ? "rgba(30,41,59,0.75)" : "rgba(255,255,255,0.8)",
      };
    default:
      return {
        shadow: "none",
        border: dark ? "#334155" : "#f1f5f9",
        bg: dark ? "#0f172a" : "#f8fafc",
      };
  }
}

export function buildRuntimeThemeStyle(spec: LandingPageV2Spec): RuntimeThemeTokens {
  const global = spec.pipeline.creative_director.global_direction;
  const dt = spec.design_tokens;
  const accent = ACCENTS[dt.accent_family];
  const typo = TYPOGRAPHY[global.typography] ?? TYPOGRAPHY.minimal_sans;
  const dark = dt.color_mode === "dark";
  const card = cardTokens(dt.card_style, dark);

  return {
    "--lp-accent": accent.primary,
    "--lp-accent-soft": dark ? "#1e1b4b" : accent.soft,
    "--lp-accent-contrast": accent.contrast,
    "--lp-bg": dark ? "#020617" : "#ffffff",
    "--lp-surface": dark ? "#0f172a" : "#f8fafc",
    "--lp-text": dark ? "#f8fafc" : "#0f172a",
    "--lp-text-muted": dark ? "#94a3b8" : "#64748b",
    "--lp-border": dark ? "#334155" : "#e2e8f0",
    "--lp-font-display": typo.display,
    "--lp-font-body": typo.body,
    "--lp-radius": typo.radius,
    "--lp-card-shadow": card.shadow,
    "--lp-card-border": card.border,
    "--lp-card-bg": card.bg,
    "--lp-cta-weight": dt.cta_emphasis === "bold" ? "700" : dt.cta_emphasis === "subtle" ? "500" : "600",
  };
}
