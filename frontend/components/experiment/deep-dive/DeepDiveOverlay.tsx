"use client";

import { useCallback, useEffect, useState } from "react";
import { Archive } from "lucide-react";
import { ArchiveProjectDialog } from "@/components/experiment/ArchiveProjectDialog";
import { EvidenceStagePanel } from "@/components/research/EvidenceStagePanel";
import {
  LaunchStagePanel,
  type LaunchLandingReport,
} from "@/components/launch/LaunchStagePanel";
import { PublishConfirmDialog } from "@/components/launch/PublishConfirmDialog";
import { SignalStagePanel } from "@/components/signal/SignalStagePanel";
import { getExperiment } from "@/lib/api";
import type { ExperimentStatus, FounderDecision } from "@/lib/types";
import { useToast } from "@/components/ui/ToastProvider";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  act: "evidence" | "launch" | "signal";
  experimentId: string;
  /** Canvas-owned experiment.status — single source of truth on screen. */
  experimentStatus: ExperimentStatus;
  projectName: string;
  founderDecision?: FounderDecision | null;
  founderDecisionAt?: string | null;
  founderDecisionNote?: string | null;
  founderDecisionVersion?: number | null;
  /** Refresh canvas experiment after publish / decision / archive. */
  onExperimentRefresh?: () => Promise<void>;
  /** Plain act switch to Launch (no tab targeting — Kit deep-link deferred). */
  onOpenLaunch: () => void;
};

export function DeepDiveOverlay({
  isOpen,
  onClose,
  act,
  experimentId,
  experimentStatus,
  projectName,
  founderDecision = null,
  founderDecisionAt = null,
  founderDecisionNote = null,
  founderDecisionVersion = null,
  onExperimentRefresh,
  onOpenLaunch,
}: Props) {
  const { toast } = useToast();
  const [launchLanding, setLaunchLanding] =
    useState<LaunchLandingReport | null>(null);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [showArchiveDialog, setShowArchiveDialog] = useState(false);
  const [landingRefreshKey, setLandingRefreshKey] = useState(0);
  const [resolvedProjectName, setResolvedProjectName] = useState(projectName);

  useEffect(() => {
    setResolvedProjectName(projectName);
  }, [projectName]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showArchiveDialog) {
          setShowArchiveDialog(false);
          return;
        }
        if (showPublishDialog) {
          setShowPublishDialog(false);
          return;
        }
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose, showPublishDialog, showArchiveDialog]);

  useEffect(() => {
    setLaunchLanding(null);
    setShowPublishDialog(false);
    setShowArchiveDialog(false);
  }, [isOpen, act]);

  useEffect(() => {
    if (!isOpen || act !== "launch") return;
    let cancelled = false;
    void getExperiment(experimentId)
      .then((exp) => {
        if (!cancelled && exp.name) setResolvedProjectName(exp.name);
      })
      .catch(() => {
        /* keep prop / fallback name */
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
      void onExperimentRefresh?.().catch(() => {
        /* canvas refresh is best-effort; Launch local state already live */
      });
    },
    [toast, onExperimentRefresh],
  );

  if (!isOpen) return null;

  const isLive = Boolean(launchLanding?.isLive && launchLanding.slug);
  const publishLabel = isLive
    ? `Live at /${launchLanding!.slug}`
    : "Publish landing page";
  const publishEnabled = launchLanding?.status === "LANDING_DRAFT";
  const canArchive = experimentStatus !== "ARCHIVED";

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
            {canArchive ? (
              <button
                type="button"
                onClick={() => setShowArchiveDialog(true)}
                className="inline-flex items-center gap-1.5 border-2 border-border-master bg-surface-elevated px-3 py-1.5 font-label-md text-label-sm uppercase tracking-wider text-ink-secondary shadow-brutal-sm"
                aria-label="Archive project"
              >
                <Archive className="h-3.5 w-3.5" aria-hidden />
                Archive
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
          <div className="min-h-0 flex-1 overflow-hidden">
            <SignalStagePanel
              experimentId={experimentId}
              status={experimentStatus}
              isOpen={isOpen}
              act={act}
              onOpenLaunch={onOpenLaunch}
              onExperimentRefresh={onExperimentRefresh}
              founderDecision={founderDecision}
              founderDecisionAt={founderDecisionAt}
              founderDecisionNote={founderDecisionNote}
              founderDecisionVersion={founderDecisionVersion}
            />
          </div>
        )}
      </div>

      {showPublishDialog ? (
        <PublishConfirmDialog
          open={showPublishDialog}
          experimentId={experimentId}
          projectName={resolvedProjectName}
          onClose={() => setShowPublishDialog(false)}
          onPublished={handlePublished}
        />
      ) : null}

      <ArchiveProjectDialog
        open={showArchiveDialog}
        experimentId={experimentId}
        projectName={resolvedProjectName}
        onClose={() => setShowArchiveDialog(false)}
        onArchived={() => {
          void onExperimentRefresh?.();
          onClose();
        }}
      />
    </>
  );
}
