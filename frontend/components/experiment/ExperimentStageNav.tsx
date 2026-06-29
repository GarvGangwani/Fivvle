"use client";

import {
  BarChart3,
  FileText,
  Layout,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import type { ExperimentStageId } from "@/lib/experiment-stages";
import {
  EXPERIMENT_STAGES,
  isStageUnlocked,
} from "@/lib/experiment-stages";

const STAGE_ICONS: Record<ExperimentStageId, typeof Lightbulb> = {
  refine: Lightbulb,
  report: FileText,
  landing: Layout,
  metrics: BarChart3,
  insight: Sparkles,
};

interface ExperimentStageNavProps {
  activeStage: ExperimentStageId;
  status: string;
  onStageChange: (stage: ExperimentStageId) => void;
}

export function ExperimentStageNav({
  activeStage,
  status,
  onStageChange,
}: ExperimentStageNavProps) {
  return (
    <nav
      className="mb-2 shrink-0 overflow-x-auto sm:mb-3"
      aria-label="Project stages"
    >
      <div className="fv-experiment-stage-nav flex min-w-max gap-1 rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-1">
        {EXPERIMENT_STAGES.map((stage) => {
          const unlocked = isStageUnlocked(stage.id, status);
          const active = activeStage === stage.id;
          const Icon = STAGE_ICONS[stage.id];

          return (
            <button
              key={stage.id}
              type="button"
              disabled={!unlocked}
              onClick={() => unlocked && onStageChange(stage.id)}
              title={unlocked ? stage.description : "Not available yet"}
              className={`fv-stage-tab ${active ? "fv-stage-tab-active" : ""} ${
                !unlocked ? "fv-stage-tab-locked" : ""
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">{stage.shortLabel}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
