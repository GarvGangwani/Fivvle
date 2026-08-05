"use client";

import { StartupUrlCard } from "./StartupUrlCard";
import { ShareWithTrackingCard } from "./ShareWithTrackingCard";

type Props = {
  experimentId: string;
  slug: string | null;
  isLive: boolean;
  experimentName: string;
  landingReady: boolean;
  landingGenerating?: boolean;
  onGenerateLandingPage: () => void;
  onSlugSaved: (slug: string) => void;
};

/**
 * Launch Share tab — Startup URL + tracked channel links.
 * Zero backend work; wraps LandingPageSlugEditor + ShareLinksPanel (A1).
 */
export function LaunchShareTab({
  experimentId,
  slug,
  isLive,
  experimentName,
  landingReady,
  landingGenerating = false,
  onGenerateLandingPage,
  onSlugSaved,
}: Props) {
  if (landingGenerating) {
    return (
      <Shell>
        <p className="text-center font-mono text-mono-sm uppercase text-ink-primary/60">
          Building your page — share unlocks when it&apos;s ready.
        </p>
      </Shell>
    );
  }

  if (!landingReady || !slug) {
    return (
      <Shell>
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="max-w-xs font-mono text-mono-sm uppercase text-ink-primary/60">
            Your kit unlocks after your landing page is ready.
          </p>
          <button
            type="button"
            onClick={onGenerateLandingPage}
            className="border-2 border-border-master bg-accent px-4 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-sm transition-all hover:shadow-brutal-md"
          >
            Generate landing page
          </button>
        </div>
      </Shell>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        <StartupUrlCard
          experimentId={experimentId}
          slug={slug}
          projectName={experimentName}
          isLive={isLive}
          onSlugSaved={onSlugSaved}
        />
        <ShareWithTrackingCard
          slug={slug}
          experimentName={experimentName}
          isLive={isLive}
        />
      </div>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-1 items-center justify-center p-6">
      {children}
    </div>
  );
}
