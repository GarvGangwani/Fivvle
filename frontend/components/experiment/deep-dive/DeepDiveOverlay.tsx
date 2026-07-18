"use client";

import { useCallback, useEffect, useState } from "react";
import type { Experiment } from "@/types/experiment";
import { publishProject } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useToast } from "@/components/ui/Toast";
import { LaunchStagePanel } from "@/components/launch/LaunchStagePanel";
import { PublishConfirmDialog } from "@/components/launch/PublishConfirmDialog";
import { DeepDiveShell } from "./DeepDiveShell";
import { DeepDiveSidebar } from "./DeepDiveSidebar";
import { DeepDiveMain } from "./DeepDiveMain";
import type { DeepDiveSection } from "./types";

interface DeepDiveOverlayProps {
  experiment: Experiment;
  initialSection?: DeepDiveSection;
  onClose: () => void;
  /** Called after a successful publish so the parent can refresh experiment state. */
  onExperimentUpdated?: () => void | Promise<void>;
}

export function DeepDiveOverlay({
  experiment,
  initialSection = "overview",
  onClose,
  onExperimentUpdated,
}: DeepDiveOverlayProps) {
  const { toast } = useToast();
  const [activeSection, setActiveSection] = useState<DeepDiveSection>(initialSection);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const isLive = experiment.status === "LANDING_LIVE";
  const canPublish = experiment.status === "LANDING_DRAFT" && Boolean(experiment.landing_page);

  const handlePublishClick = useCallback(() => {
    if (!canPublish || publishing) return;
    setShowPublishDialog(true);
  }, [canPublish, publishing]);

  const handlePublishConfirm = useCallback(
    async (ctaMode: "waitlist" | "coming_soon") => {
      setPublishing(true);
      try {
        await publishProject(experiment.id, { cta_mode: ctaMode });
        toast("Your page is live.", "success");
        setShowPublishDialog(false);
        await onExperimentUpdated?.();
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Could not publish. Try again.";
        toast(message, "error");
      } finally {
        setPublishing(false);
      }
    },
    [experiment.id, onExperimentUpdated, toast],
  );

  const handleCopyLiveLink = useCallback(async () => {
    const slug = experiment.landing_page?.slug;
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
  }, [experiment.landing_page?.slug, toast]);

  // Escape to close
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (showPublishDialog) {
          setShowPublishDialog(false);
          return;
        }
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, showPublishDialog]);

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  if (activeSection === "launch") {
    return (
      <>
        <DeepDiveShell onClose={onClose}>
          <LaunchStagePanel
            experiment={experiment}
            onBack={onClose}
            onPublish={handlePublishClick}
            publishing={publishing}
            isLive={isLive}
            onCopyLiveLink={isLive ? handleCopyLiveLink : undefined}
          />
        </DeepDiveShell>
        {showPublishDialog ? (
          <PublishConfirmDialog
            open={showPublishDialog}
            publishing={publishing}
            onConfirm={handlePublishConfirm}
            onCancel={() => {
              if (!publishing) setShowPublishDialog(false);
            }}
          />
        ) : null}
      </>
    );
  }

  return (
    <DeepDiveShell onClose={onClose}>
      <DeepDiveSidebar
        experiment={experiment}
        activeSection={activeSection}
        onSectionChange={setActiveSection}
      />
      <DeepDiveMain experiment={experiment} section={activeSection} />
    </DeepDiveShell>
  );
}
