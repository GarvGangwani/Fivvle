"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { generateLandingPage, getExperiment, getLandingPage } from "@/lib/api";
import { generateLaunchKit } from "@/lib/api-launch-kit";
import { useLaunchKit } from "@/hooks/useLaunchKit";
import { useToast } from "@/components/ui/ToastProvider";
import {
  LivePagePreviewPanel,
  type PreviewState,
} from "@/components/launch/LivePagePreviewPanel";
import { LaunchKitPanel } from "@/components/launch/LaunchKitPanel";
import {
  LaunchTabs,
  type LaunchTabId,
} from "@/components/launch/LaunchTabs";
import { LaunchCopyTab } from "@/components/launch/LaunchCopyTab";
import { LaunchDesignTab } from "@/components/launch/design/LaunchDesignTab";
import { LaunchShareTab } from "@/components/launch/share/LaunchShareTab";
import { getExperimentDisplayName } from "@/lib/experiment-name";

/** Statuses where a LandingPage row exists (mirrors canvas-helpers LANDING_PAGE_CREATED). */
const LANDING_READY_STATUSES = new Set([
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "ARCHIVED",
  "COMPLETED",
]);

const KIT_POLL_INTERVAL_MS = 3000;
const MAX_KIT_POLLS = 20;

export type LaunchLandingReport = {
  status: string;
  slug: string | null;
  isLive: boolean;
};

type Props = {
  experimentId: string;
  /** Reports resolved status + landing state up so the overlay can gate Publish. */
  onLandingStateChange?: (state: LaunchLandingReport) => void;
  /** Overlay-owned publish / live-copy handler (kit footer uses the same). */
  onPublishClick?: () => void;
  /** Bumped by overlay after a successful publish to refetch experiment status. */
  landingRefreshKey?: number;
};

export function LaunchStagePanel({
  experimentId,
  onLandingStateChange,
  onPublishClick: _onPublishClick,
  landingRefreshKey = 0,
}: Props) {
  const { toast } = useToast();
  const {
    launchKit,
    loading: kitLoading,
    error: kitError,
    notGenerated,
    refresh,
    patch,
    isSaving,
    checkReadinessItem,
  } = useLaunchKit(experimentId, {
    onConflict: (message) => toast(message, "info"),
    onError: (message) => toast(message, "error"),
  });

  const [status, setStatus] = useState<string | null>(null);
  const [statusReloadKey, setStatusReloadKey] = useState(0);
  const [slug, setSlug] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [experimentName, setExperimentName] = useState("Untitled project");
  const [pendingLandingGenerate, setPendingLandingGenerate] = useState(false);
  const [kitGenerating, setKitGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<LaunchTabId>("copy");
  /** Bumps iframe `?v=` after Copy/Design PATCH so preview picks up edits. */
  const [previewCacheBust, setPreviewCacheBust] = useState(0);
  const kitPollCount = useRef(0);
  const defaultTabSettledRef = useRef(false);

  const bumpPreviewCache = useCallback(() => {
    setPreviewCacheBust(Date.now());
  }, []);

  const landingReady = status !== null && LANDING_READY_STATUSES.has(status);
  const landingGenerating =
    status === "LANDING_GENERATING" || pendingLandingGenerate;

  // One-shot default tab: Copy pre-publish, Kit when already live.
  // Founder tab clicks after this win for the rest of the session.
  useEffect(() => {
    if (defaultTabSettledRef.current) return;
    if (status === null) return;
    defaultTabSettledRef.current = true;
    setActiveTab(status === "LANDING_LIVE" ? "kit" : "copy");
  }, [status]);

  // Experiment status — orthogonal to LaunchKit; fetched here and re-fetched via
  // statusReloadKey while a generation is in flight, or after publish.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const experiment = await getExperiment(experimentId);
        if (cancelled) return;
        setStatus(experiment.status);
        setExperimentName(getExperimentDisplayName(experiment));
      } catch {
        if (cancelled) return;
        setStatus((prev) => prev ?? "RESEARCH_READY");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [experimentId, statusReloadKey, landingRefreshKey]);

  // Landing page (slug + live_at) — only meaningful once a page exists.
  useEffect(() => {
    if (!landingReady) {
      setSlug(null);
      setIsLive(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const page = await getLandingPage(experimentId);
        if (cancelled) return;
        setSlug(page.slug);
        setIsLive(page.live_at !== null);
      } catch {
        if (cancelled) return;
        setSlug(null);
        setIsLive(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [experimentId, landingReady, status]);

  // Clear the pending flag once the backend actually produced the page.
  useEffect(() => {
    if (landingReady) setPendingLandingGenerate(false);
  }, [landingReady]);

  // Poll experiment status every 3s while the page is generating.
  useEffect(() => {
    if (!landingGenerating) return;
    const timer = setTimeout(
      () => setStatusReloadKey((key) => key + 1),
      KIT_POLL_INTERVAL_MS,
    );
    return () => clearTimeout(timer);
  }, [landingGenerating, statusReloadKey]);

  // Poll the launch kit every 3s while a kit generation is in flight.
  useEffect(() => {
    if (!kitGenerating) return;
    if (launchKit) {
      setKitGenerating(false);
      kitPollCount.current = 0;
      return;
    }
    if (kitPollCount.current >= MAX_KIT_POLLS) {
      setKitGenerating(false);
      kitPollCount.current = 0;
      return;
    }
    const timer = setTimeout(() => {
      kitPollCount.current += 1;
      refresh();
    }, KIT_POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [kitGenerating, launchKit, refresh]);

  // Report status + landing state up for the overlay's Publish button.
  useEffect(() => {
    if (status === null) return;
    onLandingStateChange?.({ status, slug, isLive });
  }, [status, slug, isLive, onLandingStateChange]);

  const handleGenerateLandingPage = useCallback(async () => {
    setPendingLandingGenerate(true);
    try {
      await generateLandingPage(experimentId);
      toast("Building your landing page — this takes a moment.", "info");
      setStatusReloadKey((key) => key + 1);
    } catch {
      setPendingLandingGenerate(false);
      toast("Could not start landing page generation. Try again.", "error");
    }
  }, [experimentId, toast]);

  const handleGenerateKit = useCallback(async () => {
    setKitGenerating(true);
    kitPollCount.current = 0;
    try {
      await generateLaunchKit(experimentId);
      toast("Building your launch kit — this takes a moment.", "info");
    } catch {
      setKitGenerating(false);
      toast("Could not start launch kit generation. Try again.", "error");
    }
  }, [experimentId, toast]);

  const previewState: PreviewState = landingGenerating
    ? "generating"
    : landingReady
      ? isLive
        ? "live"
        : "draft"
      : "generate";

  return (
    <div className="relative flex h-full min-h-0 overflow-hidden">
      <span
        className="pointer-events-none absolute bottom-10 left-10 z-0 select-none font-display text-[120px] uppercase leading-none text-ink-primary opacity-20"
        aria-hidden="true"
      >
        Launch
      </span>

      {/* Left ~70% — live page preview */}
      <div className="relative z-10 w-[70%] min-w-0">
        <LivePagePreviewPanel
          previewState={previewState}
          slug={slug}
          cacheBust={previewCacheBust}
          onGenerateLandingPage={handleGenerateLandingPage}
        />
      </div>

      {/* Right ~30% — tab surface */}
      <div className="relative z-10 flex w-[30%] min-w-0 flex-col border-l-2 border-border-master">
        <LaunchTabs activeTab={activeTab} onTabChange={setActiveTab} />
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {activeTab === "copy" ? (
            <LaunchCopyTab
              experimentId={experimentId}
              landingGenerating={landingGenerating}
              onGenerateLandingPage={handleGenerateLandingPage}
              onLandingPageSaved={bumpPreviewCache}
            />
          ) : activeTab === "design" ? (
            <LaunchDesignTab
              experimentId={experimentId}
              landingGenerating={landingGenerating}
              onGenerateLandingPage={handleGenerateLandingPage}
              onLandingPageSaved={bumpPreviewCache}
            />
          ) : activeTab === "share" ? (
            <LaunchShareTab
              experimentId={experimentId}
              slug={slug}
              isLive={isLive}
              experimentName={experimentName}
              landingReady={landingReady}
              landingGenerating={landingGenerating}
              onGenerateLandingPage={handleGenerateLandingPage}
              onSlugSaved={setSlug}
            />
          ) : (
            renderKitColumn()
          )}
        </div>
      </div>
    </div>
  );

  function renderKitColumn() {
    if (status === null) {
      return <KitShell><KitMessage message="Loading launch kit…" /></KitShell>;
    }
    // Gate by status first: PR 1 rejects generation before LANDING_DRAFT.
    if (!landingReady) {
      return (
        <KitShell>
          <KitMessage message="Your kit unlocks after your landing page is ready." />
        </KitShell>
      );
    }
    if (kitLoading || kitGenerating) {
      return (
        <KitShell>
          <KitMessage
            message={kitGenerating ? "Building your launch kit…" : "Loading launch kit…"}
          />
        </KitShell>
      );
    }
    if (kitError) {
      return (
        <KitShell>
          <KitMessage message={kitError} tone="error" />
        </KitShell>
      );
    }
    if (notGenerated || !launchKit) {
      return <KitGenerateState onGenerate={handleGenerateKit} />;
    }
    return (
      <LaunchKitPanel
        launchKit={launchKit}
        slug={slug}
        isLive={isLive}
        experimentName={experimentName}
        onPatch={patch}
        isSaving={isSaving}
        checkReadinessItem={checkReadinessItem}
      />
    );
  }
}

/** Header frame for kit fallback states — micro-copy only (tab strip owns the label). */
function KitShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b-2 border-border-master bg-surface-elevated px-6 py-4">
        <p className="font-mono text-mono-sm uppercase text-ink-primary/60">
          Ready to put this in front of people
        </p>
      </div>
      <div className="flex min-h-0 flex-1 items-center justify-center p-6">
        {children}
      </div>
    </div>
  );
}

function KitMessage({
  message,
  tone = "neutral",
}: {
  message: string;
  tone?: "neutral" | "error";
}) {
  return (
    <p
      className={`text-center font-mono text-mono-sm uppercase ${
        tone === "error" ? "text-status-critical" : "text-ink-primary/60"
      }`}
    >
      {message}
    </p>
  );
}

function KitGenerateState({ onGenerate }: { onGenerate: () => void }) {
  return (
    <KitShell>
      <div className="flex flex-col items-center gap-4 text-center">
        <span
          className="material-symbols-outlined text-ink-tertiary"
          style={{ fontSize: 40, fontVariationSettings: "'FILL' 1" }}
          aria-hidden="true"
        >
          rocket_launch
        </span>
        <p className="max-w-xs font-mono text-mono-sm uppercase text-ink-primary/60">
          Generate a personalized launch kit based on your evidence report.
        </p>
        <button
          type="button"
          onClick={onGenerate}
          className="border-2 border-border-master bg-brand-primary px-4 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-sm transition-all hover:shadow-brutal-md"
        >
          Generate launch kit
        </button>
      </div>
    </KitShell>
  );
}
