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

/**
 * Mirrors backend `ExperimentStatus` StrEnum in `backend/app/db/enums.py`.
 * Every member must stay in sync when the backend enum grows.
 */
export type ExperimentStatus =
  | "SPARK"
  | "DRAFT"
  | "REFINING"
  | "REFINED"
  | "RESEARCHING"
  | "RESEARCH_PLANNING"
  | "RESEARCH_SEARCHING"
  | "RESEARCH_READING"
  | "RESEARCH_REFLECTING"
  | "RESEARCH_VOICES"
  | "RESEARCH_SYNTHESIZING"
  | "RESEARCH_READY"
  | "RESEARCH_FAILED"
  | "LANDING_GENERATING"
  | "LANDING_DRAFT"
  | "LANDING_LIVE"
  | "INSIGHT_GENERATING"
  | "INSIGHT_READY"
  | "INSIGHT_FAILED"
  | "ARCHIVED";

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
  /** True once write-once original_idea has been captured. */
  has_original_idea?: boolean;
  /** Immutable original idea text (null until captured). */
  original_idea?: string | null;
  original_idea_captured_at?: string | null;
  /** Origin Artifact theme — violet | pink | green | orange. */
  idea_theme?: string | null;
  /** Chat attachments frozen to the original idea at capture. */
  origin_attachments?: OriginFrozenAttachment[];
  /** Research validation overall_recommendation — not the founder Signal decision. */
  verdict?: string | null;
  founder_decision?: FounderDecision | null;
  founder_decision_at?: string | null;
  founder_decision_note?: string | null;
  founder_decision_version?: number | null;
  spark_last_edited_at?: string | null;
  refinement_started_at?: string | null;
  current_spark_version?: number;
  current_refined_idea_version?: number;
  current_edited_doc_version?: number | null;
  refine_spark_version?: number | null;
  evidence_spark_version?: number | null;
  launch_spark_version?: number | null;
  signal_spark_version?: number | null;
  refine_refined_idea_version?: number | null;
  evidence_refined_idea_version?: number | null;
  launch_refined_idea_version?: number | null;
  signal_refined_idea_version?: number | null;
  launch_edited_doc_version?: number | null;
  refine_is_stale?: boolean;
  evidence_is_stale?: boolean;
  launch_is_stale?: boolean;
  signal_is_stale?: boolean;
  refine_stale_reasons?: string[];
  evidence_stale_reasons?: string[];
  launch_stale_reasons?: string[];
  signal_stale_reasons?: string[];
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
 * user's answer and the message ID that carries that answer. Retained for
 * API/history shapes; the Stack B clarifying wizard that consumed this was
 * removed in Part 2 PR-3b.
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
  /** 1-based question number as displayed globally in the thread. */
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
    /** Universal / chat attachment refs for history chips. */
    attachments?: Array<{
      id: string;
      filename: string;
      content_kind: string;
    }>;
    /** Durable turn marker (running | done | failed). */
    turn_status?: "running" | "done" | "failed" | string;
    turn_id?: string;
  } | null;
  /** Structured tool_call / tool_result payload (universal chat agent shape). */
  tool_payload?: Record<string, unknown> | null;
  parent_message_id?: string | null;
  sibling_index?: number;
  sibling_count?: number;
  created_at: string;
}

/** Source chip metadata from get_research_context tool_result. */
export interface ResearchSubagentSourceRef {
  marker_id: string;
  source_title: string;
  source_url: string | null;
  source_domain: string | null;
}

/** tool_payload.result for ask_refine_agent. */
export interface RefineMcqOption {
  index: number;
  label: string;
}

export interface RefineSubagentToolResult {
  assistant_text: string;
  refined_idea_patch: Record<string, unknown> | null;
  has_pending_mcq: boolean;
  log_entry: string | null;
  /** Present when has_pending_mcq — displayed in the rail question card. */
  mcq_question: string | null;
  mcq_options: RefineMcqOption[];
  mcq_answered_question_id: string | null;
  /** Schema default is "multiple"; single submits on one click. */
  mcq_selection_mode: "single" | "multiple";
}

/** tool_payload.result for get_research_context (master-native research). */
export interface ResearchContextToolResult {
  available: boolean;
  findings_digest: string;
  sources: Array<{
    id: string;
    title: string;
    url: string | null;
    domain: string | null;
  }>;
  source_refs: ResearchSubagentSourceRef[];
}

export type SubagentToolName = "ask_refine_agent";

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
  | { kind: "limitation"; value: string }
  | { kind: "url"; value: string };

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
  /** Ordered rows for this turn (user → tool_call/tool_result → assistant). */
  messages: ChatHistoryMessage[];
  thread_id: string;
}

/** `done` SSE frame from POST /chat/universal/stream. */
export interface UniversalChatStreamDone {
  assistant_message_id: string;
  thread_id: string;
  user_message_id: string;
}

export type UniversalSubagentName = "refine" | "research";

export interface UniversalChatMessagesResponse {
  thread_id: string | null;
  experiment_id: string;
  active_leaf_message_id: string | null;
  messages: ChatHistoryMessage[];
  in_progress_turn_id?: string | null;
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

/** Mirrors backend `InsightProgress` on AnalyticsResponse (snake_case). */
export interface InsightProgress {
  views_current: number;
  views_target: number;
  signups_current: number;
  signups_target: number;
  days_current: number;
  days_target: number;
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
  publish_number?: number | null;
  total_publishes?: number;
  insight_threshold_met: boolean;
  insight_progress: InsightProgress;
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

/** Frozen chat attachment on the original idea (GET experiment detail). */
export interface OriginFrozenAttachment {
  id: string;
  original_filename: string;
  content_kind: string;
  media_type: string | null;
  created_at: string;
}

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

export type IdeaTheme = "violet" | "pink" | "green" | "orange";

export interface CaptureIdeaResponse {
  experiment_id: string;
  original_idea: string;
  original_idea_captured_at: string;
  idea_theme: IdeaTheme;
  frozen_attachments: Array<{
    id: string;
    original_filename: string;
    content_kind: string;
  }>;
  user_message_id: string;
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
