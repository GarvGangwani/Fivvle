export type CtaMode = "scroll" | "external" | "waitlist";

export interface CtaConfig {
  mode: CtaMode;
  url?: string | null;
}

export function resolveCtaHref(
  config: CtaConfig | undefined,
  scrollTarget = "#cta",
): string {
  if (!config || config.mode === "scroll") return scrollTarget;
  if (config.mode === "external" && config.url) return config.url;
  if (config.mode === "waitlist") return scrollTarget;
  return scrollTarget;
}

export const CTA_MODE_OPTIONS: {
  id: CtaMode;
  label: string;
  description: string;
}[] = [
  {
    id: "waitlist",
    label: "Fivvle waitlist",
    description: "Email capture on your page — leads stored in Fivvle",
  },
  {
    id: "external",
    label: "External link",
    description: "Send visitors to Calendly, Stripe, your app, etc.",
  },
  {
    id: "scroll",
    label: "Scroll to CTA",
    description: "In-page scroll to the bottom signup section",
  },
];
