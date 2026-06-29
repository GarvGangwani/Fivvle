/**
 * Paywall session flags and copy — pricing amounts live in pricing.ts.
 */

export { INSIGHT_PAYWALL_CREDITS, METRICS_PAYWALL_CREDITS, VALIDATION_PAYWALL_CREDITS } from "@/lib/pricing";

export const VALIDATION_PAYWALL_INCLUDES = [
  {
    id: "research",
    label: "Research",
    description: "Multi-source market research on your idea",
  },
  {
    id: "report",
    label: "Report",
    description: "Structured validation report with citations",
  },
  {
    id: "landing-page",
    label: "Landing Page",
    description: "Tracked waitlist page to measure demand",
  },
] as const;

export const METRICS_PAYWALL_INCLUDES = [
  {
    id: "traffic",
    label: "Traffic & signups",
    description: "Live page views and waitlist conversion totals",
  },
  {
    id: "sources",
    label: "Source breakdown",
    description: "See which channels drive views and signups",
  },
  {
    id: "locations",
    label: "Signup locations",
    description: "Geographic signal from waitlist signups",
  },
] as const;

export const INSIGHT_PAYWALL_INCLUDES = [
  {
    id: "synthesis",
    label: "Cognitive + behavioral synthesis",
    description: "Combines your research report with live landing page data",
  },
  {
    id: "recommendation",
    label: "Proceed / iterate / pivot / kill",
    description: "Clear AI recommendation with rationale",
  },
  {
    id: "takeaways",
    label: "Key takeaways",
    description: "Actionable findings tied to research and metrics",
  },
] as const;

const METRICS_UNLOCK_STORAGE_KEY = "fivvle_metrics_unlocked_v1";
const INSIGHT_UNLOCK_STORAGE_KEY = "fivvle_insight_unlocked_v1";

function readUnlockedIds(key: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((id): id is string => typeof id === "string"));
  } catch {
    return new Set();
  }
}

function writeUnlockedIds(key: string, ids: Set<string>): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(key, JSON.stringify([...ids]));
}

export function isMetricsAnalysisUnlocked(experimentId: string): boolean {
  return readUnlockedIds(METRICS_UNLOCK_STORAGE_KEY).has(experimentId);
}

export function unlockMetricsAnalysis(experimentId: string): void {
  const ids = readUnlockedIds(METRICS_UNLOCK_STORAGE_KEY);
  ids.add(experimentId);
  writeUnlockedIds(METRICS_UNLOCK_STORAGE_KEY, ids);
}

export function isInsightUnlocked(experimentId: string): boolean {
  return readUnlockedIds(INSIGHT_UNLOCK_STORAGE_KEY).has(experimentId);
}

export function unlockInsight(experimentId: string): void {
  const ids = readUnlockedIds(INSIGHT_UNLOCK_STORAGE_KEY);
  ids.add(experimentId);
  writeUnlockedIds(INSIGHT_UNLOCK_STORAGE_KEY, ids);
}
