import type { ExperimentSummary } from "@/lib/types";

export type PillState =
  | "SPARK"
  | "REFINING"
  | "RESEARCHING"
  | "LAUNCHED"
  | "COMPLETE"
  | "CRITICAL"
  | "ARCHIVED";

// Remove jitter once backend exposes real per-act progress — tracked-work.
const STATUS_BASE_PROGRESS: Record<PillState, number> = {
  SPARK: 15,
  REFINING: 35,
  RESEARCHING: 65,
  LAUNCHED: 85,
  COMPLETE: 100,
  CRITICAL: 0,
  ARCHIVED: 100,
};

const ACT_LABELS: Record<PillState, string> = {
  SPARK: "SPARK",
  REFINING: "REFINE",
  RESEARCHING: "EVIDENCE",
  LAUNCHED: "SIGNAL",
  COMPLETE: "VERDICT",
  CRITICAL: "EVIDENCE",
  ARCHIVED: "ARCHIVED",
};

const UNMAPPED_STATUSES = new Set<string>();

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0 || parts[0] === "") return "";
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function mapStatusToPill(status: string): PillState {
  switch (status) {
    case "SPARK":
    case "DRAFT":
      return "SPARK";
    case "REFINING":
    case "REFINED":
      return "REFINING";
    case "RESEARCHING":
    case "RESEARCH_PLANNING":
    case "RESEARCH_SEARCHING":
    case "RESEARCH_READING":
    case "RESEARCH_REFLECTING":
    case "RESEARCH_VOICES":
    case "RESEARCH_SYNTHESIZING":
    case "RESEARCH_READY":
    case "INSIGHT_GENERATING":
      return "RESEARCHING";
    case "LANDING_GENERATING":
    case "LANDING_DRAFT":
    case "LANDING_LIVE":
      return "LAUNCHED";
    case "INSIGHT_READY":
    case "COMPLETE":
      return "COMPLETE";
    case "RESEARCH_FAILED":
    case "INSIGHT_FAILED":
      return "CRITICAL";
    case "ARCHIVED":
      return "ARCHIVED";
    default:
      UNMAPPED_STATUSES.add(status);
      return "SPARK";
  }
}

export function getUnmappedStatuses(): string[] {
  return Array.from(UNMAPPED_STATUSES);
}

export function getActLabel(pill: PillState): string {
  return ACT_LABELS[pill];
}

function hashStringToRange(str: string, min: number, max: number): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  const range = max - min + 1;
  return min + (Math.abs(hash) % range);
}

export function getHardcodedProgressPercent(
  status: string,
  experimentId: string,
): number {
  const pill = mapStatusToPill(status);
  if (pill === "COMPLETE") return 100;
  if (pill === "CRITICAL") return 0;
  if (pill === "ARCHIVED") return 100;

  const base = STATUS_BASE_PROGRESS[pill] ?? 15;
  const jitter = hashStringToRange(experimentId, -8, 8);
  return Math.max(5, Math.min(95, base + jitter));
}

export function getProgressBarFillClass(pill: PillState): string {
  if (pill === "CRITICAL") return "bg-status-critical";
  if (pill === "ARCHIVED") return "bg-ink-tertiary";
  return "bg-brand-primary";
}

export function formatExperimentId(id: string): string {
  const compact = id.replace(/-/g, "").slice(0, 4).toUpperCase();
  return `#EXP-${compact}`;
}

// TODO: enforce title requirement server-side once refinement always produces a title.
export function getExperimentDisplayTitle(experiment: ExperimentSummary): string {
  const title = experiment.name?.trim();
  if (title) return title;
  return `Untitled — #${experiment.id.slice(0, 4).toUpperCase()}`;
}

export function getInsightDataPoint(experiment: ExperimentSummary): string {
  const pill = mapStatusToPill(experiment.status);
  const progress = getHardcodedProgressPercent(
    experiment.status,
    experiment.id,
  );
  const stats = experiment.card_stats;

  if (stats && (stats.page_views > 0 || stats.waitlist_signups > 0)) {
    return `${stats.waitlist_signups} waitlist signups · ${stats.page_views} page views`;
  }

  if (pill === "RESEARCHING") {
    return `${progress}% research complete`;
  }

  if (pill === "LAUNCHED") {
    return `${progress}% signal collection in progress`;
  }

  if (pill === "COMPLETE") {
    return "Verdict ready to review";
  }

  return `${progress}% through ${getActLabel(pill).toLowerCase()} act`;
}

export function countExperimentsThisMonth(
  experiments: ExperimentSummary[],
): number {
  const now = new Date();
  const month = now.getMonth();
  const year = now.getFullYear();
  return experiments.filter((exp) => {
    const created = new Date(exp.created_at);
    return created.getMonth() === month && created.getFullYear() === year;
  }).length;
}

export function sortByUpdatedDesc(
  experiments: ExperimentSummary[],
): ExperimentSummary[] {
  return [...experiments].sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

export function getFirstName(displayName: string | null | undefined): string {
  if (!displayName?.trim()) return "there";
  return displayName.trim().split(/\s+/)[0];
}
