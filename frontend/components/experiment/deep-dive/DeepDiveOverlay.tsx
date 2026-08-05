"use client";

/**
 * Phase panel overlay (Universal Agent Phase 2 layout).
 *
 * Z-index scheme (canvas route):
 * - Scrim:           z-[65]  — translucent; click closes panel
 * - Phase panel:     z-[70]  — opaque card over canvas gutters
 * - Universal dock:  z-[80]  — stays interactive above scrim
 *
 * Panel frame matches dock gutters: top/left/bottom-6 (24px). Right inset
 * reserves the master chat rail (expanded 480px / collapsed 40px) plus a
 * matching 24px gap between panel and dock.
 */
import { useCallback, useEffect, useState } from "react";
import { Archive } from "lucide-react";
import { ArchiveProjectDialog } from "@/components/experiment/ArchiveProjectDialog";
import { ACT_CONFIG } from "@/components/experiment/act-config";
import { RefinePhaseBody } from "@/components/experiment/refine/RefinePhaseBody";
import type { RefineChatMessageModel } from "@/components/experiment/refine/RefineChatMessage";
import { EvidenceStagePanel } from "@/components/research/EvidenceStagePanel";
import {
  LaunchStagePanel,
  type LaunchLandingReport,
} from "@/components/launch/LaunchStagePanel";
import { PublishConfirmDialog } from "@/components/launch/PublishConfirmDialog";
import { SignalStagePanel } from "@/components/signal/SignalStagePanel";
import { getExperiment, republishLandingPage } from "@/lib/api";
import type { Experiment, ExperimentStatus, FounderDecision } from "@/lib/types";
import { useToast } from "@/components/ui/ToastProvider";

export type DeepDiveAct =
  | "refine"
  | "evidence"
  | "launch"
  | "signal";

/** Expanded: dock right-6 + 480px + 24px gap between panel and dock */
const PANEL_RIGHT_EXPANDED = "right-[calc(480px+3rem)]";
/** Collapsed: dock right-6 + w-10 (2.5rem) + 24px gap between panel and dock */
const PANEL_RIGHT_COLLAPSED = "right-[calc(2.5rem+3rem)]";

function overlayTitle(act: DeepDiveAct): string {
  if (act === "launch") return "Phase 04: Launch";
  const config = ACT_CONFIG[act];
  return `PHASE ${config.index}: ${config.actName} — ${config.title}`;
}

type RefinePanelProps = {
  messages: RefineChatMessageModel[];
  onFinalizedOrReset: () => Promise<void>;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  act: DeepDiveAct;
  experimentId: string;
  experiment: Experiment;
  /** Canvas-owned experiment.status — single source of truth on screen. */
  experimentStatus: ExperimentStatus;
  projectName: string;
  founderDecision?: FounderDecision | null;
  founderDecisionAt?: string | null;
  founderDecisionNote?: string | null;
  founderDecisionVersion?: number | null;
  /** Refresh canvas experiment after publish / decision / archive. */
  onExperimentRefresh?: () => Promise<void>;
  onExperimentChange?: (experiment: Experiment) => void;
  /** Plain act switch to Launch (no tab targeting — Kit deep-link deferred). */
  onOpenLaunch: () => void;
  /** Master rail collapse — drives panel right inset. */
  chatDockCollapsed?: boolean;
  refinePanel?: RefinePanelProps | null;
};

export function DeepDiveOverlay({
  isOpen,
  onClose,
  act,
  experimentId,
  experiment,
  experimentStatus,
  projectName,
  founderDecision = null,
  founderDecisionAt = null,
  founderDecisionNote = null,
  founderDecisionVersion = null,
  onExperimentRefresh,
  onExperimentChange,
  onOpenLaunch,
  chatDockCollapsed = false,
  refinePanel = null,
}: Props) {
  const { toast } = useToast();
  const [launchLanding, setLaunchLanding] =
    useState<LaunchLandingReport | null>(null);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [showArchiveDialog, setShowArchiveDialog] = useState(false);
  const [landingRefreshKey, setLandingRefreshKey] = useState(0);
  const [resolvedProjectName, setResolvedProjectName] = useState(projectName);
  const [republishing, setRepublishing] = useState(false);

  useEffect(() => {
    setResolvedProjectName(projectName);
  }, [projectName]);

  const requestClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (showArchiveDialog) {
        setShowArchiveDialog(false);
        return;
      }
      if (showPublishDialog) {
        setShowPublishDialog(false);
        return;
      }
      requestClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    isOpen,
    requestClose,
    showPublishDialog,
    showArchiveDialog,
  ]);

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

  const handleRepublish = useCallback(async () => {
    const confirmed = window.confirm(
      "Republish? Your Signal analytics will reset — the current cohort will close and a new one will start. Prior data stays saved but insight reports will focus on the new run. Continue?",
    );
    if (!confirmed) return;

    setRepublishing(true);
    try {
      const result = await republishLandingPage(experimentId);
      toast(
        `New cohort started (Publish #${result.publish_number}).`,
        "success",
      );
      setLandingRefreshKey((k) => k + 1);
      void onExperimentRefresh?.().catch(() => {
        /* best-effort */
      });
    } catch {
      toast("Republish failed — try again.", "error");
    } finally {
      setRepublishing(false);
    }
  }, [experimentId, toast, onExperimentRefresh]);

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
  const publishEnabled = launchLanding?.status === "LANDING_DRAFT";
  const canArchive = experimentStatus !== "ARCHIVED";
  const title = overlayTitle(act);
  const rightInset = chatDockCollapsed
    ? PANEL_RIGHT_COLLAPSED
    : PANEL_RIGHT_EXPANDED;

  return (
    <>
      {/* Scrim — below panel (70) and dock (80); click closes */}
      <button
        type="button"
        aria-label="Close phase panel"
        className="fixed inset-0 z-[65] cursor-default border-0 bg-ink-primary/40 p-0"
        onClick={requestClose}
      />

      <div
        className={`fixed bottom-6 left-6 top-6 z-[70] flex flex-col overflow-hidden rounded-md border-2 border-border-master bg-canvas-bg shadow-brutal-lg ${rightInset}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b-2 border-border-master px-6">
          <button
            type="button"
            onClick={requestClose}
            className="font-label-md text-label-sm uppercase text-ink-primary"
          >
            ← Back to canvas
          </button>

          {act === "launch" ? (
            <span className="border-b-2 border-border-master pb-1 font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              {title}
            </span>
          ) : (
            <h2 className="font-display text-display-sm uppercase text-ink-primary">
              {title}
            </h2>
          )}

          <div className="flex items-center gap-3">
            {act === "launch" ? (
              isLive ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void handleCopyLiveLink()}
                    className="rounded-none border-2 border-border-master bg-surface-card px-3 py-1.5 font-label-md text-label-sm uppercase text-ink-primary shadow-brutal-md transition-all hover:-translate-y-0.5"
                  >
                    Copy link
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleRepublish()}
                    disabled={republishing}
                    className="rounded-none border-2 border-border-master bg-surface-elevated px-3 py-1.5 font-label-md text-label-sm uppercase text-ink-primary shadow-brutal-md transition-all enabled:hover:-translate-y-0.5 disabled:opacity-50"
                  >
                    {republishing ? "Republishing…" : "Republish (new cohort)"}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handlePublishClick}
                  disabled={!publishEnabled}
                  className="rounded-none border-2 border-border-master bg-surface-card px-3 py-1.5 font-label-md text-label-sm uppercase text-ink-primary shadow-brutal-md transition-all enabled:hover:-translate-y-0.5 disabled:opacity-50"
                >
                  Publish landing page
                </button>
              )
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
              onClick={requestClose}
              className="font-label-md text-label-sm uppercase text-ink-primary"
              aria-label="Close overlay"
            >
              ✕
            </button>
          </div>
        </div>

        {act === "refine" && refinePanel ? (
          <div className="min-h-0 flex-1 overflow-hidden">
            <RefinePhaseBody
              experiment={experiment}
              messages={refinePanel.messages}
              onFinalizedOrReset={refinePanel.onFinalizedOrReset}
            />
          </div>
        ) : act === "evidence" ? (
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
        ) : act === "signal" ? (
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
        ) : null}
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
