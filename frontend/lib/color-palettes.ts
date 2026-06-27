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

const DEFAULT_PRESET_ID: Record<TemplateId, string> = {
  "dark-premium": "gold-dark",
  "bold-v1": "red-light",
  "minimal-v3": "warm-default",
  "editorial-saas": "paper-light",
  aether: "lime-light",
  abstract: "forest-light",
};

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
    {
      id: "rose-dark",
      name: "Rose",
      preset: "rose-dark",
      accent: "#f472b6",
      background: "#100a0e",
      foreground: "#f5e8ef",
    },
    {
      id: "cyan-dark",
      name: "Cyan",
      preset: "cyan-dark",
      accent: "#22d3ee",
      background: "#060c10",
      foreground: "#e6f4f8",
    },
    {
      id: "champagne-light",
      name: "Champagne",
      preset: "champagne-light",
      accent: "#a67c3d",
      background: "#f7f3eb",
      foreground: "#1c1814",
    },
    {
      id: "ivory-light",
      name: "Ivory",
      preset: "ivory-light",
      accent: "#4a5568",
      background: "#faf9f7",
      foreground: "#1a1d24",
    },
    {
      id: "sage-mist-light",
      name: "Sage mist",
      preset: "sage-mist-light",
      accent: "#3d6b54",
      background: "#f2f6f3",
      foreground: "#142019",
    },
    {
      id: "blush-light",
      name: "Blush",
      preset: "blush-light",
      accent: "#be4a6f",
      background: "#faf5f6",
      foreground: "#241418",
    },
    {
      id: "cool-slate-light",
      name: "Cool slate",
      preset: "cool-slate-light",
      accent: "#3b5bdb",
      background: "#f3f5fa",
      foreground: "#12141f",
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
      id: "blue-light",
      name: "Ocean",
      preset: "blue-light",
      accent: "#2563EB",
      background: "#EEF4FA",
      foreground: "#0A1628",
    },
    {
      id: "coral-light",
      name: "Coral",
      preset: "coral-light",
      accent: "#E85D3A",
      background: "#FBF4EF",
      foreground: "#1A120E",
    },
    {
      id: "amber-light",
      name: "Amber",
      preset: "amber-light",
      accent: "#D97706",
      background: "#FBF6EE",
      foreground: "#1A1408",
    },
    {
      id: "forest-light-bold",
      name: "Forest",
      preset: "forest-light-bold",
      accent: "#15803D",
      background: "#F0F5F1",
      foreground: "#0F1A14",
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
      id: "violet-dark",
      name: "Violet night",
      preset: "violet-dark",
      accent: "#A78BFA",
      background: "#12101A",
      foreground: "#EDE9FE",
    },
    {
      id: "ember-dark",
      name: "Ember",
      preset: "ember-dark",
      accent: "#FB7185",
      background: "#140E10",
      foreground: "#F8ECEE",
    },
    {
      id: "ocean-deep-dark",
      name: "Deep ocean",
      preset: "ocean-deep-dark",
      accent: "#38BDF8",
      background: "#081018",
      foreground: "#E8F4FC",
    },
    {
      id: "graphite-dark",
      name: "Graphite",
      preset: "graphite-dark",
      accent: "#E2E8F0",
      background: "#111318",
      foreground: "#F1F5F9",
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
    {
      id: "ink-minimal",
      name: "Ink",
      preset: "ink-minimal",
      accent: "#111111",
      background: "#FAFAF8",
      foreground: "#111111",
    },
    {
      id: "terracotta",
      name: "Terracotta",
      preset: "terracotta",
      accent: "#B45309",
      background: "#F9F3EB",
      foreground: "#292524",
    },
    {
      id: "charcoal-dark",
      name: "Charcoal",
      preset: "charcoal-dark",
      accent: "#F4F4F5",
      background: "#18181B",
      foreground: "#FAFAFA",
    },
    {
      id: "midnight-dark",
      name: "Midnight",
      preset: "midnight-dark",
      accent: "#60A5FA",
      background: "#0C1220",
      foreground: "#E8EEF8",
    },
    {
      id: "moss-dark",
      name: "Moss",
      preset: "moss-dark",
      accent: "#86EFAC",
      background: "#0E1612",
      foreground: "#EAF5EE",
    },
    {
      id: "wine-dark",
      name: "Wine",
      preset: "wine-dark",
      accent: "#F472B6",
      background: "#140C10",
      foreground: "#F8ECF2",
    },
    {
      id: "navy-dark",
      name: "Navy",
      preset: "navy-dark",
      accent: "#93C5FD",
      background: "#0A1020",
      foreground: "#E6EDF8",
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
      id: "indigo",
      name: "Indigo",
      preset: "indigo",
      accent: "#4f46e5",
      background: "#f4f4f8",
      foreground: "#18181b",
    },
    {
      id: "terracotta-editorial",
      name: "Terracotta",
      preset: "terracotta-editorial",
      accent: "#c2410c",
      background: "#faf8f5",
      foreground: "#1c1917",
    },
    {
      id: "sage",
      name: "Sage",
      preset: "sage",
      accent: "#3f6212",
      background: "#f6f7f2",
      foreground: "#1a1d14",
    },
    {
      id: "blush-editorial",
      name: "Blush",
      preset: "blush-editorial",
      accent: "#be185d",
      background: "#faf6f7",
      foreground: "#1c1418",
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
      id: "midnight-editorial",
      name: "Midnight",
      preset: "midnight-editorial",
      accent: "#818cf8",
      background: "#0b0d18",
      foreground: "#eef0ff",
    },
    {
      id: "forest-editorial-dark",
      name: "Forest",
      preset: "forest-editorial-dark",
      accent: "#86efac",
      background: "#0c1210",
      foreground: "#ecf8f0",
    },
    {
      id: "copper-dark",
      name: "Copper",
      preset: "copper-dark",
      accent: "#f59e0b",
      background: "#12100c",
      foreground: "#f8f2e8",
    },
    {
      id: "slate-editorial-dark",
      name: "Slate",
      preset: "slate-editorial-dark",
      accent: "#94a3b8",
      background: "#101318",
      foreground: "#eef1f6",
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
      id: "coral-aether",
      name: "Coral",
      preset: "coral-aether",
      accent: "#fb7185",
      background: "#f8f4f4",
      foreground: "#1a1414",
    },
    {
      id: "sky-aether",
      name: "Sky",
      preset: "sky-aether",
      accent: "#38bdf8",
      background: "#f2f6fa",
      foreground: "#0f172a",
    },
    {
      id: "peach-light",
      name: "Peach",
      preset: "peach-light",
      accent: "#f97316",
      background: "#faf6f2",
      foreground: "#1a1410",
    },
    {
      id: "carbon-dark",
      name: "Carbon",
      preset: "carbon-dark",
      accent: "#d6fd70",
      background: "#111111",
      foreground: "#f0f0f0",
    },
    {
      id: "violet-deep-dark",
      name: "Deep violet",
      preset: "violet-deep-dark",
      accent: "#c4b5fd",
      background: "#100e18",
      foreground: "#ede9fe",
    },
    {
      id: "rose-night-dark",
      name: "Rose night",
      preset: "rose-night-dark",
      accent: "#fb7185",
      background: "#140e12",
      foreground: "#f8ecef",
    },
    {
      id: "ocean-aether-dark",
      name: "Ocean deep",
      preset: "ocean-aether-dark",
      accent: "#38bdf8",
      background: "#081018",
      foreground: "#e8f4fc",
    },
    {
      id: "ember-aether-dark",
      name: "Ember",
      preset: "ember-aether-dark",
      accent: "#fb923c",
      background: "#12100c",
      foreground: "#f8f0e8",
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
      id: "clay",
      name: "Clay",
      preset: "clay",
      accent: "#a16207",
      background: "#f5f0e8",
      foreground: "#292524",
    },
    {
      id: "ocean-abstract",
      name: "Ocean",
      preset: "ocean-abstract",
      accent: "#0d9488",
      background: "#f0f7f6",
      foreground: "#134e4a",
    },
    {
      id: "sand-light",
      name: "Sand",
      preset: "sand-light",
      accent: "#92400e",
      background: "#f8f4ec",
      foreground: "#292018",
    },
    {
      id: "ink-dark",
      name: "Ink dark",
      preset: "ink-dark",
      accent: "#8fbc8f",
      background: "#141816",
      foreground: "#eceae4",
    },
    {
      id: "moss-abstract-dark",
      name: "Moss night",
      preset: "moss-abstract-dark",
      accent: "#6ee7b7",
      background: "#0e1412",
      foreground: "#e8f5ef",
    },
    {
      id: "clay-dark",
      name: "Clay dark",
      preset: "clay-dark",
      accent: "#fbbf24",
      background: "#12100c",
      foreground: "#f5efe6",
    },
    {
      id: "teal-deep-dark",
      name: "Teal deep",
      preset: "teal-deep-dark",
      accent: "#2dd4bf",
      background: "#0a1212",
      foreground: "#e6f5f3",
    },
    {
      id: "charcoal-warm-dark",
      name: "Charcoal warm",
      preset: "charcoal-warm-dark",
      accent: "#d6d3d1",
      background: "#161412",
      foreground: "#f5f3f0",
    },
  ],
};

export function getPresetsForTemplate(templateId: TemplateId): ColorPreset[] {
  return PRESETS[templateId] ?? PRESETS["dark-premium"];
}

export function defaultPresetForTemplate(templateId: TemplateId): ColorPreset {
  const presets = getPresetsForTemplate(templateId);
  const targetId = DEFAULT_PRESET_ID[templateId];
  return presets.find((p) => p.id === targetId) ?? presets[0];
}

export function defaultPaletteForTemplate(templateId: TemplateId): UserColorPalette {
  const p = defaultPresetForTemplate(templateId);
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

/** Hue anchors tuned per template mood (degrees). */
const TEMPLATE_HUE_ANCHORS: Record<TemplateId, number[]> = {
  "dark-premium": [42, 155, 330, 215, 185],
  "bold-v1": [8, 75, 220, 18, 265],
  "minimal-v3": [12, 28, 350, 200, 45],
  "editorial-saas": [155, 35, 210, 25, 175],
  aether: [245, 195, 265, 220, 170],
  abstract: [145, 38, 165, 25, 95],
};

/** Extended hue sets for random palette generation (15+ per mode, per template). */
const TEMPLATE_RANDOM_HUES: Record<TemplateId, { light: number[]; dark: number[] }> = {
  "dark-premium": {
    light: [38, 48, 55, 165, 185, 200, 215, 280, 300, 320, 340, 15, 25, 95, 120, 145],
    dark: [35, 42, 50, 155, 170, 190, 205, 225, 265, 285, 310, 330, 350, 75, 110, 130],
  },
  "bold-v1": {
    light: [5, 12, 22, 35, 48, 165, 195, 210, 225, 250, 275, 300, 330, 350, 55, 85],
    dark: [8, 18, 28, 45, 72, 180, 200, 215, 235, 255, 275, 295, 315, 335, 350, 95],
  },
  "minimal-v3": {
    light: [8, 18, 28, 42, 55, 95, 125, 155, 175, 195, 215, 235, 280, 310, 340, 350],
    dark: [10, 22, 35, 48, 62, 100, 130, 150, 170, 190, 210, 230, 260, 290, 320, 345],
  },
  "editorial-saas": {
    light: [0, 18, 32, 48, 72, 95, 125, 155, 175, 195, 215, 235, 260, 285, 310, 330],
    dark: [12, 28, 42, 58, 82, 105, 135, 160, 180, 200, 220, 245, 270, 295, 315, 340],
  },
  aether: {
    light: [165, 185, 200, 215, 235, 250, 265, 280, 295, 310, 330, 350, 25, 55, 85, 120],
    dark: [170, 190, 205, 220, 240, 255, 270, 285, 300, 315, 330, 345, 15, 45, 75, 105],
  },
  abstract: {
    light: [25, 38, 55, 85, 110, 135, 155, 175, 195, 215, 235, 260, 285, 310, 330, 350],
    dark: [22, 35, 50, 78, 105, 130, 150, 170, 190, 210, 230, 255, 280, 305, 325, 345],
  },
};

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b]
    .map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0"))
    .join("")}`;
}

function hslToHex(h: number, s: number, l: number): string {
  const sat = Math.max(0, Math.min(100, s)) / 100;
  const lit = Math.max(0, Math.min(100, l)) / 100;
  const hue = ((h % 360) + 360) % 360;
  const c = (1 - Math.abs(2 * lit - 1)) * sat;
  const x = c * (1 - Math.abs(((hue / 60) % 2) - 1));
  const m = lit - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (hue < 60) {
    r = c;
    g = x;
  } else if (hue < 120) {
    r = x;
    g = c;
  } else if (hue < 180) {
    g = c;
    b = x;
  } else if (hue < 240) {
    g = x;
    b = c;
  } else if (hue < 300) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }
  return rgbToHex((r + m) * 255, (g + m) * 255, (b + m) * 255);
}

function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const rgb = hexToRgb(hex);
  if (!rgb) return { h: 0, s: 0, l: 50 };
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l: l * 100 };
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return { h: h * 360, s: s * 100, l: l * 100 };
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function ensureTextContrast(foreground: string, background: string): string {
  let fg = foreground;
  let hsl = hexToHsl(fg);
  const bgLum = relativeLuminance(background);
  const targetL = bgLum > 0.5 ? 12 : 90;
  for (let i = 0; i < 20; i += 1) {
    if (contrastRatio(fg, background) >= 4.5) return fg;
    hsl.l += hsl.l > targetL ? -3 : 3;
    hsl.l = Math.max(4, Math.min(96, hsl.l));
    fg = hslToHex(hsl.h, hsl.s, hsl.l);
  }
  return fg;
}

/** Infer light/dark page mode from background luminance. */
export function inferColorModeFromPalette(palette: UserColorPalette): ColorMode {
  return relativeLuminance(palette.background) > 0.45 ? "light" : "dark";
}

export function getPresetsByMode(
  templateId: TemplateId,
): { light: ColorPreset[]; dark: ColorPreset[] } {
  const presets = getPresetsForTemplate(templateId);
  const light: ColorPreset[] = [];
  const dark: ColorPreset[] = [];
  for (const preset of presets) {
    if (inferColorModeFromPalette(preset) === "dark") {
      dark.push(preset);
    } else {
      light.push(preset);
    }
  }
  return { light, dark };
}

function jitterHex(
  hex: string,
  opts: { dh?: number; ds?: number; dl?: number; minL?: number; maxL?: number },
): string {
  const hsl = hexToHsl(hex);
  const h = hsl.h + (Math.random() - 0.5) * (opts.dh ?? 20);
  const s = Math.max(4, Math.min(92, hsl.s + (Math.random() - 0.5) * (opts.ds ?? 14)));
  let l = hsl.l + (Math.random() - 0.5) * (opts.dl ?? 10);
  if (opts.minL != null) l = Math.max(opts.minL, l);
  if (opts.maxL != null) l = Math.min(opts.maxL, l);
  l = Math.max(2, Math.min(98, l));
  return hslToHex(h, s, l);
}

function jitterFromPreset(seed: UserColorPalette, colorMode: ColorMode): UserColorPalette {
  const isDark = colorMode === "dark";
  const accent = jitterHex(seed.accent, { dh: 22, ds: 20, dl: isDark ? 12 : 14 });
  const background = jitterHex(seed.background, {
    dh: 16,
    ds: isDark ? 14 : 16,
    dl: isDark ? 8 : 6,
    minL: isDark ? 2 : 84,
    maxL: isDark ? 18 : 98,
  });
  const foreground = ensureTextContrast(
    jitterHex(seed.foreground, {
      dh: 12,
      ds: 14,
      dl: isDark ? 10 : 8,
      minL: isDark ? 76 : 4,
      maxL: isDark ? 96 : 24,
    }),
    background,
  );
  return { preset: "random", accent, background, foreground };
}

/** Shift any designer preset into a target light/dark mode while keeping hue character. */
function remapPaletteToMode(palette: UserColorPalette, targetMode: ColorMode): UserColorPalette {
  const isDark = targetMode === "dark";
  const accentH = hexToHsl(palette.accent);
  const bgH = hexToHsl(palette.background);
  const fgH = hexToHsl(palette.foreground);
  const hueAnchor = accentH.h;
  const bgHue = bgH.h + (hueAnchor - bgH.h) * 0.35;

  const accent = hslToHex(
    hueAnchor,
    Math.max(isDark ? 40 : 45, Math.min(90, accentH.s)),
    isDark
      ? Math.max(50, Math.min(70, accentH.l < 42 ? accentH.l + 20 : accentH.l))
      : Math.max(30, Math.min(52, accentH.l > 62 ? accentH.l - 16 : accentH.l)),
  );

  const background = hslToHex(
    bgHue,
    isDark ? Math.min(26, Math.max(8, bgH.s)) : Math.min(30, Math.max(5, bgH.s * 0.75)),
    isDark ? Math.max(3, Math.min(13, 5 + (bgH.l % 6))) : Math.max(89, Math.min(97, 93 + (bgH.l % 4))),
  );

  const foreground = ensureTextContrast(
    hslToHex(
      fgH.h,
      isDark ? Math.min(20, Math.max(4, fgH.s * 0.6)) : Math.min(24, Math.max(6, fgH.s * 0.7)),
      isDark ? 90 + (fgH.l % 5) : 9 + (fgH.l % 6),
    ),
    background,
  );

  return { preset: palette.preset, accent, background, foreground };
}

function seedsFromHues(hues: number[], colorMode: ColorMode): UserColorPalette[] {
  const isDark = colorMode === "dark";
  return hues.map((hue, index) => {
    const accentSat = isDark ? 48 + (index % 4) * 9 : 52 + (index % 5) * 7;
    const accentLight = isDark ? 54 + (index % 3) * 7 : 34 + (index % 4) * 5;
    const accent = hslToHex(hue, accentSat, accentLight);

    const bgHue = hue + (index % 2 === 0 ? 12 : -14) + (index % 3) * 4;
    const bgSat = isDark ? 10 + (index % 4) * 4 : 8 + (index % 5) * 3;
    const bgLight = isDark ? 4 + (index % 5) * 1.6 : 91 + (index % 4) * 1.5;
    const background = hslToHex(bgHue, bgSat, bgLight);

    const fgHue = hue + (index % 2 === 0 ? -6 : 8);
    const fgSat = isDark ? 6 + (index % 3) * 4 : 10 + (index % 4) * 3;
    const fgLight = isDark ? 90 + (index % 3) : 10 + (index % 4);
    const foreground = ensureTextContrast(hslToHex(fgHue, fgSat, fgLight), background);

    return { preset: "random", accent, background, foreground };
  });
}

function buildRandomSeedPool(templateId: TemplateId, colorMode: ColorMode): UserColorPalette[] {
  const presets = getPresetsForTemplate(templateId);
  const hues = TEMPLATE_RANDOM_HUES[templateId] ?? TEMPLATE_RANDOM_HUES["editorial-saas"];
  const generated = seedsFromHues(hues[colorMode], colorMode);
  const remappedPresets = presets.map((preset) => remapPaletteToMode(preset, colorMode));
  return [...generated, ...remappedPresets];
}

function generateAlgorithmicPalette(templateId: TemplateId, colorMode: ColorMode): UserColorPalette {
  const isDark = colorMode === "dark";
  const strategy = Math.floor(Math.random() * 4);
  let baseHue = pickHue(templateId);

  if (strategy === 1) {
    baseHue = (baseHue + 150 + (Math.random() - 0.5) * 30) % 360;
  } else if (strategy === 2) {
    baseHue = (baseHue + 30 + (Math.random() - 0.5) * 20) % 360;
  } else if (strategy === 3) {
    baseHue = (baseHue + 180 + (Math.random() - 0.5) * 24) % 360;
  }

  const accentS = isDark ? 42 + Math.random() * 38 : 48 + Math.random() * 34;
  const accentL = isDark ? 52 + Math.random() * 18 : 32 + Math.random() * 18;
  const accent = hslToHex(baseHue, accentS, accentL);

  const bgHue = baseHue + (Math.random() - 0.5) * 28;
  const bgS = isDark ? 10 + Math.random() * 22 : 6 + Math.random() * 28;
  const bgL = isDark ? 3 + Math.random() * 9 : 88 + Math.random() * 8;
  const background = hslToHex(bgHue, bgS, bgL);

  const fgHue = baseHue + (Math.random() - 0.5) * 16;
  const fgS = isDark ? 6 + Math.random() * 16 : 8 + Math.random() * 20;
  const fgL = isDark ? 86 + Math.random() * 10 : 6 + Math.random() * 12;
  const foreground = ensureTextContrast(hslToHex(fgHue, fgS, fgL), background);

  return { preset: "random", accent, background, foreground };
}

function pickHue(templateId: TemplateId): number {
  const anchors = TEMPLATE_HUE_ANCHORS[templateId] ?? TEMPLATE_HUE_ANCHORS["dark-premium"];
  const anchor = anchors[Math.floor(Math.random() * anchors.length)];
  return anchor + (Math.random() - 0.5) * 16;
}

/**
 * Generate a harmonious palette for the template — draws from 16+ hue seeds per mode,
 * all designer presets remapped to the target mode, then jitters in HSL space.
 */
export function generateIntelligentPalette(
  templateId: TemplateId,
  colorMode: ColorMode,
): UserColorPalette {
  const pool = buildRandomSeedPool(templateId, colorMode);
  const seed = pool[Math.floor(Math.random() * pool.length)];

  if (Math.random() < 0.12) {
    return generateAlgorithmicPalette(templateId, colorMode);
  }

  return jitterFromPreset(seed, colorMode);
}
