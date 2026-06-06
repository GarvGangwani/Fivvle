export type PageGoal =
  | "waitlist"
  | "launch"
  | "app_install"
  | "demo_booking"
  | "investor_teaser"
  | "paid_ads";

export type WizardStep = "select" | "upload" | "goal" | "progress" | "preview";

export interface CreateProjectResponse {
  message: string;
  project_id: string;
  job_id: string;
  status: string;
}

export interface JobStatus {
  id: string;
  project_id: string;
  job_type: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
  result_json?: Record<string, unknown> | null;
}

export interface LandingPageOutput {
  id: string;
  copy_json: CopyJson;
  page_json: PageJson;
  code_output?: string;
  version: number;
}

export interface CopyJson {
  hero?: HeroCopy;
  problem?: { heading: string; body: string };
  features?: FeatureCopy[];
  comparison?: ComparisonCopy;
  proof?: { headline: string; elements: string[] };
  faq?: FaqItem[];
  cta?: { heading: string; subheading: string; button: string };
  pricing?: unknown;
  [key: string]: unknown;
}

export interface HeroCopy {
  headline: string;
  subheadline: string;
  cta: string;
}

export interface FeatureCopy {
  title: string;
  description: string;
}

export interface ComparisonCopy {
  metric_label: string;
  competitor_name: string;
  our_features: string[];
  competitor_features: string[];
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface PageTheme {
  primary_color?: string;
  accent_color?: string;
  background_color?: string;
  text_color?: string;
  font_family?: string;
  style?: string;
}

export interface UserColorPalette {
  preset: string;
  accent: string;
  background: string;
  foreground: string;
}

export interface PageJson {
  template_id?: string;
  template_name?: string;
  color_mode?: "dark" | "light";
  color_palette?: Partial<UserColorPalette>;
  branding?: {
    icon_mode?: "initials" | "url" | "emoji" | "mark";
    logo_url?: string;
    logo_emoji?: string;
    logo_alt?: string;
  };
  theme?: PageTheme;
  sections?: Array<{ type: string; content: unknown }>;
}

export const PAGE_GOALS: {
  id: PageGoal;
  label: string;
  description: string;
}[] = [
  {
    id: "waitlist",
    label: "Waitlist",
    description: "Capture early interest with trust-first messaging",
  },
  {
    id: "launch",
    label: "MVP Launch",
    description: "Announce your product with benefit-led conversion copy",
  },
  {
    id: "app_install",
    label: "App Install",
    description: "Drive mobile downloads with friction-reducing proof",
  },
  {
    id: "demo_booking",
    label: "Demo Booking",
    description: "Book sales calls with authority and objection handling",
  },
  {
    id: "investor_teaser",
    label: "Investor Teaser",
    description: "Summarize upside, traction signals, and market white-space",
  },
  {
    id: "paid_ads",
    label: "Paid Ads LP",
    description: "Single-offer pages optimized for paid traffic conversion",
  },
];

export const REGENERATABLE_SECTIONS = [
  "hero",
  "problem",
  "features",
  "comparison",
  "proof",
  "objections",
  "faq",
  "pricing",
  "cta",
] as const;

export type RegenerableSection = (typeof REGENERATABLE_SECTIONS)[number];
