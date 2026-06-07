"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Lightbulb } from "lucide-react";
import { listExperiments, ApiError } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";
import { ExperimentCard } from "./ExperimentCard";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

export function DashboardContent() {
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function fetchExperiments() {
      try {
        const experiments = await listExperiments();
        if (!cancelled) {
          setLoadState({ status: "success", experiments });
        }
      } catch (err) {
        if (cancelled) return;
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
    }

    fetchExperiments();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadState.status === "loading") {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-[var(--fv-border)] border-t-[var(--fv-accent)]" />
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="fv-error px-6 py-8 text-center">
        <p className="text-sm">{loadState.message}</p>
      </div>
    );
  }

  if (loadState.experiments.length === 0) {
    return (
      <div className="fv-card flex flex-col items-center border-dashed px-6 py-16 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--fv-accent-muted)]">
          <Lightbulb className="h-6 w-6 text-[var(--fv-accent)]" />
        </div>
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">
          No experiments yet
        </h2>
        <p className="mt-2 max-w-sm text-sm text-[var(--fv-text-muted)]">
          Submit your first startup idea to start validating with AI research and
          a live landing page.
        </p>
        <Link
          href="/new"
          className="fv-btn-primary mt-6 px-5 py-2.5 text-sm no-underline"
        >
          Submit your first idea
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {loadState.experiments.map((experiment) => (
        <ExperimentCard key={experiment.id} experiment={experiment} />
      ))}
    </div>
  );
}
