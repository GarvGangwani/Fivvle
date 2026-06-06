import type { PageJson } from "./types";

export type BrandIconMode = "initials" | "url" | "emoji" | "mark";

export interface PageBranding {
  icon_mode?: BrandIconMode;
  logo_url?: string;
  logo_emoji?: string;
  logo_alt?: string;
}

export interface ResolvedBranding {
  icon_mode: BrandIconMode;
  logo_url: string | null;
  logo_emoji: string | null;
  logo_alt: string;
}

const URL_RE = /^https?:\/\/.+/i;

export function projectInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "F";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function resolveBranding(
  page: PageJson | undefined,
  projectName: string,
): ResolvedBranding {
  const b = page?.branding as PageBranding | undefined;
  const mode = b?.icon_mode ?? "initials";
  const url = b?.logo_url?.trim() || null;
  const emoji = b?.logo_emoji?.trim().slice(0, 4) || null;
  const alt = b?.logo_alt?.trim() || projectName;

  let icon_mode: BrandIconMode = mode;
  if (icon_mode === "url" && (!url || !URL_RE.test(url))) {
    icon_mode = emoji ? "emoji" : "initials";
  }
  if (icon_mode === "emoji" && !emoji) {
    icon_mode = url && URL_RE.test(url ?? "") ? "url" : "initials";
  }

  return {
    icon_mode,
    logo_url: url && URL_RE.test(url) ? url : null,
    logo_emoji: emoji,
    logo_alt: alt,
  };
}

export function defaultBranding(projectName: string): PageBranding {
  return {
    icon_mode: "initials",
    logo_alt: projectName,
  };
}
