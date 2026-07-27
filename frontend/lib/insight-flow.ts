/** When the insight paywall prompt should appear on the Insight stage. */

const INSIGHT_VIEW_STATUSES = new Set([
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ARCHIVED",
]);

/** Statuses that may start or retry insight generation. */
export const INSIGHT_GENERATION_ALLOWED_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
]);

export function canRequestInsightGeneration(experimentStatus: string): boolean {
  return INSIGHT_GENERATION_ALLOWED_STATUSES.has(experimentStatus);
}

export function isInsightGenerationInProgress(experimentStatus: string): boolean {
  return experimentStatus === "INSIGHT_GENERATING";
}

export function shouldShowInsightUnlockPrompt(
  experimentStatus: string,
  insightUnlocked: boolean,
): boolean {
  if (insightUnlocked) return false;
  return INSIGHT_VIEW_STATUSES.has(experimentStatus);
}
