"use client";

import { useState } from "react";
import { getExperiment } from "@/lib/api";
import type { Experiment } from "@/lib/types";
import { AddAttachmentMenu } from "../attachments/AddAttachmentMenu";
import { AttachmentRow } from "../attachments/AttachmentRow";
import { useAttachments } from "../hooks/useAttachments";
import { useSparkManualSave } from "../hooks/useSparkManualSave";

type Props = {
  experiment: Experiment;
  onClose: () => void;
  onMinimize: () => void;
  onExperimentChange?: (experiment: Experiment) => void;
};

export function SparkFullscreenModal({
  experiment,
  onClose,
  onMinimize,
  onExperimentChange,
}: Props) {
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const attachments = useAttachments(experiment.id);

  const refreshExperiment = async () => {
    if (!onExperimentChange) return;
    const updated = await getExperiment(experiment.id);
    onExperimentChange(updated);
  };

  const {
    idea,
    setIdea,
    saving,
    isDirty,
    currentVersion,
    nextVersion,
    handleSave,
    handleCloseAttempt,
  } = useSparkManualSave({
    experiment,
    attachments: attachments.items,
    attachmentsLoading: attachments.loading,
    onSaved: async ({ current_spark_version, raw_idea }) => {
      if (onExperimentChange) {
        const updated = await getExperiment(experiment.id);
        onExperimentChange({
          ...updated,
          current_spark_version,
          raw_idea,
        });
      }
    },
  });

  return (
    <div className="fixed inset-0 z-50 bg-canvas-bg flex flex-col">
      <div className="bg-ink-primary text-ink-inverse flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <span
            className="material-symbols-outlined text-brand-primary"
            style={{ fontSize: 24 }}
            aria-hidden="true"
          >
            bolt
          </span>
          <span className="font-mono text-mono-md uppercase tracking-wider">
            PHASE 01: SPARK // FULLSCREEN
          </span>
          <span className="font-mono text-mono-sm bg-brand-primary text-ink-inverse px-2 py-0.5">
            v{currentVersion || 1}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMinimize}
            aria-label="Exit fullscreen"
            className="p-1 hover:bg-ink-inverse/10"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
              close_fullscreen
            </span>
          </button>
          <button
            type="button"
            onClick={() => handleCloseAttempt(onClose)}
            aria-label="Close"
            className="p-1 hover:bg-ink-inverse/10"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
              close
            </span>
          </button>
        </div>
      </div>

      <div className="mx-auto grid flex-1 max-w-7xl grid-cols-1 gap-6 overflow-auto p-6 lg:grid-cols-5 w-full">
        <div className="lg:col-span-3">
          {experiment.refinement_started_at ? (
            <div className="mb-4 rounded-md border-2 border-brutalist-yellow bg-brutalist-yellow/20 p-3">
              <p className="font-body text-body-sm text-ink-primary">
                <strong>Note:</strong> You&apos;ve already started Refine.
                Editing your idea won&apos;t automatically re-run it.
              </p>
            </div>
          ) : null}
          <div className="mb-2 flex items-center justify-between">
            <label className="font-label-md text-label-md uppercase">
              THE IDEA
            </label>
            {isDirty ? (
              <span className="font-mono text-mono-sm uppercase text-brutalist-yellow bg-ink-primary px-2 py-0.5">
                UNSAVED CHANGES
              </span>
            ) : null}
          </div>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={14}
            placeholder="What are you thinking of building?"
            className="h-[min(60vh,520px)] w-full rounded-md border-2 border-border-master bg-surface-card p-4 font-body text-body-lg focus:outline-none focus:shadow-brutal-primary resize-none"
          />
          <p className="mt-2 font-mono text-mono-sm text-ink-tertiary">
            {idea.length} CHARACTERS
          </p>
        </div>
        <div className="rounded-md border-2 border-border-master bg-surface-card p-4 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <label className="font-label-md text-label-md uppercase text-ink-primary">
              ATTACHMENTS ({attachments.items.length})
            </label>
            <div className="relative">
              <button
                type="button"
                onClick={() => setAddMenuOpen((v) => !v)}
                className="rounded-sm border-2 border-border-master bg-surface-card px-3 py-1 font-label-md text-label-md uppercase shadow-brutal-sm"
              >
                + ADD
              </button>
              {addMenuOpen ? (
                <AddAttachmentMenu
                  experimentId={experiment.id}
                  onAdd={() => {
                    void attachments.refetch();
                    void refreshExperiment();
                    setAddMenuOpen(false);
                  }}
                  onClose={() => setAddMenuOpen(false)}
                />
              ) : null}
            </div>
          </div>
          {attachments.items.length === 0 ? (
            <div className="border-2 border-dashed border-border-master p-6 text-center">
              <p className="font-body text-body-sm text-ink-tertiary italic">
                No files yet. Upload a file or add a link.
              </p>
            </div>
          ) : (
            <ul className="space-y-2">
              {attachments.items.map((att) => (
                <AttachmentRow
                  key={att.id}
                  attachment={att}
                  onDelete={() => {
                    void attachments
                      .remove(att.id)
                      .then(() => refreshExperiment());
                  }}
                />
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="border-t-2 border-border-master p-6 flex items-center justify-between bg-surface-card">
        <div>
          {isDirty ? (
            <span className="font-mono text-mono-sm uppercase text-brutalist-yellow bg-ink-primary px-2 py-1">
              UNSAVED CHANGES
            </span>
          ) : (
            <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
              Version {currentVersion || 1}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={!isDirty || saving}
          className="rounded-sm bg-brand-primary text-ink-inverse px-8 py-3 border-2 border-border-master font-label-md text-label-md uppercase tracking-wider shadow-brutal-md hover:shadow-brutal-lg hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {saving
            ? "SAVING..."
            : isDirty
              ? `SAVE AS v${nextVersion}`
              : "NO CHANGES"}
        </button>
      </div>
    </div>
  );
}
