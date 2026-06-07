"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Lightbulb, Loader2 } from "lucide-react";
import { listExperiments, ApiError } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";
import { DashboardSidebar } from "./DashboardSidebar";
import { ExperimentDetailPanel } from "./ExperimentDetailPanel";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

export function DashboardContent() {
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("e");
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
              : "Could not load experiments. Please try again.",
        });
      } else {
        setLoadState({
          status: "error",
          message: "Could not load experiments. Please try again.",
        });
      }
    }
  }, []);

  useEffect(() => {
    void fetchExperiments();
  }, [fetchExperiments]);

  if (loadState.status === "loading") {
    return (
      <div className="flex h-[calc(100vh-58px)] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex h-[calc(100vh-58px)] items-center justify-center px-6">
        <div className="fv-error max-w-md text-center text-sm">
          {loadState.message}
        </div>
      </div>
    );
  }

  const { experiments } = loadState;
  const effectiveSelectedId =
    selectedId ?? (experiments.length > 0 ? experiments[0].id : null);

  return (
    <div className="flex h-[calc(100vh-58px)]">
      <DashboardSidebar
        experiments={experiments}
        selectedId={effectiveSelectedId}
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8">
        {experiments.length > 1 && (
          <div className="mb-4 md:hidden">
            <label htmlFor="experiment-select" className="sr-only">
              Select experiment
            </label>
            <select
              id="experiment-select"
              value={effectiveSelectedId ?? ""}
              onChange={(e) => {
                window.location.href = `/dashboard?e=${e.target.value}`;
              }}
              className="fv-input w-full px-3 py-2 text-sm"
            >
              {experiments.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {exp.raw_idea.slice(0, 60)}
                </option>
              ))}
            </select>
          </div>
        )}
        {experiments.length === 0 ? (
          <div className="mx-auto flex max-w-md flex-col items-center py-16 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--fv-accent-muted)]">
              <Lightbulb className="h-6 w-6 text-[var(--fv-accent)]" />
            </div>
            <h2 className="text-lg font-semibold text-[var(--fv-text)]">
              No experiments yet
            </h2>
            <p className="mt-2 text-sm text-[var(--fv-text-muted)]">
              Submit your first startup idea to start validating with AI
              research and a live landing page.
            </p>
            <Link
              href="/new"
              className="fv-btn-primary mt-6 px-5 py-2.5 text-sm no-underline"
            >
              Submit your first idea
            </Link>
          </div>
        ) : effectiveSelectedId ? (
          <ExperimentDetailPanel experimentId={effectiveSelectedId} />
        ) : (
          <div className="mx-auto max-w-md py-16 text-center">
            <p className="text-sm text-[var(--fv-text-muted)]">
              Select an experiment from the sidebar to view details.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
