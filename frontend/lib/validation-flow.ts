/** When the validation paywall + Run validation prompt should appear (after Chapter 3). */

const RESEARCH_PIPELINE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
  "RESEARCH_READY",
  "RESEARCH_FAILED",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "COMPLETED",
]);

export function shouldShowValidationResearchPrompt(
  hasRefinementFinalize: boolean,
  researchStarted: boolean,
  experimentStatus: string | null,
  hasValidationReport: boolean,
): boolean {
  if (!hasRefinementFinalize || hasValidationReport || researchStarted) {
    return false;
  }
  if (
    experimentStatus !== null &&
    RESEARCH_PIPELINE_STATUSES.has(experimentStatus)
  ) {
    return false;
  }
  return experimentStatus === "REFINED";
}
