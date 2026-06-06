export type TemplateId =
  | "dark-premium"
  | "bold-v1"
  | "minimal-v3"
  | "editorial-saas"
  | "aether"
  | "abstract";

export interface PageTemplate {
  id: TemplateId;
  name: string;
  description: string;
  defaultColorMode: "dark" | "light";
  preview: {
    bg: string;
    accent: string;
    text: string;
  };
}

export const PAGE_TEMPLATES: PageTemplate[] = [
  {
    id: "dark-premium",
    name: "Dark Premium",
    description: "Editorial serif hero, gold accents, grain texture — luxury SaaS feel.",
    defaultColorMode: "dark",
    preview: { bg: "#0a0908", accent: "#c9a25f", text: "#ebe4d4" },
  },
  {
    id: "bold-v1",
    name: "Bold V1",
    description: "Oversized display type, high-contrast accent, energetic startup energy.",
    defaultColorMode: "light",
    preview: { bg: "#F5F1EA", accent: "#FF3B1F", text: "#111111" },
  },
  {
    id: "minimal-v3",
    name: "Minimal v3",
    description: "Editorial grid layout, warm cream palette, quiet typography with rail markers.",
    defaultColorMode: "light",
    preview: { bg: "#f7efde", accent: "#C73A1B", text: "#040404" },
  },
  {
    id: "editorial-saas",
    name: "Editorial SaaS",
    description:
      "Premium editorial layout — serif hero, flowing waves, sticky features, light/dark toggle.",
    defaultColorMode: "light",
    preview: { bg: "#f8f8f6", accent: "#000000", text: "#18181b" },
  },
  {
    id: "aether",
    name: "Aether",
    description:
      "Floating pill nav, dark particle hero, lime accent bento grid — modern SaaS landing.",
    defaultColorMode: "light",
    preview: { bg: "#f2f2f2", accent: "#d6fd70", text: "#1d1d1d" },
  },
  {
    id: "abstract",
    name: "Abstract",
    description:
      "Editorial grid, numbered feature rows, dual pricing tiers — warm minimal SaaS.",
    defaultColorMode: "light",
    preview: { bg: "#f6f4f0", accent: "#2d4a3e", text: "#1a1d1b" },
  },
];

export function resolveTemplateId(value: unknown): TemplateId {
  if (
    value === "bold-v1" ||
    value === "dark-premium" ||
    value === "minimal-v3" ||
    value === "editorial-saas" ||
    value === "aether" ||
    value === "abstract"
  ) {
    return value;
  }
  return "dark-premium";
}

export function defaultColorModeForTemplate(id: TemplateId): "dark" | "light" {
  return PAGE_TEMPLATES.find((t) => t.id === id)?.defaultColorMode ?? "dark";
}
