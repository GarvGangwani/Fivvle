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

export type SurfaceTexture = "none" | "grain" | "paper" | "dot-grid" | "linen";

export type HeroGlow = "off" | "soft" | "bold";

export type GradientStyle = "flat" | "radial" | "mesh-warm" | "mesh-cool";

export interface PageSurface {
  texture?: SurfaceTexture;
  /** @deprecated Use hero_glow_intensity (0–100). Migrated in resolveSurface(). */
  hero_glow?: HeroGlow;
  gradient_style?: GradientStyle;
  /** 0 = off, 100 = strongest hero spotlight */
  hero_glow_intensity?: number;
  /** 0–100; only applies when texture is not "none" */
  texture_intensity?: number;
  /** 0–100; only applies when gradient_style is not "flat" */
  gradient_intensity?: number;
}

export interface PageJson {
  template_id?: string;
  template_name?: string;
  color_mode?: "dark" | "light";
  color_palette?: Partial<UserColorPalette>;
  surface?: PageSurface;
  branding?: {
    icon_mode?: "initials" | "url" | "emoji" | "mark";
    logo_url?: string;
    logo_emoji?: string;
    logo_alt?: string;
    /** Logo mark scale (%). Default 100. Typical range 60–160. */
    logo_scale?: number;
  };
  /** Template section image slots → hosted image URLs (editor uploads). */
  section_images?: Record<string, string>;
  theme?: PageTheme;
  sections?: Array<{ type: string; content: unknown }>;
  meta?: {
    generation_id?: string;
    generated_at?: string;
    regeneration_hint?: string | null;
  };
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
  project_name?: string | null;
  headline: string;
  subheadline: string;
  cta_text: string;
}

export interface ExperimentCardStats {
  page_views: number;
  waitlist_signups: number;
}

export interface ExperimentSummary {
  id: string;
  slug: string | null;
  name?: string | null;
  raw_idea: string;
  status: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
  card_stats?: ExperimentCardStats | null;
}

export interface SearchResult {
  id: string;
  title: string;
  snippet: string;
  matched_field: string;
  status: string;
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
  name?: string | null;
  raw_idea?: string | null;
  status: string;
  thread_id?: string | null;
  validation_report: ExperimentValidationReportSummary | null;
  refined_idea?: string | RefinedIdea | null;
  refined_idea_current?: RefinedIdea | null;
  refined_idea_updated_at?: string | null;
  chat_message_count?: number;
  evidence_atom_count?: number;
  landing_page_view_count?: number;
  resource_count?: number;
  attachment_count?: number;
  demand_score?: number | null;
  verdict?: string | null;
  spark_last_edited_at?: string | null;
  refinement_started_at?: string | null;
  current_spark_version?: number;
  refine_spark_version?: number | null;
  evidence_spark_version?: number | null;
  launch_spark_version?: number | null;
  signal_spark_version?: number | null;
  refine_is_stale?: boolean;
  evidence_is_stale?: boolean;
  launch_is_stale?: boolean;
  signal_is_stale?: boolean;
}

export interface SparkVersion {
  id: string;
  version_number: number;
  raw_idea: string | null;
  attachment_ids_snapshot: string[];
  created_at: string;
}

// --- Clarifying question block (refinement pre-research) ---

export type ClarifyingSelectionMode = "single" | "multiple";

export interface ClarifyingQuestion {
  question: string;
  selection_mode: ClarifyingSelectionMode;
  options: string[];
}

export interface ClarifyingQuestionAnswer {
  selectedOptions: string[];
  otherText: string;
}

/**
 * A completed clarifying-question turn from earlier in the thread, plus the
 * user's answer to it and the message ID that carries that answer. Passed
 * into ClarifyingQuestionBlock so the wizard can navigate backward across
 * completed turns and let the founder edit any past answer.
 */
export interface PastClarifyingTurn {
  /** The clarifying question the assistant asked in this past turn. */
  question: ClarifyingQuestion;
  /** The user's answer to it, in the same shape as current pending answers. */
  answer: ClarifyingQuestionAnswer;
  /**
   * The message ID of the USER message that carries this answer. This is what
   * we pass to editChatMessage when the founder saves an edit.
   */
  answerMessageId: string;
  /**
   * 1-based question number as displayed globally in the thread. Same
   * numbering scheme ClarifyingQuestionBlock already uses for its current
   * batch.
   */
  globalQuestionNumber: number;
}

export interface ChatHistoryMessage {
  id: string;
  role: ChatRole;
  content: string;
  turn_kind: ChatTurnKind | null;
  clarifying_questions?: ClarifyingQuestion[] | null;
  /** MCQ answer metadata (selected indices, custom text, etc.). */
  metadata?: {
    selected_option_indices?: number[];
    custom_added_text?: string | null;
    answered_question_from_message_id?: string;
  } | null;
  /** Structured tool_call / tool_result payload (universal chat agent shape). */
  tool_payload?: Record<string, unknown> | null;
  parent_message_id?: string | null;
  sibling_index?: number;
  sibling_count?: number;
  created_at: string;
}

export interface ExperimentChatMessagesResponse {
  thread_id: string | null;
  experiment_id: string;
  messages: ChatHistoryMessage[];
}

// --- Evidence chat (founder Q&A over a completed validation report) ---
// Reuses ChatHistoryMessage; evidence chat is a flat thread so the tree fields
// (parent_message_id/sibling_*) just carry their defaults.

export interface EvidenceChatSendRequest {
  message: string;
  selection_text?: string | null;
  selection_question_id?: string | null;
  /** Branch parent. Omit to hang off the current active leaf. */
  parent_message_id?: string | null;
}

export interface EvidenceChatSendResponse {
  user_message: ChatHistoryMessage;
  assistant_message: ChatHistoryMessage;
  thread_id: string;
}

/** Position of a message within its sibling group (same parent). */
export interface SiblingInfo {
  sibling_index: number;
  sibling_count: number;
  /** Ordered (oldest→newest) sibling ids, so the client can activate one by id. */
  sibling_ids: string[];
}

export interface EvidenceChatMessagesResponse {
  thread_id: string | null;
  experiment_id: string;
  active_leaf_message_id: string | null;
  /** Active branch only, root→leaf. */
  messages: ChatHistoryMessage[];
  /** message id → sibling position, for branch-navigation controls. */
  sibling_info: Record<string, SiblingInfo>;
}

export type EvidenceChatVerdict = "up" | "down";

export interface EvidenceChatFeedbackRequest {
  verdict: EvidenceChatVerdict;
}

export interface EvidenceChatFeedbackResponse {
  message_id: string;
  verdict: EvidenceChatVerdict;
}

// Same shape as EvidenceChatSendRequest minus `message` — the parent user
// message supplies the question; only the selection anchor may change.
export interface EvidenceChatRegenerateRequest {
  selection_text?: string | null;
  selection_question_id?: string | null;
}

export interface EvidenceChatRegenerateResponse {
  assistant_message: ChatHistoryMessage;
  thread_id: string;
}

export interface EvidenceChatEditRequest {
  content: string;
  selection_text?: string | null;
  selection_question_id?: string | null;
}

export interface EvidenceChatEditResponse {
  new_user_message: ChatHistoryMessage;
  new_assistant_message: ChatHistoryMessage;
  thread_id: string;
  active_leaf_message_id: string;
  sibling_info: Record<string, SiblingInfo>;
}

export interface EvidenceChatActivateResponse {
  thread_id: string;
  active_leaf_message_id: string;
}

/** `done` SSE frame payload from the evidence-chat streaming endpoint. */
export interface EvidenceChatStreamDone {
  assistant_message_id: string;
  user_message_id: string;
  thread_id: string;
  sibling_info: Record<string, SiblingInfo>;
}

/**
 * In-report reference emitted by the v3 prompt as `[ref: <anchor>]`. Resolved
 * client-side against the report and, on click, focused in the editor. Section
 * refs never navigate the editor (scores were removed from the doc).
 */
export type RefCitation =
  | { kind: "question"; value: string }
  | { kind: "competitor"; value: string }
  | { kind: "section"; value: string }
  | { kind: "limitation"; value: string };

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

export interface SectionScore {
  section_id:
    | "market"
    | "competition"
    | "distribution"
    | "regulatory"
    | "risk"
    | "research";
  label: string;
  score: number;
  rationale?: string | null;
  pros?: string[];
  cons?: string[];
}

export interface QuestionFindings {
  question_id: string;
  question: string;
  findings: Finding[];
  evidence_gap: string | null;
  score?: number | null;
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
  section_scores?: SectionScore[];
  overall_score?: number | null;
}

export interface LandingPageData {
  copy_json: CopyJson;
  page_json: PageJson;
}

/** GET /experiments/{id}/landing-page response */
export interface LandingPage {
  id: string;
  experiment_id: string;
  slug: string;
  template_id: string;
  copy_json: CopyJson;
  page_json: PageJson;
  headline: string;
  subheadline: string | null;
  live_at: string | null;
  output_version?: number;
}

export type LandingPagePatch = {
  copy_json?: CopyJson;
  page_json?: PageJson;
  template_id?: string;
  slug?: string;
};

export interface LandingPageSlugAvailability {
  slug: string;
  available: boolean;
  taken_by_live: boolean;
  message: string | null;
}

// --- Chat types (POST /chat/turn, ADR 0019) ---

export type ChatRole = "user" | "assistant" | "tool_call" | "tool_result";

export type ChatTurnKind =
  | "normal_chat"
  | "discuss"
  | "refinement_clarify"
  | "refinement_finalize"
  | "dispatch_announce"
  | "pipeline_progress"
  | "pipeline_complete"
  | "pipeline_failed"
  | "evidence_chat"
  | "universal_chat";

// --- Universal chat (canvas coach / future agent) ---

export interface UniversalChatSendResponse {
  user_message: ChatHistoryMessage;
  assistant_message: ChatHistoryMessage;
  thread_id: string;
}

export interface UniversalChatMessagesResponse {
  thread_id: string | null;
  experiment_id: string;
  active_leaf_message_id: string | null;
  messages: ChatHistoryMessage[];
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp?: string;
  turnKind?: ChatTurnKind | null;
  clarifyingQuestions?: ClarifyingQuestion[];
}

export interface ChatEditTurnResponse {
  thread_id: string;
  edited_message_id: string;
  message_id: string;
  experiment_id: string | null;
  assistant_message: string;
  turn_kind: ChatTurnKind;
  clarifying_dimension: string | null;
  clarifying_questions?: ClarifyingQuestion[];
  pipeline_dispatched: boolean;
  dispatched_at: string | null;
  experiment_status: string | null;
  research_error_detail: string | null;
  messages: ChatHistoryMessage[];
}

export interface ChatTurnResponse {
  thread_id: string;
  message_id: string;
  experiment_id: string | null;
  assistant_message: string;
  turn_kind: ChatTurnKind;
  clarifying_dimension: string | null;
  clarifying_questions?: ClarifyingQuestion[];
  pipeline_dispatched: boolean;
  dispatched_at: string | null;
  experiment_status: string | null;
  research_error_detail: string | null;
  /** Experiment.refinement_count after this turn (clarify increments). */
  refinement_count?: number | null;
}

// --- Insight & analytics types (ADR 0021) ---

export type InsightRecommendationType = "proceed" | "iterate" | "pivot" | "kill";

export type TakeawaySourceType = "BEHAVIORAL" | "COGNITIVE" | "SYNTHESIZED";

export type FounderDecision = InsightRecommendationType;

export interface WaitlistSignup {
  id: string;
  email: string;
  source_tag: string | null;
  geo_city?: string | null;
  geo_region?: string | null;
  geo_country?: string | null;
  created_at: string;
}

export interface WaitlistSignupsResponse {
  signups: WaitlistSignup[];
  total: number;
}

export interface SignupLocationBucket {
  city: string | null;
  region: string | null;
  country: string | null;
  count: number;
}

export interface ExperimentAnalytics {
  total_page_views: number;
  total_signups: number;
  unique_visitors: number;
  conversion_rate: number;
  views_by_source: Record<string, number>;
  signups_by_source: Record<string, number>;
  conversion_rate_by_source: Record<string, number>;
  signups_by_location: SignupLocationBucket[];
  days_live: number;
  warm_network_bias_index?: number;
}

export interface ResearchTakeaway {
  claim: string;
  cited_finding_ids: string[];
  source_type: TakeawaySourceType;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface TrafficSummary {
  narrative: string;
  headline_metric: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
  source_type: TakeawaySourceType;
}

export interface ConversionSourceCommentary {
  source_name: string;
  views: number;
  signups: number;
  conversion_rate: number;
  commentary: string;
  confidence: "high" | "medium" | "low";
}

export interface ConversionBySource {
  per_source: ConversionSourceCommentary[];
  warm_network_bias_commentary: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface InsightReport {
  traffic_summary: TrafficSummary;
  conversion_by_source: ConversionBySource;
  research_takeaways: ResearchTakeaway[];
  recommendation_type: InsightRecommendationType;
  recommendation: string;
  recommendation_confidence: "high" | "medium" | "low";
  recommendation_rationale: string;
  what_would_change_this: string;
}

export interface GenerateInsightResponse {
  experiment_id: string;
  status: string;
  credits_balance: number;
}

export interface ArchiveExperimentResponse {
  experiment_id: string;
  status: string;
}

export interface DeleteExperimentResponse {
  experiment_id: string;
  deleted: boolean;
}

export type CanvasNodeId =
  | "spark"
  | "refine"
  | "evidence"
  | "launch"
  | "signal"
  | "resources"
  | "spark-expanded"
  | "refine-expanded";

export type SatelliteNodeId = Exclude<
  CanvasNodeId,
  "spark-expanded" | "refine-expanded"
>;

export interface NodePosition {
  x: number;
  y: number;
}

export interface CanvasLayout {
  experiment_id: string;
  user_id: string;
  node_positions: Record<CanvasNodeId, NodePosition>;
  viewport_x?: number | null;
  viewport_y?: number | null;
  viewport_zoom?: number | null;
  updated_at: string;
}

export type ResourceType = "link" | "doc" | "image" | "competitor" | "other";

export type AttachmentType =
  | "image"
  | "document"
  | "pdf"
  | "markdown"
  | "pasted_text"
  | "link";

export interface ExperimentAttachment {
  id: string;
  experiment_id: string;
  user_id: string;
  attachment_type: AttachmentType;
  title: string;
  content_text: string | null;
  file_url: string | null;
  file_mime: string | null;
  file_size_bytes: number | null;
  created_at: string;
}

export interface AttachmentUploadUrl {
  upload_url: string;
  file_url: string;
  expires_at: string;
}

export interface ExperimentResource {
  id: string;
  experiment_id: string;
  user_id: string;
  title: string;
  url: string | null;
  note: string | null;
  resource_type: ResourceType;
  created_at: string;
}

export interface ActivityItem {
  id: string;
  event_type: string;
  summary: string;
  metadata: Record<string, unknown>;
  occurred_at: string;
}
