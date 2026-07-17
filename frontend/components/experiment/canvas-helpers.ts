import type { Experiment, NodePosition, SatelliteNodeId } from "@/lib/types";

export type NodeLockState = {
  isLocked: boolean;
  unlockRequirement?: string;
};

const LANDING_PAGE_CREATED = new Set([
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "ARCHIVED",
  "COMPLETED",
]);

function hasRefinedIdeaPayload(experiment: Experiment): boolean {
  if (experiment.refined_idea_current != null) return true;
  const idea = experiment.refined_idea;
  if (idea == null) return false;
  if (typeof idea === "string") return idea.trim().length > 0;
  return Boolean(
    idea.refined_one_liner?.trim() || idea.headline?.trim(),
  );
}

/**
 * Workflow lock for canvas satellites. Spark + Resources are always open.
 * Evidence / Launch / Signal keys on GET /experiments/{id} fields + status.
 */
export function getNodeLockState(
  nodeId: string,
  experiment: Experiment,
): NodeLockState {
  switch (nodeId) {
    case "spark":
    case "resources":
      return { isLocked: false };

    case "refine":
      if ((experiment.current_spark_version ?? 0) < 1) {
        return {
          isLocked: true,
          unlockRequirement:
            "Save your idea in Spark first to unlock Refine.",
        };
      }
      return { isLocked: false };

    case "evidence": {
      const unlocked =
        experiment.status === "REFINED" ||
        REFINED_OR_LATER.has(experiment.status) ||
        hasRefinedIdeaPayload(experiment);
      if (!unlocked) {
        return {
          isLocked: true,
          unlockRequirement:
            "Finalize your refinement to unlock Evidence.",
        };
      }
      return { isLocked: false };
    }

    case "launch": {
      // Canvas detail exposes validation_report summary + evidence_atom_count
      // (no validation_report_id). Status RESEARCH_READY+ also implies evidence ran.
      const hasValidationReport =
        experiment.validation_report != null ||
        (experiment.evidence_atom_count ?? 0) > 0 ||
        RESEARCH_READY_OR_LATER.has(experiment.status);
      if (!hasValidationReport) {
        return {
          isLocked: true,
          unlockRequirement:
            "Complete Evidence research to unlock Launch.",
        };
      }
      return { isLocked: false };
    }

    case "signal": {
      // No landing_page_id on canvas Experiment; LANDING_DRAFT / LIVE (+ later)
      // means a page was generated. landing_page_view_count alone is not enough
      // (can be 0 on a live unused page).
      const hasLandingPage = LANDING_PAGE_CREATED.has(experiment.status);
      if (!hasLandingPage) {
        return {
          isLocked: true,
          unlockRequirement:
            "Deploy your Launch page to unlock Signal.",
        };
      }
      return { isLocked: false };
    }

    default:
      return { isLocked: false };
  }
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
