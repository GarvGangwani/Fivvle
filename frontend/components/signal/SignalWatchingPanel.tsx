"use client";

import type { ExperimentAnalytics } from "@/lib/types";
import { SignalWatchingDetail } from "./SignalWatchingDetail";
import { ThresholdDistanceHero } from "./ThresholdDistanceHero";

type Props = {
  data: ExperimentAnalytics | null;
  loading: boolean;
  error: string | null;
  notAvailable: string | null;
  onOpenLaunch: () => void;
};

function WatchingSkeleton() {
  return (
    <div
      className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md"
      aria-busy="true"
      aria-label="Loading analytics"
    >
      <div className="mb-4 h-6 w-24 border-2 border-border-master bg-surface-elevated" />
      <div className="h-8 w-3/4 border-2 border-border-master bg-surface-elevated" />
      <div className="mt-4 h-4 w-full border-2 border-border-master bg-surface-elevated" />
      <div className="mt-6 space-y-4">
        <div className="h-3 border-2 border-border-master bg-surface-elevated" />
        <div className="h-3 border-2 border-border-master bg-surface-elevated" />
        <div className="h-3 border-2 border-border-master bg-surface-elevated" />
      </div>
    </div>
  );
}

function WatchingEmpty({ onOpenLaunch }: { onOpenLaunch: () => void }) {
  return (
    <div className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md">
      <div className="mb-3 inline-block border-2 border-border-master bg-brutalist-yellow px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm">
        Watching
      </div>
      <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
        Waiting for your first visitor
      </h2>
      <p className="mt-3 text-body-md text-ink-secondary">
        Your page is live. As soon as someone lands, distance to a verdict
        shows up here — one path is enough.
      </p>
      <LaunchTrafficLink onOpenLaunch={onOpenLaunch} />
    </div>
  );
}

function LaunchTrafficLink({ onOpenLaunch }: { onOpenLaunch: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpenLaunch}
      className="mt-6 font-label-md text-label-sm uppercase tracking-wider text-ink-primary underline decoration-2 underline-offset-4"
    >
      Get more traffic → Launch
    </button>
  );
}

function isEmptyAnalytics(data: {
  total_page_views: number;
  total_signups: number;
}): boolean {
  return data.total_page_views === 0 && data.total_signups === 0;
}

/** Watching shell UI — analytics owned by SignalStagePanel (router). */
export function SignalWatchingPanel({
  data,
  loading,
  error,
  notAvailable,
  onOpenLaunch,
}: Props) {
  if (notAvailable) {
    return (
      <div className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md">
        <p className="mb-2 font-label-md text-label-md uppercase tracking-wider text-ink-tertiary">
          Not available
        </p>
        <p className="text-body-md text-ink-secondary">{notAvailable}</p>
      </div>
    );
  }

  if (loading && !data) {
    return <WatchingSkeleton />;
  }

  if (!data) {
    if (error) {
      return (
        <div className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md">
          <p className="mb-2 font-label-md text-label-md uppercase tracking-wider text-ink-tertiary">
            Temporary issue
          </p>
          <p className="text-body-md text-ink-secondary">{error}</p>
        </div>
      );
    }
    return <WatchingSkeleton />;
  }

  if (isEmptyAnalytics(data)) {
    return (
      <>
        {error ? (
          <p className="mb-3 font-mono text-mono-sm uppercase text-ink-tertiary">
            Showing last known empty state · {error}
          </p>
        ) : null}
        <WatchingEmpty onOpenLaunch={onOpenLaunch} />
      </>
    );
  }

  return (
    <div className="space-y-4">
      {error ? (
        <p className="border-2 border-border-master bg-surface-elevated px-3 py-2 font-mono text-mono-sm uppercase text-ink-tertiary shadow-brutal-sm">
          Update delayed · {error}
        </p>
      ) : null}

      <ThresholdDistanceHero progress={data.insight_progress} />
      <SignalWatchingDetail analytics={data} />
      <LaunchTrafficLink onOpenLaunch={onOpenLaunch} />
    </div>
  );
}
