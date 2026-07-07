/** Landing Page Runtime schema v4 — mirrors backend/app/schemas/landing_page_v2.py */

export type SpacingScale = "xs" | "s" | "m" | "l" | "xl" | "2xl";

export type AccentFamily =
  | "indigo"
  | "emerald"
  | "amber"
  | "rose"
  | "slate"
  | "cyan";

export type CardStyle = "flat" | "elevated" | "outline" | "glass";
export type CtaEmphasis = "subtle" | "moderate" | "bold";

export type BackgroundStyle =
  | "default"
  | "surface"
  | "dark_gradient"
  | "accent_soft"
  | "full_bleed_dark"
  | "muted";

export type AnimationStyle =
  | "none"
  | "fade"
  | "fade_up"
  | "slide_in"
  | "subtle_scale";

export type ComponentType =
  | "HeroSection"
  | "ProblemSection"
  | "ProblemComparison"
  | "StorySection"
  | "FeatureTimeline"
  | "AlternatingFeature"
  | "PhoneMockup"
  | "Statistics"
  | "TrustSection"
  | "Testimonials"
  | "Pricing"
  | "FAQ"
  | "CtaSection"
  | "SplitLayout"
  | "ComparisonCards"
  | "FeatureGrid"
  | "AnimatedTimeline"
  | "BeforeAfter"
  | "FounderLetter"
  | "FeatureReveal"
  | "ImageShowcase"
  | "FooterSection";

export type ComponentVariant =
  | "centered"
  | "split_left"
  | "split_right"
  | "editorial_left"
  | "editorial_right"
  | "cinematic"
  | "minimal"
  | "product_first"
  | "image_first"
  | "sticky_scroll"
  | "stacked"
  | "grid"
  | "asymmetric";

export type VisualElementType =
  | "product_screenshot"
  | "dashboard"
  | "phone_mockup"
  | "illustration"
  | "diagram"
  | "chart"
  | "comparison"
  | "timeline"
  | "cards"
  | "testimonial_card"
  | "logo_strip"
  | "animation_placeholder"
  | "before_after"
  | "none";

export type HeadlineAlignment = "left" | "center" | "right";

export type NarrativeArchetype =
  | "b2b_saas"
  | "consumer_app"
  | "ai_tool"
  | "marketplace"
  | "founder_story"
  | "dating_app"
  | "generic";

export interface NarrativeStageGoal {
  stage_id: string;
  label: string;
  goal: string;
  visitor_feeling: string;
  objection_addressed?: string | null;
}

export interface NarrativeArchitectOutput {
  business_archetype: NarrativeArchetype;
  story_summary: string;
  stages: NarrativeStageGoal[];
  key_objections: string[];
  desired_end_state: string;
  stage_order: string[];
}

export interface GlobalCreativeDirection {
  visual_style: string;
  tone: string;
  pace: string;
  typography: string;
  color_mode: "light" | "dark";
  accent_family: AccentFamily;
  visual_personality: string;
}

export interface SectionCreativeBrief {
  stage_id: string;
  purpose: string;
  emotional_objective: string;
  visual_objective: string;
  emotion: string;
  theme: string;
  layout_intent: string;
  visual_weight: string;
  pacing: string;
  hierarchy: string;
  storytelling_role: string;
  transition_style: string;
  atmosphere: string;
  component_priority: string[];
  spacing: SpacingScale;
  animation: AnimationStyle;
}

export interface CreativeDirectorOutput {
  global_direction: GlobalCreativeDirection;
  section_briefs: SectionCreativeBrief[];
}

export interface VisualElementSpec {
  stage_id: string;
  visual_type: VisualElementType;
  purpose: string;
  prominence: string;
  asset_key?: string | null;
  alt?: string | null;
}

export interface VisualComposerOutput {
  visuals: VisualElementSpec[];
  rhythm_notes: string;
}

export interface SectionCopyItem {
  title?: string | null;
  body?: string | null;
  label?: string | null;
  value?: string | null;
}

export interface SectionMetadata {
  purpose: string;
  emotion: string;
  conversion_goal: string;
  recommended_layout?: string | null;
  recommended_visual?: string | null;
}

export interface ComponentPlanSpec {
  id: string;
  stage_id: string;
  component: ComponentType;
  variant: ComponentVariant;
  background: BackgroundStyle;
  spacing: SpacingScale;
  headline_alignment: HeadlineAlignment;
  visual: VisualElementType;
  visual_asset_key?: string | null;
  animation: AnimationStyle;
  headline?: string | null;
  subheadline?: string | null;
  body?: string | null;
  items: SectionCopyItem[];
  cta_label?: string | null;
  metadata: SectionMetadata;
}

export interface DesignTokenSpec {
  color_mode: "light" | "dark";
  accent_family: AccentFamily;
  card_style: CardStyle;
  cta_emphasis: CtaEmphasis;
}

export interface AssetRefSpec {
  asset_key: string;
  role: string;
  alt: string;
  storytelling_role?: string | null;
  url?: string | null;
}

export interface PipelineArtifacts {
  narrative: NarrativeArchitectOutput;
  creative_director: CreativeDirectorOutput;
  visual_composer: VisualComposerOutput;
}

export interface LandingPageV2Spec {
  schema_version: 4;
  page_goal: "waitlist" | "interest" | "contact";
  pipeline: PipelineArtifacts;
  design_tokens: DesignTokenSpec;
  components: ComponentPlanSpec[];
  asset_refs: AssetRefSpec[];
}

export type LandingPageV2GenerationPhase =
  | "idle"
  | "planning_narrative"
  | "creative_direction"
  | "visual_composition"
  | "component_planning"
  | "ready"
  | "failed";

export interface LandingPageV2GenerationStatus {
  experiment_id: string;
  generation_status: "idle" | "generating" | "ready" | "failed";
  generation_phase: LandingPageV2GenerationPhase;
  error_detail?: string | null;
  spec?: LandingPageV2Spec | null;
  publication_slug?: string | null;
  resolved_assets: Record<string, string>;
}

export interface GenerateLandingPageV2Request {
  page_goal?: "waitlist" | "interest" | "contact";
  regeneration_hint?: string | null;
}

export interface GenerateLandingPageV2Response {
  experiment_id: string;
  generation_status: "generating";
}

export function isRuntimeSpecV4(
  spec: unknown,
): spec is LandingPageV2Spec {
  return (
    typeof spec === "object" &&
    spec !== null &&
    (spec as LandingPageV2Spec).schema_version === 4 &&
    Array.isArray((spec as LandingPageV2Spec).components)
  );
}
