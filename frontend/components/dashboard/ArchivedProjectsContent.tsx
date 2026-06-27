"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArchiveRestore, ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { listExperiments, unarchiveExperiment, ApiError } from "@/lib/api";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { formatRelativeTime } from "@/lib/format-time";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import type { ExperimentSummary } from "@/lib/types";
import { DeleteProjectDialog } from "@/components/experiment/DeleteProjectDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "./StatusBadge";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

export function ArchivedProjectsContent() {
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ExperimentSummary | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchArchived = useCallback(async () => {
    try {
      const experiments = await listExperiments({ archived: true });
      setLoadState({ status: "success", experiments });
    } catch (err) {
      setLoadState({
        status: "error",
        message:
          err instanceof ApiError
            ? "Could not load archived projects. Please try again."
            : "Could not load archived projects. Please try again.",
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
      setActionError("Could not restore project. Please try again.");
    } finally {
      setRestoringId(null);
    }
  }

  if (loadState.status === "loading") {
    return (
      <div className="p-4 sm:p-6">
        <div className="fv-skeleton mb-8 h-10 w-56 rounded-lg" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="fv-skeleton h-40 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex items-center justify-center p-6 py-20">
        <ErrorBanner message={loadState.message} className="max-w-md" />
      </div>
    );
  }

  const { experiments } = loadState;

  return (
    <div className="p-4 sm:p-6">
      <PageHeader
        title="Archived projects"
        description="Projects you've archived are stored here. Restore any project to continue working on it."
        actions={
          <Link
            href="/"
            className="fv-btn-ghost inline-flex items-center gap-2 px-4 py-2 text-sm no-underline"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to projects
          </Link>
        }
      />

      {actionError && (
        <ErrorBanner
          message={actionError}
          onDismiss={() => setActionError(null)}
          className="mb-4"
        />
      )}

      {experiments.length === 0 ? (
        <EmptyState
          icon={<ArchiveRestore className="h-7 w-7 text-[var(--fv-text-muted)]" />}
          title="No archived projects"
          description="When you archive a project, it will appear here. Archived projects are hidden from your main dashboard and sidebar."
          action={
            <Link href="/" className="fv-btn-ghost px-4 py-2 text-sm no-underline">
              Go to active projects
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {experiments.map((experiment) => {
            const name = getExperimentDisplayName(experiment);
            const isRestoring = restoringId === experiment.id;

            return (
              <div key={experiment.id} className="fv-project-card flex flex-col">
                <button
                  type="button"
                  onClick={() => router.push(`/experiment/${experiment.id}`)}
                  className="flex-1 text-left"
                >
                  <div className="mb-3 flex items-start justify-between gap-2">
                    <h3 className="truncate text-base font-semibold text-[var(--fv-text)]">
                      {name}
                    </h3>
                    <StatusBadge status={experiment.status} />
                  </div>
                  <p className="line-clamp-2 text-sm leading-relaxed text-[var(--fv-text-muted)]">
                    {experiment.raw_idea?.trim() ?? ""}
                  </p>
                  <p className="mt-3 text-xs text-[var(--fv-text-dim)]">
                    Archived {formatRelativeTime(experiment.updated_at)}
                  </p>
                </button>
                <div className="mt-4 flex gap-2 border-t border-[var(--fv-border)] pt-3">
                  <button
                    type="button"
                    onClick={() => void handleRestore(experiment.id)}
                    disabled={isRestoring}
                    className="fv-btn-ghost inline-flex flex-1 items-center justify-center gap-2 px-3 py-2 text-sm disabled:opacity-50"
                  >
                    {isRestoring ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ArchiveRestore className="h-4 w-4" />
                    )}
                    Restore
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(experiment)}
                    className="fv-btn-ghost inline-flex items-center justify-center gap-2 px-3 py-2 text-sm text-[var(--fv-text-muted)] hover:text-[var(--fv-danger)]"
                    aria-label={`Delete ${name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {deleteTarget && (
        <DeleteProjectDialog
          experimentId={deleteTarget.id}
          projectName={getExperimentDisplayName(deleteTarget)}
          open={deleteTarget !== null}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => void fetchArchived()}
          redirectTo="/archived"
        />
      )}
    </div>
  );
}
