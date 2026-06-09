const GRAY_STATUSES = new Set(["DRAFT", "REFINING", "REFINED"]);

const BLUE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
  "RESEARCH_READY",
]);

const YELLOW_STATUSES = new Set(["LANDING_GENERATING", "LANDING_DRAFT"]);

const GREEN_STATUSES = new Set(["LANDING_LIVE"]);

const PURPLE_STATUSES = new Set(["INSIGHT_GENERATING", "INSIGHT_READY"]);

const RED_STATUSES = new Set(["RESEARCH_FAILED", "INSIGHT_FAILED"]);

function statusColorClass(status: string): string {
  if (GRAY_STATUSES.has(status)) {
    return "bg-white/10 text-[var(--fv-text-soft)] ring-white/10";
  }
  if (BLUE_STATUSES.has(status)) {
    return "bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]";
  }
  if (YELLOW_STATUSES.has(status)) {
    return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
  }
  if (GREEN_STATUSES.has(status)) {
    return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
  }
  if (PURPLE_STATUSES.has(status)) {
    return "bg-[rgba(168,85,247,0.15)] text-purple-300 ring-[rgba(168,85,247,0.3)]";
  }
  if (RED_STATUSES.has(status)) {
    return "bg-[rgba(239,68,68,0.15)] text-red-300 ring-[rgba(239,68,68,0.3)]";
  }
  return "bg-white/10 text-[var(--fv-text-soft)] ring-white/10";
}

function formatStatusLabel(status: string): string {
  return status
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${statusColorClass(status)}`}
    >
      {formatStatusLabel(status)}
    </span>
  );
}
