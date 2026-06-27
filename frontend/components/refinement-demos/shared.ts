/** Shared sample idea for all refinement UI demos (Mewwly-style dating app). */

export const SAMPLE_PITCH =
  "A blind dating app that matches people weekly using behavioral psychology archetypes — Art of Seduction and Enneagram — instead of photos.";

export const SAMPLE_AUDIENCE_OPTIONS = [
  "Singles 25–35 in cities",
  "Burned out on swipe apps",
  "Want depth over volume",
  "Privacy-conscious daters",
] as const;

export const SAMPLE_PAIN_OPTIONS = [
  "Superficiality of photo-first apps",
  "Decision fatigue from endless swiping",
  "Ghosting after shallow matches",
  "No compatibility beyond looks",
] as const;

export const SAMPLE_REFINED = {
  oneLiner:
    "Weekly psych-matched blind dates for swipe-fatigued singles who want chemistry without the photo lottery.",
  audience:
    "Urban singles 25–35 who deleted Hinge twice and crave one intentional match per week.",
  value:
    "One curated match per week based on personality archetypes — less noise, more real connection.",
  risk: "Users may not trust blind matching without photos at first.",
  test: "Landing page waitlist + source-tagged shares on Reddit and TikTok.",
} as const;

export interface DemoConcept {
  id: string;
  title: string;
  subtitle: string;
}

export const DEMO_CONCEPTS: DemoConcept[] = [
  {
    id: "refinement-ascent",
    title: "Refinement Ascent",
    subtitle: "Editorial magazine arc — live in Refine tab",
  },
  {
    id: "refinement-peak",
    title: "Refinement Peak",
    subtitle: "Timeline journey (alternate)",
  },
  {
    id: "quest-map",
    title: "Guided refinement",
    subtitle: "Structured steps with live hypothesis draft",
  },
  {
    id: "idea-stats",
    title: "Idea Stats",
    subtitle: "RPG-style clarity meters that level up",
  },
  {
    id: "blueprint",
    title: "Blueprint Builder",
    subtitle: "Live hypothesis card that fills slot by slot",
  },
  {
    id: "card-draft",
    title: "Card Draft",
    subtitle: "Pick positioning cards each turn",
  },
  {
    id: "pitch-deck",
    title: "Pitch Deck Unlock",
    subtitle: "Slides unlock as you answer",
  },
  {
    id: "evidence-board",
    title: "Evidence Board",
    subtitle: "Pin notes on a detective cork board",
  },
  {
    id: "confidence-duel",
    title: "Confidence Duel",
    subtitle: "Rate certainty; AI stress-tests weak spots",
  },
];
