import {
  SAMPLE_AUDIENCE_OPTIONS,
  SAMPLE_PAIN_OPTIONS,
  SAMPLE_PITCH,
  SAMPLE_REFINED,
} from "../shared";

export type QuestNodeId =
  | "spark"
  | "audience"
  | "problem"
  | "edge"
  | "risks"
  | "test"
  | "lock";

export interface QuestNode {
  id: QuestNodeId;
  label: string;
  shortLabel: string;
  description: string;
  coachTip: string;
}

export const QUEST_NODES: QuestNode[] = [
  {
    id: "spark",
    label: "Idea",
    shortLabel: "Idea",
    description: "Capture the raw idea in your own words.",
    coachTip:
      "Don’t polish yet — messy is fine. We’re looking for who, what changes, and what makes it different.",
  },
  {
    id: "audience",
    label: "Audience",
    shortLabel: "Audience",
    description: "Sharpen who feels this problem most acutely.",
    coachTip:
      "Specific beats broad. “Singles 25–35 who deleted Hinge twice” beats “people who date.”",
  },
  {
    id: "problem",
    label: "Problem",
    shortLabel: "Problem",
    description: "Rank the frustrations you’re solving.",
    coachTip:
      "Clear pain ranking leads to sharper research questions and landing page copy.",
  },
  {
    id: "edge",
    label: "Differentiation",
    shortLabel: "Edge",
    description: "Choose your primary wedge vs existing apps.",
    coachTip:
      "One clear wedge helps research compare you to the right competitors.",
  },
  {
    id: "risks",
    label: "Risks",
    shortLabel: "Risks",
    description: "Name what could kill the idea early.",
    coachTip:
      "Honest risks become research questions — we investigate them directly.",
  },
  {
    id: "test",
    label: "Validation plan",
    shortLabel: "Plan",
    description: "How you’ll validate demand before building.",
    coachTip:
      "Fivvle validates with a landing page and tracked shares. Pick channels you can reach.",
  },
  {
    id: "lock",
    label: "Review & research",
    shortLabel: "Review",
    description: "Review the assembled hypothesis and start research.",
    coachTip:
      "You can return to any completed step to edit before starting research.",
  },
];

export const EDGE_OPTIONS = [
  {
    id: "psych",
    title: "Psychology-first matching",
    body: "Archetypes & behavior over photos.",
  },
  {
    id: "slow",
    title: "Intentional pace",
    body: "One curated match per week — anti-swipe.",
  },
  {
    id: "blind",
    title: "Blind-by-design",
    body: "Photos unlock only after mutual interest.",
  },
  {
    id: "science",
    title: "Framed as science",
    body: "Enneagram + seduction frameworks as the hook.",
  },
] as const;

export const RISK_OPTIONS = [
  "Users won’t trust blind matching without photos",
  "Weekly pace feels too slow for active daters",
  "Psychology framing feels gimmicky vs serious",
  "Hard to reach singles outside major cities",
  "Incumbents copy the mechanic quickly",
] as const;

export const TEST_CHANNELS = [
  { id: "reddit", label: "Reddit communities", tag: "reddit" },
  { id: "tiktok", label: "TikTok / short video", tag: "tiktok" },
  { id: "linkedin", label: "LinkedIn founder circle", tag: "linkedin" },
  { id: "warm", label: "Friends & early believers", tag: "warm" },
  { id: "twitter", label: "X / Twitter thread", tag: "twitter" },
] as const;


export const SPARK_STARTER_CHIPS = [
  "Weekly match instead of endless swipes",
  "Personality test before photos",
  "For people burned out on Hinge",
] as const;

export function buildRefinedSummary(state: QuestFormState) {
  const edge = EDGE_OPTIONS.find((e) => e.id === state.edgeId);
  const topPain = state.rankedPains[0] ?? "Swipe fatigue";
  const channels = state.testChannels
    .map((id) => TEST_CHANNELS.find((c) => c.id === id)?.label)
    .filter(Boolean)
    .join(", ");

  return {
    projectName: state.projectName || "Mewwly",
    oneLiner:
      state.pitch.trim().length > 40
        ? SAMPLE_REFINED.oneLiner
        : "Refine your spark to generate a one-liner.",
    audience:
      [state.audience.join(" · "), state.audienceOther.trim()]
        .filter(Boolean)
        .join(" · ") || SAMPLE_REFINED.audience,
    value: edge
      ? `${edge.title}: ${edge.body}`
      : SAMPLE_REFINED.value,
    pains: state.rankedPains.length
      ? state.rankedPains.join(" → ")
      : topPain,
    risks:
      [...state.risks, state.riskOther.trim()].filter(Boolean).join("; ") ||
      SAMPLE_REFINED.risk,
    testPlan: channels || SAMPLE_REFINED.test,
  };
}

export interface QuestFormState {
  pitch: string;
  audience: string[];
  audienceOther: string;
  rankedPains: string[];
  edgeId: string | null;
  risks: string[];
  riskOther: string;
  testChannels: string[];
  projectName: string;
}

export function createInitialFormState(): QuestFormState {
  return {
    pitch: "",
    audience: [],
    audienceOther: "",
    rankedPains: [],
    edgeId: null,
    risks: [],
    riskOther: "",
    testChannels: [],
    projectName: "",
  };
}

export function needsSparkClarifier(pitch: string): boolean {
  return pitch.trim().length > 0 && pitch.trim().length < 80;
}

export const SPARK_CLARIFIER_PROMPT =
  "In one sentence: who is this for, and what changes for them?";

export const SAMPLE_PITCH_EXPORT = SAMPLE_PITCH;
