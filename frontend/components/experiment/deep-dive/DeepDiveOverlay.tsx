"use client";

import { useCallback, useEffect, useState } from "react";
import { EvidenceStagePanel } from "@/components/research/EvidenceStagePanel";
import {
  LaunchStagePanel,
  type LaunchLandingReport,
} from "@/components/launch/LaunchStagePanel";
import { PublishConfirmDialog } from "@/components/launch/PublishConfirmDialog";
import { getExperiment } from "@/lib/api";
import { useToast } from "@/components/ui/ToastProvider";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  act: "evidence" | "launch" | "signal";
  experimentId: string;
};

export function DeepDiveOverlay({ isOpen, onClose, act, experimentId }: Props) {
  const { toast } = useToast();
  const [launchLanding, setLaunchLanding] =
    useState<LaunchLandingReport | null>(null);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [landingRefreshKey, setLandingRefreshKey] = useState(0);
  const [projectName, setProjectName] = useState("your project");

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showPublishDialog) {
          setShowPublishDialog(false);
          return;
        }
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose, showPublishDialog]);

  useEffect(() => {
    setLaunchLanding(null);
    setShowPublishDialog(false);
  }, [isOpen, act]);

  useEffect(() => {
    if (!isOpen || act !== "launch") return;
    let cancelled = false;
    void getExperiment(experimentId)
      .then((exp) => {
        if (!cancelled && exp.name) setProjectName(exp.name);
      })
      .catch(() => {
        /* keep fallback name */
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, act, experimentId]);

  const handlePublishClick = useCallback(() => {
    if (launchLanding?.status !== "LANDING_DRAFT") return;
    setShowPublishDialog(true);
  }, [launchLanding?.status]);

  const handleCopyLiveLink = useCallback(async () => {
    const slug = launchLanding?.slug;
    if (!slug) {
      toast("Live link is not ready yet.", "error");
      return;
    }
    const url = `${window.location.origin}/e/${slug}`;
    try {
      await navigator.clipboard.writeText(url);
      toast("Link copied", "success");
    } catch {
      toast("Could not copy link.", "error");
    }
  }, [launchLanding?.slug, toast]);

  const handlePublished = useCallback(
    (result: { slug: string; public_url: string }) => {
      setShowPublishDialog(false);
      toast("Your page is live.", "success");
      setLandingRefreshKey((k) => k + 1);
      setLaunchLanding((prev) =>
        prev
          ? { ...prev, status: "LANDING_LIVE", slug: result.slug, isLive: true }
          : {
              status: "LANDING_LIVE",
              slug: result.slug,
              isLive: true,
            },
      );
      void navigator.clipboard.writeText(result.public_url).catch(() => {
        /* non-fatal */
      });
    },
    [toast],
  );

  if (!isOpen) return null;

  const isLive = Boolean(launchLanding?.isLive && launchLanding.slug);
  const publishLabel = isLive
    ? `Live at /${launchLanding!.slug}`
    : "Publish landing page";
  const publishEnabled = launchLanding?.status === "LANDING_DRAFT";

  return (
    <>
      <div className="fixed inset-0 z-[70] flex flex-col bg-canvas-bg">
        <div className="flex h-16 shrink-0 items-center justify-between border-b-2 border-border-master px-6">
          <button
            type="button"
            onClick={onClose}
            className="font-label-md text-label-sm uppercase text-ink-primary"
          >
            ← Back to canvas
          </button>

          {act === "launch" ? (
            <span className="border-b-2 border-border-master pb-1 font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              Phase 04: Launch
            </span>
          ) : (
            <h2 className="font-display text-display-sm uppercase text-ink-primary">
              {act} deep-dive
            </h2>
          )}

          <div className="flex items-center gap-3">
            {act === "launch" ? (
              <button
                type="button"
                onClick={isLive ? () => void handleCopyLiveLink() : handlePublishClick}
                disabled={!isLive && !publishEnabled}
                className="rounded-none border-2 border-border-master bg-surface-card px-3 py-1.5 font-label-md text-label-sm uppercase text-ink-primary shadow-brutal-md transition-all enabled:hover:-translate-y-0.5 disabled:opacity-50"
              >
                {publishLabel}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="font-label-md text-label-sm uppercase text-ink-primary"
              aria-label="Close overlay"
            >
              ✕
            </button>
          </div>
        </div>

        {act === "evidence" ? (
          <div className="min-h-0 flex-1 overflow-hidden">
            <EvidenceStagePanel experimentId={experimentId} />
          </div>
        ) : act === "launch" ? (
          <div className="min-h-0 flex-1 overflow-hidden">
            <LaunchStagePanel
              experimentId={experimentId}
              onLandingStateChange={setLaunchLanding}
              onPublishClick={handlePublishClick}
              landingRefreshKey={landingRefreshKey}
            />
          </div>
        ) : (
          <div className="p-24 text-center">
            <div className="mb-2 font-label-md text-label-md uppercase text-brand-primary">
              COMING IN STEP 6
            </div>
            <h2 className="font-display text-display-lg uppercase text-ink-primary">
              {act} deep-dive
            </h2>
          </div>
        )}
      </div>

      {showPublishDialog ? (
        <PublishConfirmDialog
          open={showPublishDialog}
          experimentId={experimentId}
          projectName={projectName}
          onClose={() => setShowPublishDialog(false)}
          onPublished={handlePublished}
        />
      ) : null}
    </>
  );
}
