import type { Experiment, NodePosition, SatelliteNodeId } from "@/lib/types";

export type PhaseRevealState = {
  isVisible: boolean;
  /**
   * What the founder still has to do. Only surfaced when something tries to open
   * a phase that has not been revealed (a stale `?act=` deep link, or the chat
   * agent navigating ahead) — a hidden node cannot be clicked.
   */
  requirement?: string;
};

/** True once write-once original_idea has been captured (PR1/PR2). */
export function experimentHasOriginalIdea(experiment: Experiment): boolean {
  if (experiment.has_original_idea === true) return true;
  if (experiment.has_original_idea === false) return false;
  return Boolean(experiment.original_idea?.trim());
}

/**
 * Launch is done when the landing page went public. `live_at` is the durable
 * signal: status can leave LANDING_LIVE (re-finalizing refine, insight
 * generation) while the page stays live.
 */
export function launchIsComplete(experiment: Experiment): boolean {
  return (
    experiment.landing_page_live_at != null ||
    LANDING_LIVE_OR_LATER.has(experiment.status)
  );
}

/**
 * Evidence is done when a validation report exists. RESEARCH_FAILED is not in
 * RESEARCH_READY_OR_LATER, so a failed run does not count as complete.
 */
export function evidenceIsComplete(experiment: Experiment): boolean {
  return (
    experiment.validation_report != null ||
    (experiment.evidence_atom_count ?? 0) > 0 ||
    RESEARCH_READY_OR_LATER.has(experiment.status) ||
    launchIsComplete(experiment)
  );
}

/**
 * Refine is done only when the founder explicitly said so — never inferred from
 * a populated refined_idea (which the Refiner writes on most turns) or from turn
 * count. The evidence fallback keeps pre-existing experiments coherent: rows
 * that already have a report predate the stamp, and their phases must stay
 * reachable.
 */
export function refineIsComplete(experiment: Experiment): boolean {
  return (
    experiment.refine_completed_at != null || evidenceIsComplete(experiment)
  );
}

/**
 * Progressive reveal for canvas satellites. A phase node mounts only once the
 * previous phase is complete — there is no locked state, because an unreachable
 * phase simply is not on the canvas yet.
 *
 * Every signal is durable (an explicit stamp, or a persisted report / live
 * page), so a revealed phase can never disappear on the next status change.
 */
export function getPhaseRevealState(
  nodeId: string,
  experiment: Experiment,
): PhaseRevealState {
  // The origin slot is not a phase: it holds the dormant capture prompt before
  // capture and the sealed artifact after, so it is always on the canvas.
  if (nodeId === "spark" || nodeId === "core") return { isVisible: true };

  if (!experimentHasOriginalIdea(experiment)) {
    return {
      isVisible: false,
      requirement: "Describe your idea in chat to start the experiment.",
    };
  }

  switch (nodeId) {
    case "refine":
    case "resources":
      return { isVisible: true };

    case "evidence":
      return refineIsComplete(experiment)
        ? { isVisible: true }
        : {
            isVisible: false,
            requirement: "Finish refining to unlock Evidence.",
          };

    case "launch":
      return evidenceIsComplete(experiment)
        ? { isVisible: true }
        : {
            isVisible: false,
            requirement: "Complete Evidence research to unlock Launch.",
          };

    case "signal":
      return launchIsComplete(experiment)
        ? { isVisible: true }
        : {
            isVisible: false,
            requirement: "Publish your Launch page to unlock Signal.",
          };

    default:
      return { isVisible: true };
  }
}

export function isPhaseNodeVisible(
  nodeId: string,
  experiment: Experiment,
): boolean {
  return getPhaseRevealState(nodeId, experiment).isVisible;
}

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
  "ARCHIVED",
]);

const LANDING_LIVE_OR_LATER = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
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
