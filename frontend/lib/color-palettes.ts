import type { TemplateId } from "./templates";

export type ColorMode = "light" | "dark";

export interface UserColorPalette {
  preset: string;
  accent: string;
  background: string;
  foreground: string;
}

export interface ColorPreset extends UserColorPalette {
  id: string;
  name: string;
}

const PRESETS: Record<TemplateId, ColorPreset[]> = {
  "dark-premium": [
    {
      id: "gold-dark",
      name: "Gold (default)",
      preset: "gold-dark",
      accent: "#c9a25f",
      background: "#0a0908",
      foreground: "#ebe4d4",
    },
    {
      id: "silver-dark",
      name: "Silver",
      preset: "silver-dark",
      accent: "#b8c0cc",
      background: "#0a0c10",
      foreground: "#e8ecf0",
    },
    {
      id: "emerald-dark",
      name: "Emerald",
      preset: "emerald-dark",
      accent: "#6ee7b7",
      background: "#061210",
      foreground: "#e6f5f0",
    },
  ],
  "bold-v1": [
    {
      id: "red-light",
      name: "Bold red (default)",
      preset: "red-light",
      accent: "#FF3B1F",
      background: "#F5F1EA",
      foreground: "#111111",
    },
    {
      id: "lime-dark",
      name: "Neon dark",
      preset: "lime-dark",
      accent: "#C8FF3F",
      background: "#0E0E1A",
      foreground: "#F0EBE0",
    },
    {
      id: "blue-light",
      name: "Ocean",
      preset: "blue-light",
      accent: "#2563EB",
      background: "#EEF4FA",
      foreground: "#0A1628",
    },
  ],
  "minimal-v3": [
    {
      id: "warm-default",
      name: "Warm (default)",
      preset: "warm-default",
      accent: "#C73A1B",
      background: "#f7efde",
      foreground: "#040404",
    },
    {
      id: "slate",
      name: "Slate",
      preset: "slate",
      accent: "#475569",
      background: "#f1f5f9",
      foreground: "#0f172a",
    },
    {
      id: "forest",
      name: "Forest",
      preset: "forest",
      accent: "#2D6A4F",
      background: "#F0F4F1",
      foreground: "#1B1B1B",
    },
  ],
  "editorial-saas": [
    {
      id: "paper-light",
      name: "Paper (default)",
      preset: "paper-light",
      accent: "#000000",
      background: "#f8f8f6",
      foreground: "#18181b",
    },
    {
      id: "ink-dark",
      name: "Ink dark",
      preset: "ink-dark",
      accent: "#ffffff",
      background: "#0d0e12",
      foreground: "#f5f5f7",
    },
    {
      id: "indigo",
      name: "Indigo",
      preset: "indigo",
      accent: "#4f46e5",
      background: "#f4f4f8",
      foreground: "#18181b",
    },
  ],
  aether: [
    {
      id: "lime-light",
      name: "Lime (default)",
      preset: "lime-light",
      accent: "#d6fd70",
      background: "#f2f2f2",
      foreground: "#1d1d1d",
    },
    {
      id: "violet",
      name: "Violet",
      preset: "violet",
      accent: "#a78bfa",
      background: "#f4f2f8",
      foreground: "#131313",
    },
    {
      id: "midnight",
      name: "Midnight",
      preset: "midnight",
      accent: "#d6fd70",
      background: "#ececec",
      foreground: "#0a0a0a",
    },
  ],
  abstract: [
    {
      id: "forest-light",
      name: "Forest (default)",
      preset: "forest-light",
      accent: "#2d4a3e",
      background: "#f6f4f0",
      foreground: "#1a1d1b",
    },
    {
      id: "slate-warm",
      name: "Slate warm",
      preset: "slate-warm",
      accent: "#475569",
      background: "#f4f2ee",
      foreground: "#1c1917",
    },
    {
      id: "ink-dark",
      name: "Ink dark",
      preset: "ink-dark",
      accent: "#8fbc8f",
      background: "#141816",
      foreground: "#eceae4",
    },
  ],
};

export function getPresetsForTemplate(templateId: TemplateId): ColorPreset[] {
  return PRESETS[templateId] ?? PRESETS["dark-premium"];
}

export function defaultPaletteForTemplate(templateId: TemplateId): UserColorPalette {
  const p = getPresetsForTemplate(templateId)[0];
  return {
    preset: p.preset,
    accent: p.accent,
    background: p.background,
    foreground: p.foreground,
  };
}

export function resolveColorPalette(
  pageJson: { color_palette?: Partial<UserColorPalette> } | undefined,
  templateId: TemplateId,
): UserColorPalette {
  const defaults = defaultPaletteForTemplate(templateId);
  const cp = pageJson?.color_palette;
  if (!cp) return defaults;
  return {
    preset: cp.preset ?? defaults.preset,
    accent: cp.accent ?? defaults.accent,
    background: cp.background ?? defaults.background,
    foreground: cp.foreground ?? defaults.foreground,
  };
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = hex.replace("#", "").match(/^([0-9a-f]{6})$/i);
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

function mix(a: string, b: string, t: number): string {
  const ca = hexToRgb(a);
  const cb = hexToRgb(b);
  if (!ca || !cb) return a;
  const r = Math.round(ca.r + (cb.r - ca.r) * t);
  const g = Math.round(ca.g + (cb.g - ca.g) * t);
  const bl = Math.round(ca.b + (cb.b - ca.b) * t);
  return `#${[r, g, bl].map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

function withAlpha(hex: string, alpha: number): string {
  const c = hexToRgb(hex);
  if (!c) return hex;
  return `rgba(${c.r}, ${c.g}, ${c.b}, ${alpha})`;
}

/** 0–1 relative luminance for hex colors */
export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0.5;
  return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
}

/** Text color that contrasts with a solid fill (buttons, badges) */
export function contrastInk(onHex: string): string {
  return relativeLuminance(onHex) > 0.52 ? "#111111" : "#f8f8f8";
}

/** Map user palette → template CSS custom properties */
export function paletteToCssVars(
  templateId: TemplateId,
  palette: UserColorPalette,
  colorMode: ColorMode,
): Record<string, string> {
  const { accent, background, foreground } = palette;
  const muted = mix(foreground, background, 0.45);
  const faint = withAlpha(foreground, 0.2);
  const rule = withAlpha(foreground, colorMode === "dark" ? 0.12 : 0.1);
  const accentOn = contrastInk(accent);
  const textOn = contrastInk(foreground);
  const bgOn = contrastInk(background);
  const accentGlow = withAlpha(accent, 0.28);

  if (templateId === "dark-premium") {
    return {
      "--bg": background,
      "--bg-2": mix(background, foreground, 0.08),
      "--text": foreground,
      "--text-soft": muted,
      "--text-muted": mix(foreground, background, 0.55),
      "--line": rule,
      "--line-strong": withAlpha(foreground, 0.22),
      "--accent": accent,
      "--accent-on": accentOn,
      "--text-on": textOn,
      "--bg-on": bgOn,
      "--accent-glow": accentGlow,
    };
  }

  if (templateId === "bold-v1") {
    return {
      "--bg": background,
      "--bg-2": mix(background, foreground, 0.06),
      "--fg": foreground,
      "--fg-on": textOn,
      "--bg-on": bgOn,
      "--muted": withAlpha(foreground, 0.62),
      "--rule": rule,
      "--accent": accent,
      "--accent-ink": accentOn,
      "--accent-soft": withAlpha(accent, 0.18),
      "--inverse-bg": colorMode === "dark" ? foreground : "#111111",
      "--inverse-fg": contrastInk(colorMode === "dark" ? foreground : "#111111"),
    };
  }

  if (templateId === "minimal-v3") {
    return {
      "--bg": background,
      "--fg": foreground,
      "--fg-on": textOn,
      "--bg-on": bgOn,
      "--fg-dim": withAlpha(foreground, 0.69),
      "--fg-faint": faint,
      "--rule": rule,
      "--accent": accent,
      "--accent-on": accentOn,
    };
  }

  if (templateId === "editorial-saas") {
    return {
      "--bg": background,
      "--bg-secondary": mix(background, foreground, colorMode === "dark" ? 0.1 : 0.06),
      "--bg-card": colorMode === "dark" ? mix(background, foreground, 0.14) : "#ffffff",
      "--text": foreground,
      "--text-on": textOn,
      "--text-muted": muted,
      "--text-faint": withAlpha(foreground, 0.35),
      "--border": rule,
      "--border-strong": withAlpha(foreground, colorMode === "dark" ? 0.15 : 0.15),
      "--accent": accent,
      "--accent-hover": mix(accent, foreground, 0.25),
      "--accent-ink": accentOn,
    };
  }

  if (templateId === "abstract") {
    return {
      "--bg": background,
      "--bg-alt": mix(background, foreground, colorMode === "dark" ? 0.12 : 0.06),
      "--ink": foreground,
      "--ink-muted": muted,
      "--ink-faint": withAlpha(foreground, 0.45),
      "--accent": accent,
      "--accent-light": mix(accent, foreground, colorMode === "dark" ? 0.35 : 0.2),
      "--accent-surface": withAlpha(accent, 0.06),
      "--border": rule,
      "--border-hover": withAlpha(foreground, 0.18),
    };
  }

  // aether
  return {
    "--bg": background,
    "--bg-2": mix(background, foreground, 0.06),
    "--fg": foreground,
    "--muted": muted,
    "--accent": accent,
    "--accent-on": accentOn,
    "--on-dark": "#ffffff",
    "--surface-dark": mix(foreground, "#000000", 0.85),
  };
}

export function cssVarsToStyle(vars: Record<string, string>): Record<string, string> {
  return vars;
}

const NAMED_COLORS: Record<string, string> = {
  red: "#DC2626",
  orange: "#EA580C",
  gold: "#CA8A04",
  green: "#16A34A",
  blue: "#2563EB",
  navy: "#1E3A5F",
  purple: "#7C3AED",
  pink: "#DB2777",
  black: "#111111",
  white: "#FAFAFA",
  cream: "#F5F0E3",
  slate: "#475569",
  silver: "#94A3B8",
  teal: "#0D9488",
  coral: "#E55E40",
};

/** Parse hex and named colors from brand visual_direction text */
export function extractColorsFromBrand(visualDirection: string): Partial<UserColorPalette> {
  const found: string[] = [];
  const hexMatches = visualDirection.match(/#([0-9A-Fa-f]{3,8})\b/g) ?? [];
  found.push(...hexMatches.map((h) => (h.length === 4 ? h : h)));

  const lower = visualDirection.toLowerCase();
  for (const [name, hex] of Object.entries(NAMED_COLORS)) {
    if (lower.includes(name) && !found.includes(hex)) {
      found.push(hex);
    }
  }

  const normalize = (h: string) => {
    if (h.length === 4) {
      return `#${h[1]}${h[1]}${h[2]}${h[2]}${h[3]}${h[3]}`;
    }
    return h;
  };

  const colors = [...new Set(found.map(normalize))];
  if (colors.length === 0) return {};

  const accent = colors[0];
  const background =
    colors.find((c) => {
      const rgb = hexToRgb(c);
      return rgb && (rgb.r + rgb.g + rgb.b) / 3 > 180;
    }) ?? "#f7efde";
  const foreground =
    colors.find((c) => {
      const rgb = hexToRgb(c);
      return rgb && (rgb.r + rgb.g + rgb.b) / 3 < 80;
    }) ?? "#111111";

  return {
    preset: "brand",
    accent,
    background,
    foreground,
  };
}
