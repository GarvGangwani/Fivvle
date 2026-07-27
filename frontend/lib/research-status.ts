/** Shared helpers for research pipeline polling UI. */

export const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

/** Statuses that mean cognitive research finished successfully (report exists). */
export const RESEARCH_SUCCESS_STATUSES = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ARCHIVED",
]);

export function isResearchInProgress(status: string | null | undefined): boolean {
  return status != null && RESEARCH_ACTIVE_STATUSES.has(status);
}

export function isResearchComplete(status: string | null | undefined): boolean {
  return status != null && RESEARCH_SUCCESS_STATUSES.has(status);
}

export function isResearchFailed(status: string | null | undefined): boolean {
  return status === "RESEARCH_FAILED";
}

/** Map API status to PhaseIndicator currentPhase token. */
export function resolveResearchPhase(status: string | null | undefined): string {
  if (!status || status === "RESEARCHING") return "RESEARCHING";
  if (isResearchComplete(status)) return "RESEARCH_READY";
  if (isResearchInProgress(status)) return status;
  if (isResearchFailed(status)) return "RESEARCH_FAILED";
  return "RESEARCHING";
}
