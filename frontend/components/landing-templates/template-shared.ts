import type { CSSProperties } from "react";
import type { CopyJson } from "@/lib/types";
import type { ResolvedBranding } from "@/lib/branding";
import type { CtaConfig } from "@/lib/cta-config";

export interface TemplateProps {
  copy: CopyJson;
  projectName: string;
  colorMode?: "dark" | "light";
  cssVarStyle?: CSSProperties;
  branding: ResolvedBranding;
  /** Live Fivvle-hosted page (hides editor-only controls). */
  isPublished?: boolean;
  ctaConfig?: CtaConfig;
  publicationSlug?: string;
  scrollTarget?: string;
  /** Editor preview — show full copy without template truncation caps. */
  forEditor?: boolean;
  /** Hosted section images keyed by slot id (see lib/section-images.ts). */
  sectionImages?: Record<string, string>;
  /** Required in editor when section image upload is enabled. */
  experimentId?: string;
  onSectionImageChange?: (slotId: string, url: string | null) => void;
}

export function splitHeadline(headline: string): { main: string; accent?: string } {
  const parts = headline.split(/,\s*/);
  if (parts.length >= 2) {
    return { main: parts[0], accent: parts.slice(1).join(", ") };
  }
  const words = headline.trim().split(/\s+/);
  if (words.length <= 3) return { main: headline };
  const mid = Math.ceil(words.length / 2);
  return {
    main: words.slice(0, mid).join(" "),
    accent: words.slice(mid).join(" "),
  };
}

export function mergeFaq(copy: CopyJson) {
  const faq = [...(copy.faq ?? [])];
  const objections = copy.objections as
    | { items?: { question: string; answer: string }[] }
    | undefined;
  for (const item of objections?.items ?? []) {
    if (!faq.some((f) => f.question === item.question)) {
      faq.push(item);
    }
  }
  return faq;
}
