"use client";

/**
 * Spark form body (idea + attachments + save footer).
 * Used inside DeepDiveOverlay phase panel; also reused by SparkFullscreenModal
 * if that shell is ever remounted.
 */
import { useEffect, useState } from "react";
import { getExperiment } from "@/lib/api";
import type { Experiment } from "@/lib/types";
import { AddAttachmentMenu } from "../attachments/AddAttachmentMenu";
import { AttachmentRow } from "../attachments/AttachmentRow";
import { useAttachments } from "../hooks/useAttachments";
import { useSparkManualSave } from "../hooks/useSparkManualSave";

type Props = {
  experiment: Experiment;
  onExperimentChange?: (experiment: Experiment) => void;
  onDirtyChange?: (dirty: boolean) => void;
};

export function SparkPhaseBody({
  experiment,
  onExperimentChange,
  onDirtyChange,
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

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  useEffect(() => {
    return () => {
      onDirtyChange?.(false);
    };
  }, [onDirtyChange]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mx-auto grid min-h-0 w-full max-w-7xl flex-1 grid-cols-1 gap-6 overflow-auto p-6 lg:grid-cols-5">
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
              <span className="bg-ink-primary px-2 py-0.5 font-mono text-mono-sm uppercase text-brutalist-yellow">
                UNSAVED CHANGES
              </span>
            ) : null}
          </div>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={14}
            placeholder="What are you thinking of building?"
            className="h-[min(60vh,520px)] w-full resize-none rounded-md border-2 border-border-master bg-surface-card p-4 font-body text-body-lg focus:shadow-brutal-primary focus:outline-none"
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
              <p className="font-body text-body-sm italic text-ink-tertiary">
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

      <div className="flex shrink-0 items-center justify-between border-t-2 border-border-master bg-surface-card p-6">
        <div>
          {isDirty ? (
            <span className="bg-ink-primary px-2 py-1 font-mono text-mono-sm uppercase text-brutalist-yellow">
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
          className="rounded-sm border-2 border-border-master bg-brand-primary px-8 py-3 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-md transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-lg active:translate-x-0 active:translate-y-0 active:shadow-none disabled:cursor-not-allowed disabled:opacity-50"
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
