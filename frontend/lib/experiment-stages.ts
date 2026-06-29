/** Maps experiment status to the founder journey stage for UI navigation. */

export type ExperimentStageId =
  | "refine"
  | "report"
  | "landing"
  | "metrics"
  | "insight";

export interface ExperimentStage {
  id: ExperimentStageId;
  label: string;
  shortLabel: string;
  description: string;
}

export const EXPERIMENT_STAGES: ExperimentStage[] = [
  {
    id: "refine",
    label: "Refine idea",
    shortLabel: "Refine",
    description: "Shape your idea through conversation before research runs.",
  },
  {
    id: "report",
    label: "Validation report",
    shortLabel: "Report",
    description: "Evidence-backed market research and recommendation.",
  },
  {
    id: "landing",
    label: "Landing page",
    shortLabel: "Landing",
    description: "Generate and customize your validation landing page.",
  },
  {
    id: "metrics",
    label: "Live metrics",
    shortLabel: "Metrics",
    description: "Page views, signups, and conversion by source.",
  },
  {
    id: "insight",
    label: "Insight & decision",
    shortLabel: "Insight",
    description: "Combined cognitive + behavioral signal and next steps.",
  },
];

const REPORT_UNLOCKED = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const LANDING_UNLOCKED = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const METRICS_UNLOCKED = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const INSIGHT_UNLOCKED = new Set([
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

/** Experiment statuses while the research engine pipeline is running. */
export const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

/** Poll experiment detail while background jobs are in flight. */
export function shouldPollExperimentStatus(status: string): boolean {
  return (
    RESEARCH_ACTIVE_STATUSES.has(status) ||
    status === "LANDING_GENERATING" ||
    status === "INSIGHT_GENERATING"
  );
}

export function pollIntervalForStatus(status: string): number {
  if (status === "LANDING_GENERATING") return 5000;
  return 3000;
}

/** Show stage tabs once refinement is complete (Chapter 3) or a report exists. */
export function shouldShowExperimentStageNav(
  status: string,
  hasValidationReport: boolean,
  refinementFinalized = false,
): boolean {
  if (hasValidationReport || refinementFinalized) return true;
  if (status === "REFINED") return true;
  if (RESEARCH_ACTIVE_STATUSES.has(status) || status === "RESEARCH_FAILED") {
    return true;
  }
  return isStageUnlocked("report", status);
}

export function isStageUnlocked(
  stage: ExperimentStageId,
  status: string,
): boolean {
  switch (stage) {
    case "refine":
      return true;
    case "report":
      return REPORT_UNLOCKED.has(status);
    case "landing":
      return LANDING_UNLOCKED.has(status);
    case "metrics":
      return METRICS_UNLOCKED.has(status);
    case "insight":
      return INSIGHT_UNLOCKED.has(status);
    default:
      return false;
  }
}

export function defaultStageForStatus(status: string): ExperimentStageId {
  if (INSIGHT_UNLOCKED.has(status)) return "insight";
  if (METRICS_UNLOCKED.has(status)) return "metrics";
  if (status === "LANDING_DRAFT" || status === "LANDING_LIVE") return "landing";
  if (REPORT_UNLOCKED.has(status)) return "report";
  if (status.startsWith("RESEARCH") && status !== "RESEARCH_READY") return "refine";
  return "refine";
}

export function stageProgressIndex(stage: ExperimentStageId): number {
  return EXPERIMENT_STAGES.findIndex((s) => s.id === stage);
}
