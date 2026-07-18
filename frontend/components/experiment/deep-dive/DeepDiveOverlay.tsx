"use client";

import { useCallback, useEffect, useState } from "react";
import { EvidenceStagePanel } from "@/components/research/EvidenceStagePanel";
import {
  LaunchStagePanel,
  type LaunchLandingReport,
} from "@/components/launch/LaunchStagePanel";
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

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    setLaunchLanding(null);
  }, [isOpen, act]);

  const handlePublishClick = useCallback(() => {
    toast("Publishing lands in PR 3", "info");
  }, [toast]);

  if (!isOpen) return null;

  const publishLabel =
    launchLanding?.isLive && launchLanding.slug
      ? `Live at /${launchLanding.slug}`
      : "Publish landing page";
  const publishEnabled = launchLanding?.status === "LANDING_DRAFT";

  return (
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
              onClick={handlePublishClick}
              disabled={!publishEnabled}
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
  );
}
