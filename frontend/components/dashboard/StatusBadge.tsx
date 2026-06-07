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
    return "bg-gray-100 text-gray-700 ring-gray-200";
  }
  if (BLUE_STATUSES.has(status)) {
    return "bg-blue-100 text-blue-800 ring-blue-200";
  }
  if (YELLOW_STATUSES.has(status)) {
    return "bg-yellow-100 text-yellow-800 ring-yellow-200";
  }
  if (GREEN_STATUSES.has(status)) {
    return "bg-green-100 text-green-800 ring-green-200";
  }
  if (PURPLE_STATUSES.has(status)) {
    return "bg-purple-100 text-purple-800 ring-purple-200";
  }
  if (RED_STATUSES.has(status)) {
    return "bg-red-100 text-red-800 ring-red-200";
  }
  return "bg-gray-100 text-gray-700 ring-gray-200";
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
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${statusColorClass(status)}`}
    >
      {formatStatusLabel(status)}
    </span>
  );
}
