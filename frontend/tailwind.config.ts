import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class", "[data-theme='dark']"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand — routed through accent tokens
        "brand-primary": "var(--fv-accent)",
        "brand-primary-deep": "var(--fv-brand-deep)",
        "brand-primary-soft": "var(--fv-brand-soft)",
        "brutalist-yellow": "var(--fv-yellow)",

        // Surfaces
        "canvas-bg": "var(--fv-canvas-bg)",
        "surface-card": "var(--fv-surface-card)",
        "surface-muted": "var(--fv-surface-muted)",
        "surface-elevated": "var(--fv-surface-elevated-brutal)",

        // Text
        "ink-primary": "var(--fv-ink-primary)",
        "ink-secondary": "var(--fv-ink-secondary)",
        "ink-tertiary": "var(--fv-ink-tertiary)",
        "ink-inverse": "var(--fv-ink-inverse)",

        // Structural
        "border-master": "var(--fv-border-master)",
        "border-subtle": "var(--fv-border-subtle)",

        // Status
        "status-active": "var(--fv-accent)",
        "status-staging": "var(--fv-ink-tertiary)",
        "status-success": "#16A34A",
        "status-critical": "#BA1A1A",
        "status-warning": "var(--fv-yellow)",

        // Legacy fv-* tokens — CSS variables used by unmigrated screens
        fv: {
          bg: "var(--fv-bg)",
          surface: "var(--fv-surface)",
          text: "var(--fv-text)",
          "text-muted": "var(--fv-text-muted)",
          "text-soft": "var(--fv-text-soft)",
          "text-dim": "var(--fv-text-dim)",
          inactive: "var(--fv-inactive)",
          accent: "var(--fv-accent)",
          "accent-hover": "var(--fv-accent-hover)",
          success: "var(--fv-success)",
          warning: "var(--fv-warning)",
          danger: "var(--fv-danger)",
          "on-accent": "var(--fv-on-accent)",
          border: "var(--fv-border)",
        },

        // TODO: remove after screen migrations complete — Material-style aliases
        background: "var(--background)",
        foreground: "var(--foreground)",
        "on-surface": "var(--fv-text)",
        "on-surface-variant": "var(--fv-text-muted)",
        "surface-container-low": "var(--fv-surface-2)",
        "surface-container": "var(--fv-surface)",
        "surface-container-high": "var(--fv-surface-elevated)",
      },

      borderRadius: {
        DEFAULT: "var(--fv-radius-md)",
        none: "0px",
        xs: "var(--fv-radius-xs)",
        sm: "var(--fv-radius-sm)",
        md: "var(--fv-radius-md)",
        lg: "var(--fv-radius-lg)",
        xl: "var(--fv-radius-xl)",
        "2xl": "var(--fv-radius-xl)",
        pill: "var(--fv-radius-pill)",
        full: "9999px",
      },

      borderWidth: {
        DEFAULT: "2px",
        master: "2px",
        thick: "3px",
      },

      boxShadow: {
        "brutal-sm": "3px 3px 0 0 var(--fv-shadow-color)",
        "brutal-md": "4px 4px 0 0 var(--fv-shadow-color)",
        "brutal-lg": "6px 6px 0 0 var(--fv-shadow-color)",
        "brutal-xl": "8px 8px 0 0 var(--fv-shadow-color)",
        "brutal-primary": "4px 4px 0 0 var(--fv-shadow-color-primary)",
      },

      spacing: {
        gutter: "24px",
        "section-gap": "64px",
        "card-padding": "16px",
        "canvas-grid": "40px",
        "toolbar-height": "56px",
      },

      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        display: ["Geist", "system-ui", "sans-serif"],
        headline: ["Geist", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "var(--font-dm-mono)", "ui-monospace", "monospace"],
      },

      fontSize: {
        "display-xl": [
          "64px",
          { lineHeight: "1.05", letterSpacing: "-0.02em", fontWeight: "900" },
        ],
        "display-lg": [
          "48px",
          { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "900" },
        ],
        "headline-lg": ["32px", { lineHeight: "1.2", fontWeight: "600" }],
        "headline-md": ["20px", { lineHeight: "1.4", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "1.6", fontWeight: "400" }],
        "body-md": ["14px", { lineHeight: "1.5", fontWeight: "400" }],
        "body-sm": ["12px", { lineHeight: "1.5", fontWeight: "400" }],
        "label-md": [
          "12px",
          { lineHeight: "1", letterSpacing: "0.05em", fontWeight: "700" },
        ],
        "label-sm": [
          "10px",
          { lineHeight: "1", letterSpacing: "0.08em", fontWeight: "700" },
        ],
        "mono-md": ["11px", { lineHeight: "1.4", fontWeight: "500" }],
        "mono-sm": ["9px", { lineHeight: "1.2", fontWeight: "500" }],
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/container-queries"),
  ],
};

export default config;
