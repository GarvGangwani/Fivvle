"use client";

import { useEffect, useRef, useState } from "react";
import type { NodeProps } from "reactflow";
import { getExperiment } from "@/lib/api";
import type { Experiment } from "@/lib/types";
import { AddAttachmentMenu } from "../attachments/AddAttachmentMenu";
import { AttachmentRow } from "../attachments/AttachmentRow";
import { useAttachments } from "../hooks/useAttachments";

export type SparkExpandedData = {
  experiment: Experiment;
  onClose: () => void;
  onFullscreen: () => void;
  onSave: (rawIdea: string) => Promise<void>;
  onExperimentChange?: (experiment: Experiment) => void;
};

function useDebouncedSave(
  value: string,
  onSave: (rawIdea: string) => Promise<void>,
  delayMs: number,
) {
  const [saving, setSaving] = useState(false);
  const first = useRef(true);
  const latest = useRef(onSave);
  latest.current = onSave;

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    setSaving(true);
    const timer = window.setTimeout(() => {
      void latest
        .current(value)
        .catch(() => undefined)
        .finally(() => setSaving(false));
    }, delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return saving;
}

export function SparkExpandedNode({ data }: NodeProps<SparkExpandedData>) {
  const { experiment, onClose, onFullscreen, onSave, onExperimentChange } = data;
  const [idea, setIdea] = useState(experiment.raw_idea ?? "");
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const attachments = useAttachments(experiment.id);
  const saving = useDebouncedSave(idea, onSave, 800);

  useEffect(() => {
    setIdea(experiment.raw_idea ?? "");
  }, [experiment.id, experiment.raw_idea]);

  const refreshExperiment = async () => {
    if (!onExperimentChange) return;
    const updated = await getExperiment(experiment.id);
    onExperimentChange(updated);
  };

  return (
    <div className="w-[560px] bg-surface-card border-2 border-border-master shadow-brutal-lg">
      <div className="bg-ink-primary text-ink-inverse flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <span
            className="material-symbols-outlined text-brand-primary"
            style={{ fontSize: 20 }}
            aria-hidden="true"
          >
            bolt
          </span>
          <span className="font-mono text-mono-md uppercase tracking-wider">
            PHASE 01: SPARK // EXPANDED_VIEW
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onFullscreen}
            aria-label="Enter fullscreen"
            className="p-1 hover:bg-ink-inverse/10"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              open_in_full
            </span>
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="p-1 hover:bg-ink-inverse/10"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              close
            </span>
          </button>
        </div>
      </div>

      {experiment.refinement_started_at ? (
        <div className="mx-5 mt-4 border-2 border-brutalist-yellow bg-brutalist-yellow/20 p-3">
          <p className="font-body text-body-sm text-ink-primary">
            <strong>Note:</strong> You&apos;ve already started Refine. Editing
            your idea won&apos;t automatically re-run it.
          </p>
        </div>
      ) : null}

      <div className="p-5">
        <div className="flex items-center justify-between mb-2">
          <label className="font-label-md text-label-md uppercase text-ink-primary">
            THE IDEA
          </label>
          <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
            {saving ? "SAVING..." : "AUTO-SAVED"}
          </span>
        </div>
        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="What are you thinking of building? Just write it out plainly. Fivvle will help you refine it in the next phase."
          rows={6}
          className="nodrag w-full border-2 border-border-master bg-surface-card p-3 font-body text-body-md placeholder:text-ink-tertiary focus:shadow-brutal-primary focus:outline-none resize-none"
        />
        <p className="mt-2 font-mono text-mono-sm text-ink-tertiary">
          {idea.length} CHARACTERS
        </p>
      </div>

      <div className="p-5 border-t-2 border-border-master">
        <div className="flex items-center justify-between mb-3">
          <label className="font-label-md text-label-md uppercase text-ink-primary">
            ATTACHMENTS ({attachments.items.length})
          </label>
          <div className="relative nodrag">
            <button
              type="button"
              onClick={() => setAddMenuOpen((v) => !v)}
              className="border-2 border-border-master bg-surface-card px-3 py-1 font-label-md text-label-md uppercase shadow-brutal-sm hover:shadow-brutal-md hover:-translate-x-0.5 hover:-translate-y-0.5 transition-all"
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
          <ul className="space-y-2 nodrag">
            {attachments.items.map((att) => (
              <AttachmentRow
                key={att.id}
                attachment={att}
                onDelete={() => {
                  void attachments.remove(att.id).then(() => refreshExperiment());
                }}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
