"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import type { ExperimentSummary } from "@/lib/types";

const VALIDATED_STATUSES = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
]);

const IN_PROGRESS_STATUSES = new Set([
  "DRAFT",
  "REFINING",
  "REFINED",
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

type ExperimentWithRefinement = ExperimentSummary & {
  validation_report?: {
    overall_recommendation?: string | null;
    total_finding_count?: number;
  } | null;
};

interface DashboardSidebarProps {
  experiments: ExperimentWithRefinement[];
  selectedId?: string | null;
}

function getStatusLine(experiment: ExperimentWithRefinement): {
  dotColor: string;
  label: string;
} {
  if (VALIDATED_STATUSES.has(experiment.status)) {
    const score = experiment.validation_report?.total_finding_count;
    return {
      dotColor: "var(--fv-success)",
      label: score != null ? `Score: ${Math.min(100, score * 10)}` : "Validated",
    };
  }
  if (IN_PROGRESS_STATUSES.has(experiment.status)) {
    return { dotColor: "var(--fv-warning)", label: "In progress" };
  }
  return {
    dotColor: "var(--fv-text-dim)",
    label: experiment.status.replace(/_/g, " ").toLowerCase(),
  };
}

export function DashboardSidebar({
  experiments,
  selectedId,
}: DashboardSidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className="hidden w-[260px] shrink-0 flex-col border-r md:flex"
      style={{
        borderColor: "rgba(255,255,255,0.06)",
        height: "calc(100vh - 4rem)",
      }}
    >
      <div className="flex flex-1 flex-col overflow-y-auto p-4">
        <Link href="/new" className="fv-new-idea-btn">
          <Plus className="h-[14px] w-[14px]" />
          New Idea
        </Link>

        <p
          className="mb-3 mt-5 px-1 text-[11px] font-semibold uppercase tracking-[0.1em]"
          style={{ color: "var(--fv-text-dim)" }}
        >
          Recent
        </p>

        <div className="space-y-1">
          {experiments.map((experiment) => {
            const isActive =
              selectedId === experiment.id ||
              pathname === `/experiment/${experiment.id}`;
            const { dotColor, label } = getStatusLine(experiment);

            return (
              <Link
                key={experiment.id}
                href={`/dashboard?e=${experiment.id}`}
                className={`fv-sidebar-item block px-3 py-3 no-underline ${
                  isActive ? "fv-sidebar-item-active" : ""
                }`}
              >
                <p className="text-[13px] font-medium text-fv-text">
                  {getExperimentDisplayName(experiment)}
                </p>
                <div className="mt-1 flex items-center gap-1.5">
                  <span
                    className="h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ background: dotColor }}
                  />
                  <span
                    className="text-[11px]"
                    style={{ color: "var(--fv-text-dim)" }}
                  >
                    {label}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
