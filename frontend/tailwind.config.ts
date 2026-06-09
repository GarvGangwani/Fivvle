import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-dm-mono)", "ui-monospace", "monospace"],
      },
      colors: {
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
      },
    },
  },
  plugins: [],
};

export default config;
