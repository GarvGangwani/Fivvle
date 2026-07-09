"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listExperiments, unarchiveExperiment, ApiError } from "@/lib/api";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import type { ExperimentSummary } from "@/lib/types";
import { DeleteProjectDialog } from "@/components/experiment/DeleteProjectDialog";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { ProjectCard } from "./ProjectCard";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

export function ArchivedProjectsContent() {
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ExperimentSummary | null>(
    null,
  );
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchArchived = useCallback(async () => {
    try {
      const experiments = await listExperiments({ archived: true });
      setLoadState({ status: "success", experiments });
    } catch {
      setLoadState({
        status: "error",
        message: "Could not load archived experiments. Please try again.",
      });
    }
  }, []);

  useEffect(() => {
    void fetchArchived();
  }, [fetchArchived]);

  useEffect(() => {
    const onChanged = () => {
      void fetchArchived();
    };
    window.addEventListener("fivvle:experiments-changed", onChanged);
    return () => window.removeEventListener("fivvle:experiments-changed", onChanged);
  }, [fetchArchived]);

  async function handleRestore(experimentId: string) {
    setRestoringId(experimentId);
    setActionError(null);
    try {
      await unarchiveExperiment(experimentId);
      notifyExperimentsChanged();
      await fetchArchived();
    } catch {
      setActionError("Could not restore experiment. Please try again.");
    } finally {
      setRestoringId(null);
    }
  }

  if (loadState.status === "loading") {
    return (
      <div className="py-8">
        <div className="mb-8 h-10 w-72 animate-pulse bg-surface-elevated motion-reduce:animate-none" />
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-64 animate-pulse bg-surface-elevated motion-reduce:animate-none"
            />
          ))}
        </div>
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex items-center justify-center py-20">
        <p
          role="alert"
          className="border-2 border-status-critical bg-surface-card px-6 py-4 font-body-md text-body-md text-status-critical"
        >
          {loadState.message}
        </p>
      </div>
    );
  }

  const { experiments } = loadState;

  return (
    <div className="py-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-display-lg uppercase text-ink-primary">
            ARCHIVED EXPERIMENTS
          </h1>
          <p className="mt-2 font-body-md text-body-md text-ink-secondary">
            Restore any archived validation to continue working on it.
          </p>
        </div>
        <Link
          href="/"
          className={`${marketingButtonClass} inline-flex shrink-0 border-2 border-border-master bg-surface-card px-6 py-3 font-label-md text-label-md uppercase text-ink-primary no-underline`}
        >
          ← BACK TO EXPERIMENTS
        </Link>
      </div>

      {actionError ? (
        <p
          role="alert"
          className="mb-6 border-2 border-status-critical bg-surface-card px-4 py-3 font-body-md text-body-md text-status-critical"
        >
          {actionError}
        </p>
      ) : null}

      {experiments.length === 0 ? (
        <div className="border-2 border-border-master bg-surface-card p-10 text-center shadow-brutal-md">
          <p className="font-headline text-headline-md text-ink-primary">
            No archived experiments
          </p>
          <p className="mt-2 font-body-md text-body-md text-ink-secondary">
            When you archive a validation, it will appear here.
          </p>
          <Link
            href="/"
            className="mt-6 inline-block font-label-md text-label-md uppercase text-brand-primary no-underline hover:underline"
          >
            Go to active experiments
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {experiments.map((experiment) => {
            const name = getExperimentDisplayName(experiment);
            const isRestoring = restoringId === experiment.id;

            return (
              <div key={experiment.id} className="flex flex-col gap-3">
                <ProjectCard experiment={experiment} archived />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void handleRestore(experiment.id)}
                    disabled={isRestoring}
                    className={`${marketingButtonClass} flex-1 bg-surface-card px-4 py-2 font-label-md text-label-md uppercase text-ink-primary disabled:opacity-60`}
                  >
                    {isRestoring ? "RESTORING…" : "RESTORE"}
                  </button>
                  <button
                    type="button"
                    onClick={() => router.push(`/experiment/${experiment.id}`)}
                    className={`${marketingButtonClass} bg-surface-card px-4 py-2 font-label-md text-label-md uppercase text-ink-primary`}
                  >
                    OPEN
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(experiment)}
                    className={`${marketingButtonClass} bg-surface-card px-4 py-2 font-label-md text-label-md uppercase text-status-critical`}
                    aria-label={`Delete ${name}`}
                  >
                    DELETE
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {deleteTarget ? (
        <DeleteProjectDialog
          experimentId={deleteTarget.id}
          projectName={getExperimentDisplayName(deleteTarget)}
          open={deleteTarget !== null}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => void fetchArchived()}
          redirectTo="/archived"
        />
      ) : null}
    </div>
  );
}
