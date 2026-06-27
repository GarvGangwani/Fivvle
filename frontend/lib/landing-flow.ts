/** Experiment statuses where an existing landing page can be viewed in the editor. */

export const LANDING_PAGE_EDITOR_STATUSES = new Set([
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "ANALYZING",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
]);

export function canViewLandingPageEditor(experimentStatus: string): boolean {
  return LANDING_PAGE_EDITOR_STATUSES.has(experimentStatus);
}

/** Blocked only while regenerating or after archive (must match backend). */
const LANDING_PAGE_EDIT_BLOCKED_STATUSES = new Set([
  "ARCHIVED",
  "LANDING_GENERATING",
]);

export function canEditLandingPage(experimentStatus: string): boolean {
  if (LANDING_PAGE_EDIT_BLOCKED_STATUSES.has(experimentStatus)) {
    return false;
  }
  return LANDING_PAGE_EDITOR_STATUSES.has(experimentStatus);
}

export function landingPageEditBlockedReason(status: string): string {
  if (canEditLandingPage(status)) {
    return "";
  }
  if (status === "LANDING_GENERATING") {
    return "Landing page is regenerating. Wait for it to finish, then try again.";
  }
  if (status === "ARCHIVED") {
    return "Archived projects cannot be edited.";
  }
  return "Landing page cannot be edited in the current project stage.";
}
