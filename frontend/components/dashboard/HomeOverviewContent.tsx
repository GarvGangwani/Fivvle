"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { listExperiments, ApiError } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { ProjectCard } from "./ProjectCard";
import { WorkspaceInsightCard } from "./WorkspaceInsightCard";
import { UsageSidebarCard } from "./UsageSidebarCard";
import {
  countExperimentsThisMonth,
  getFirstName,
  sortByUpdatedDesc,
} from "./dashboard-helpers";
import { DashboardHomeSkeleton } from "./skeletons/DashboardHomeSkeleton";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

export function HomeOverviewContent() {
  const { user } = useAuth();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  const fetchExperiments = useCallback(async () => {
    try {
      const experiments = await listExperiments();
      setLoadState({ status: "success", experiments });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setLoadState({
        status: "error",
        message: "Could not load experiments. Please try again.",
      });
    }
  }, []);

  useEffect(() => {
    void fetchExperiments();
  }, [fetchExperiments]);

  if (loadState.status === "loading") {
    return (
      <div className="px-gutter pb-gutter pt-24">
        <DashboardHomeSkeleton />
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex items-center justify-center px-gutter pb-20 pt-24">
        <p
          role="alert"
          className="border-2 border-status-critical bg-surface-card px-6 py-4 font-body-md text-body-md text-status-critical"
        >
          {loadState.message}
        </p>
      </div>
    );
  }

  const sorted = sortByUpdatedDesc(loadState.experiments);
  const firstName = getFirstName(user?.displayName);

  if (sorted.length === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-gutter pb-12 pt-24">
        <div className="max-w-xl rounded-md border-2 border-border-master bg-surface-card p-10 text-center shadow-brutal-md">
          <p className="font-label-md text-label-md uppercase text-ink-tertiary">
            WELCOME
          </p>
          <h1 className="mt-4 font-display text-display-lg uppercase text-ink-primary">
            Your first validation starts here.
          </h1>
          <p className="mt-4 font-body-md text-body-md text-ink-secondary">
            Fivvle researches your idea, tests it against real people, and hands
            you a defensible decision. Start with a raw idea — no forms, just a
            conversation.
          </p>
          <Link
            href="/new"
            className={`${marketingButtonClass} mt-8 inline-flex bg-brand-primary px-8 py-4 font-label-md text-label-md uppercase text-ink-inverse no-underline shadow-brutal-md`}
          >
            START YOUR FIRST VALIDATION →
          </Link>
        </div>
      </div>
    );
  }

  const recent = sorted.slice(0, 3);
  const mostActive = sorted[0];

  return (
    <div className="px-gutter pb-8 pt-24">
      <h1 className="font-display text-display-lg uppercase text-ink-primary">
        Welcome back, {firstName}
      </h1>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WorkspaceInsightCard experiment={mostActive} hasExperiments />
        </div>
        <UsageSidebarCard
          validationsThisMonth={countExperimentsThisMonth(sorted)}
        />
      </div>

      <div className="mt-12 flex items-center justify-between gap-4">
        <p className="font-label-md text-label-md uppercase text-ink-secondary">
          RECENT EXPERIMENTS
        </p>
        <Link
          href="/experiments"
          className="font-label-md text-label-md uppercase text-brand-primary no-underline hover:underline"
        >
          View all →
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        {recent.map((experiment) => (
          <ProjectCard key={experiment.id} experiment={experiment} />
        ))}
      </div>

      <div className="mt-10 flex justify-center">
        <Link
          href="/new"
          className={`${marketingButtonClass} inline-flex bg-brand-primary px-8 py-4 font-label-md text-label-md uppercase text-ink-inverse no-underline shadow-brutal-md`}
        >
          START NEW VALIDATION
        </Link>
      </div>
    </div>
  );
}
