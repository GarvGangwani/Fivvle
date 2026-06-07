export type PageGoal =
  | "waitlist"
  | "launch"
  | "app_install"
  | "demo_booking"
  | "investor_teaser"
  | "paid_ads";

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

// --- Backend-matching experiment types ---

export interface RefinedIdea {
  refined_one_liner: string;
  target_audience: string;
  value_proposition: string;
  risks: string[];
  headline: string;
  subheadline: string;
  cta_text: string;
}

export interface ExperimentSummary {
  id: string;
  slug: string | null;
  raw_idea: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ExperimentDetail extends ExperimentSummary {
  refined_idea: RefinedIdea | null;
  landing_page: LandingPageData | null;
  validation_report_id: string | null;
  insight_report_id: string | null;
}

export interface GenerateLandingPageRequest {
  page_goal?: string;
  template_id?: string;
}

export interface GenerateLandingPageResponse {
  experiment_id: string;
  status: string;
}

export interface JobStatus {
  id: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
}

export interface ResearchStatus {
  status: string;
  phase_label: string | null;
  phases_completed: string[];
  last_updated_at: string;
  error_detail: string | null;
}

export interface ExperimentValidationReportSummary {
  overall_recommendation: string | null;
  total_finding_count: number;
  total_citation_count: number;
}

/** GET /experiments/{id} response shape */
export interface Experiment {
  id: string;
  status: string;
  validation_report: ExperimentValidationReportSummary | null;
}

export interface Citation {
  url: string;
  title: string;
  source_domain: string;
  accessed_at: string;
}

export interface Finding {
  question_id: string;
  claim: string;
  evidence_summary: string;
  citations: Citation[];
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface QuestionFindings {
  question_id: string;
  question: string;
  findings: Finding[];
  evidence_gap: string | null;
}

export interface CompetitorMention {
  name: string;
  description: string;
  positioning_vs_idea: string;
  citations: Citation[];
}

export type OverallRecommendation =
  | "proceed"
  | "iterate"
  | "pivot"
  | "kill"
  | "too_vague_to_recommend";

export interface ValidationReport {
  executive_summary: string;
  questions_and_findings: QuestionFindings[];
  competitors: CompetitorMention[];
  market_signals: string;
  distribution_signals: string | null;
  regulatory_signals: string | null;
  risks_assessment: string;
  overall_recommendation: OverallRecommendation;
  recommendation_rationale: string;
  research_limitations: string;
  rubric_version_used: string;
}

export interface LandingPageData {
  copy_json: CopyJson;
  page_json: PageJson;
}

// --- Chat types (POST /chat/turn, ADR 0019) ---

export type ChatRole = "user" | "assistant";

export type ChatTurnKind =
  | "normal_chat"
  | "refinement_clarify"
  | "refinement_finalize"
  | "dispatch_announce"
  | "pipeline_progress"
  | "pipeline_complete"
  | "pipeline_failed";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp?: string;
}

export interface ChatTurnResponse {
  thread_id: string;
  message_id: string;
  experiment_id: string | null;
  assistant_message: string;
  turn_kind: ChatTurnKind;
  clarifying_dimension: string | null;
  pipeline_dispatched: boolean;
  dispatched_at: string | null;
  experiment_status: string | null;
  research_error_detail: string | null;
}
