import type { NodePosition, SatelliteNodeId } from "@/lib/types";

export const DEFAULT_POSITIONS: Record<SatelliteNodeId, NodePosition> = {
  spark: { x: -250, y: -430 },
  refine: { x: 250, y: -430 },
  evidence: { x: 500, y: 0 },
  launch: { x: 250, y: 430 },
  signal: { x: -250, y: 430 },
  resources: { x: -500, y: 0 },
};

/** Visual center of the core shell node (w-80 = 320px, ~260px tall). */
export const CORE_NODE_CENTER = { x: 160, y: 130 };

/** Default zoom — core centered; slightly below 1.0 so satellites aren't clipped. */
export const DEFAULT_CANVAS_ZOOM = 0.88;

/** Floor zoom — do not frame tighter than the wider fit-all-nodes view. */
export const MIN_CANVAS_ZOOM = 0.72;

export const EXCLUSION_RADIUS = 220;

export function snapOutOfExclusionZone(pos: { x: number; y: number }): { x: number; y: number } {
  const distance = Math.hypot(pos.x, pos.y);
  if (distance >= EXCLUSION_RADIUS) return pos;

  if (distance === 0) return { x: EXCLUSION_RADIUS, y: 0 };

  const angle = Math.atan2(pos.y, pos.x);
  return {
    x: Math.round((Math.cos(angle) * EXCLUSION_RADIUS) / 40) * 40,
    y: Math.round((Math.sin(angle) * EXCLUSION_RADIUS) / 40) * 40,
  };
}

export function snapToGrid(pos: { x: number; y: number }): { x: number; y: number } {
  return {
    x: Math.round(pos.x / 40) * 40,
    y: Math.round(pos.y / 40) * 40,
  };
}

export function formatCanvasMetric(value: number | null | undefined): string {
  if (value == null) return "—";
  return String(value);
}

const REFINED_OR_LATER = new Set([
  "REFINED",
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_VOICES",
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
  "ARCHIVED",
]);

const RESEARCH_READY_OR_LATER = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "ARCHIVED",
]);

const LANDING_LIVE_OR_LATER = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "ARCHIVED",
]);

export function getPhasesComplete(status: string): number {
  if (status === "SPARK" || status === "DRAFT" || status === "REFINING") return 0;
  if (!REFINED_OR_LATER.has(status)) return 0;
  if (!RESEARCH_READY_OR_LATER.has(status)) return 1;
  if (!LANDING_LIVE_OR_LATER.has(status)) return 2;
  return 3;
}

export function isActRunning(actId: string, status: string): boolean {
  switch (actId) {
    case "spark":
      return status === "SPARK";
    case "refine":
      return status === "REFINING";
    case "evidence":
      return (
        status.startsWith("RESEARCH") &&
        status !== "RESEARCH_READY" &&
        status !== "RESEARCH_FAILED"
      );
    case "launch":
      return status === "LANDING_GENERATING";
    case "signal":
      return status === "INSIGHT_GENERATING";
    default:
      return false;
  }
}
