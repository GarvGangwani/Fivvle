"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChevronDown, Lightbulb } from "lucide-react";
import { listExperiments, renameExperiment, ApiError } from "@/lib/api";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import type { ExperimentSummary } from "@/lib/types";
import { DashboardSidebar } from "./DashboardSidebar";
import { ExperimentDetailPanel } from "./ExperimentDetailPanel";

const EMPTY_STATE_SUGGESTIONS = [
  { label: "SaaS idea", href: "/new" },
  { label: "Consumer app", href: "/new" },
  { label: "Marketplace", href: "/new" },
] as const;

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

function DashboardLoadingSkeleton() {
  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <aside
        className="hidden w-[260px] shrink-0 border-r p-4 md:block"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <div className="fv-skeleton h-10 rounded-xl" />
        <div className="mb-3 mt-5 px-1">
          <div className="fv-skeleton h-3 w-16 rounded" />
        </div>
        <div className="space-y-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="fv-skeleton h-14 rounded-lg" />
          ))}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8">
        <div className="fv-skeleton mb-4 h-8 w-48 rounded" />
        <div className="fv-skeleton h-64 rounded-xl" />
      </main>
    </div>
  );
}

interface ExperimentNameHeaderProps {
  experiment: ExperimentSummary;
  onRenamed: () => void;
}

function ExperimentNameHeader({
  experiment,
  onRenamed,
}: ExperimentNameHeaderProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const displayName = getExperimentDisplayName(experiment);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  function startEditing() {
    setDraft(experiment.name?.trim() ?? "");
    setError(null);
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
    setDraft("");
    setError(null);
  }

  async function saveName() {
    const trimmed = draft.trim();
    if (!trimmed) {
      setError("Name cannot be empty.");
      return;
    }
    if (trimmed === experiment.name?.trim()) {
      cancelEditing();
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await renameExperiment(experiment.id, trimmed);
      setEditing(false);
      onRenamed();
    } catch {
      setError("Could not save name. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void saveName();
    } else if (event.key === "Escape") {
      cancelEditing();
    }
  }

  return (
    <div className="mb-6">
      {editing ? (
        <div>
          <input
            ref={inputRef}
            type="text"
            value={draft}
            maxLength={100}
            disabled={saving}
            onChange={(event) => setDraft(event.target.value)}
            onBlur={() => void saveName()}
            onKeyDown={handleKeyDown}
            className="w-full max-w-xl rounded-xl border border-white/[0.12] bg-[var(--fv-surface-2)] px-4 py-2.5 text-xl font-bold text-[var(--fv-text)] outline-none focus:border-[var(--fv-accent)]/50"
            aria-label="Project name"
          />
          {error && <p className="mt-2 text-sm text-red-300">{error}</p>}
        </div>
      ) : (
        <button
          type="button"
          onClick={startEditing}
          className="cursor-pointer text-left text-xl font-bold text-[var(--fv-text)] transition-colors hover:text-[var(--fv-accent)]"
          title="Click to rename"
        >
          {displayName}
        </button>
      )}
    </div>
  );
}

export function DashboardContent() {
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("e");
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  const [nameRefreshKey, setNameRefreshKey] = useState(0);

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
    return <DashboardLoadingSkeleton />;
  }

  if (loadState.status === "error") {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center px-6">
        <div className="fv-error max-w-md text-center text-sm">
          {loadState.message}
        </div>
      </div>
    );
  }

  const { experiments } = loadState;
  const effectiveSelectedId =
    selectedId ?? (experiments.length > 0 ? experiments[0].id : null);
  const selectedExperiment =
    effectiveSelectedId != null
      ? experiments.find((experiment) => experiment.id === effectiveSelectedId)
      : undefined;

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <DashboardSidebar
        experiments={experiments}
        selectedId={effectiveSelectedId}
      />

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden p-4 sm:p-6 md:p-8">
        {experiments.length > 1 && (
          <div className="relative mb-4 md:hidden">
            <label htmlFor="experiment-select" className="sr-only">
              Select experiment
            </label>
            <select
              id="experiment-select"
              value={effectiveSelectedId ?? ""}
              onChange={(e) => {
                window.location.href = `/dashboard?e=${e.target.value}`;
              }}
              className="w-full appearance-none rounded-xl border border-white/[0.08] bg-[var(--fv-surface-2)] px-4 py-3 pr-10 text-sm text-[var(--fv-text)] outline-none"
            >
              {experiments.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {getExperimentDisplayName(exp)}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fv-text-muted)]" />
          </div>
        )}
        {experiments.length === 0 ? (
          <div className="fv-fade-up mx-auto flex max-w-md flex-col items-center py-16 text-center">
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
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {EMPTY_STATE_SUGGESTIONS.map((suggestion) => (
                <Link
                  key={suggestion.label}
                  href={suggestion.href}
                  className="rounded-full border border-white/[0.1] bg-white/[0.03] px-4 py-2 text-[13px] text-[var(--fv-text-soft)] transition-all duration-200 hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5 no-underline"
                >
                  {suggestion.label}
                </Link>
              ))}
            </div>
          </div>
        ) : effectiveSelectedId && selectedExperiment ? (
          <div className="flex min-h-0 flex-1 flex-col">
            <ExperimentNameHeader
              experiment={selectedExperiment}
              onRenamed={() => {
                void fetchExperiments();
                setNameRefreshKey((key) => key + 1);
              }}
            />
            <ExperimentDetailPanel
              experimentId={effectiveSelectedId}
              rawIdea={selectedExperiment.raw_idea}
              nameRefreshKey={nameRefreshKey}
            />
          </div>
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
