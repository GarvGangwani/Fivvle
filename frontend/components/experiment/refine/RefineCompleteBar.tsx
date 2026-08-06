"use client";

import { useState } from "react";
import { useToast } from "@/components/ui/ToastProvider";
import { completeRefine } from "@/lib/api";
import type { Experiment } from "@/lib/types";

type Props = {
  experiment: Experiment;
  /** Refetches the canvas experiment so Evidence appears without a reload. */
  onCompleted: () => Promise<void>;
};

function hasFinalizedIdea(experiment: Experiment): boolean {
  const idea = experiment.refined_idea;
  if (idea == null) return false;
  if (typeof idea === "string") return idea.trim().length > 0;
  return Boolean(idea.refined_one_liner?.trim() || idea.headline?.trim());
}

/**
 * The founder's explicit "refine is done" step, pinned under the workspace.
 *
 * Separate from FINALIZE REFINEMENT above it: finalizing locks in the idea text
 * and can be repeated, this advances the experiment and reveals Evidence on the
 * canvas. One click, no confirm — it is additive and idempotent.
 */
export function RefineCompleteBar({ experiment, onCompleted }: Props) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);

  if (experiment.refine_completed_at != null) {
    return (
      <div className="shrink-0 border-t-2 border-border-master bg-surface-elevated px-6 py-3">
        <p className="flex items-center justify-center gap-2 font-mono text-mono-sm uppercase text-ink-tertiary">
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 16 }}
            aria-hidden="true"
          >
            check_circle
          </span>
          Evidence unlocked
        </p>
      </div>
    );
  }

  // Evidence research needs a finalized idea to run against, so unlocking it
  // before then would reveal a dead end.
  const ready = hasFinalizedIdea(experiment);

  const handleClick = async () => {
    setBusy(true);
    try {
      await completeRefine(experiment.id);
      await onCompleted();
      toast("Evidence unlocked on the canvas.", "success");
    } catch {
      toast("Could not unlock Evidence. Try again.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="shrink-0 border-t-2 border-border-master bg-surface-card px-6 py-4">
      <button
        type="button"
        onClick={() => void handleClick()}
        disabled={!ready || busy}
        className="flex w-full items-center justify-center gap-2 rounded-sm border-2 border-border-master bg-accent px-6 py-4 font-label-md text-label-md uppercase tracking-wider text-ink-inverse shadow-brutal-md transition-all hover:shadow-brutal-lg enabled:hover:-translate-x-0.5 enabled:hover:-translate-y-0.5 enabled:active:translate-x-0 enabled:active:translate-y-0 enabled:active:shadow-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 18 }}
          aria-hidden="true"
        >
          arrow_forward
        </span>
        {busy ? "UNLOCKING EVIDENCE…" : "DONE REFINING — UNLOCK EVIDENCE"}
      </button>
      <p className="mt-3 text-center font-body text-body-sm text-ink-tertiary">
        {ready
          ? "Adds Evidence to your canvas. Refine stays open — you can keep going."
          : "Finalize your refined idea above first."}
      </p>
    </div>
  );
}
