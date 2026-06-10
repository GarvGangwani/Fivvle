"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Lightbulb, Plus } from "lucide-react";
import { listExperiments, ApiError } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format-time";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import type { ExperimentSummary } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

const REPORT_READY_STATUSES = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
]);

const LIVE_METRICS_STATUSES = new Set(["LANDING_LIVE", "INSIGHT_READY", "COMPLETED"]);

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

function ProjectGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="fv-skeleton h-40 rounded-xl" />
      ))}
    </div>
  );
}

function hasReportReady(status: string): boolean {
  return REPORT_READY_STATUSES.has(status);
}

function showLiveMetrics(status: string): boolean {
  return LIVE_METRICS_STATUSES.has(status);
}

export function DashboardContent() {
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  const fetchExperiments = useCallback(async () => {
    try {
      const experiments = await listExperiments();
      setLoadState({ status: "success", experiments });
    } catch (err) {
      if (err instanceof ApiError) {
        setLoadState({
          status: "error",
          message:
            err.status === 401
              ? "Session expired. Please log in again."
              : "Could not load projects. Please try again.",
        });
      } else {
        setLoadState({
          status: "error",
          message: "Could not load projects. Please try again.",
        });
      }
    }
  }, []);

  useEffect(() => {
    void fetchExperiments();
  }, [fetchExperiments]);

  if (loadState.status === "loading") {
    return <ProjectGridSkeleton />;
  }

  if (loadState.status === "error") {
    return (
      <div className="flex items-center justify-center px-6 py-16">
        <div className="fv-error max-w-md text-center text-sm">
          {loadState.message}
        </div>
      </div>
    );
  }

  const { experiments } = loadState;

  if (experiments.length === 0) {
    return (
      <div className="fv-fade-up mx-auto flex max-w-md flex-col items-center px-6 py-16 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--fv-accent-muted)]">
          <Lightbulb className="h-6 w-6 text-[var(--fv-accent)]" />
        </div>
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">
          No projects yet
        </h2>
        <p className="mt-2 text-sm text-[var(--fv-text-muted)]">
          Start your first validation — describe an idea and Fivvle will research
          the market for you.
        </p>
        <Link
          href="/new"
          className="fv-btn-primary mt-6 px-5 py-2.5 text-sm no-underline"
        >
          Create your first project
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
      {experiments.map((experiment) => {
        const name = getExperimentDisplayName(experiment);
        const hasReport = hasReportReady(experiment.status);
        const hasMetrics = showLiveMetrics(experiment.status);

        return (
          <button
            key={experiment.id}
            type="button"
            onClick={() => router.push(`/experiment/${experiment.id}`)}
            className="fv-card fv-card-hover space-y-3 p-5 text-left"
          >
            <div className="flex items-center justify-between gap-2">
              <h3 className="truncate text-[15px] font-semibold text-[var(--fv-text)]">
                {name}
              </h3>
              <StatusBadge status={experiment.status} />
            </div>
            <p className="line-clamp-2 text-[13px] text-[var(--fv-text-muted)]">
              {experiment.raw_idea.trim()}
            </p>
            <div className="flex flex-wrap items-center gap-2 text-[12px] text-[var(--fv-text-dim)]">
              <span>{formatRelativeTime(experiment.updated_at)}</span>
              {hasReport && <span>• Report ready</span>}
              {hasMetrics && <span>• Live</span>}
            </div>
          </button>
        );
      })}

      <Link
        href="/new"
        className="fv-card flex cursor-pointer items-center justify-center border-dashed p-8 no-underline transition-colors hover:border-[var(--fv-accent)]/40"
      >
        <Plus className="h-6 w-6 text-[var(--fv-text-muted)]" />
      </Link>
    </div>
  );
}
