"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Archive, Lightbulb, Plus, Sparkles } from "lucide-react";
import { listExperiments, ApiError } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";
import { ProjectCard } from "./ProjectCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { PageHeader } from "@/components/ui/PageHeader";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

function ProjectGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="fv-skeleton h-52 rounded-2xl" />
      ))}
    </div>
  );
}

export function DashboardContent() {
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  const fetchExperiments = useCallback(async () => {
    try {
      const experiments = await listExperiments();
      setLoadState({ status: "success", experiments });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        return;
      }
      if (err instanceof ApiError) {
        setLoadState({
          status: "error",
          message: "Could not load projects. Please try again.",
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
    return (
      <div className="p-4 sm:p-6">
        <div className="fv-skeleton mb-8 h-10 w-48 rounded-lg" />
        <ProjectGridSkeleton />
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

  if (experiments.length === 0) {
    return (
      <EmptyState
        icon={<Lightbulb className="h-7 w-7 text-[var(--fv-accent)]" />}
        title="No projects yet"
        description="Start your first validation — describe an idea and Fivvle will research the market, generate a landing page, and measure real interest."
        action={
          <Link
            href="/new"
            className="fv-btn-primary inline-flex items-center gap-2 px-6 py-2.5 text-sm no-underline"
          >
            <Sparkles className="h-4 w-4" />
            Create your first project
          </Link>
        }
      />
    );
  }

  return (
    <div className="p-4 sm:p-6">
      <PageHeader
        title="Your projects"
        description="Track validation progress across research, landing pages, and behavioral signal."
        actions={
          <Link
            href="/new"
            className="fv-btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm no-underline"
          >
            <Plus className="h-4 w-4" />
            New project
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {experiments.map((experiment) => (
          <ProjectCard
            key={experiment.id}
            experiment={experiment}
            onClick={() => router.push(`/experiment/${experiment.id}`)}
          />
        ))}

        <Link
          href="/new"
          className="fv-project-card fv-project-card-add no-underline"
        >
          <div className="flex flex-col items-center gap-2 text-[var(--fv-text-muted)]">
            <Plus className="h-8 w-8" />
            <span className="text-sm font-medium">New project</span>
          </div>
        </Link>
      </div>

      <div className="mt-8 border-t border-[var(--fv-border)] pt-6">
        <Link
          href="/archived"
          className="inline-flex items-center gap-2 text-sm text-[var(--fv-text-muted)] no-underline transition-colors hover:text-[var(--fv-text)]"
        >
          <Archive className="h-4 w-4" />
          View archived projects
        </Link>
      </div>
    </div>
  );
}
