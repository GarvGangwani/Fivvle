"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { archiveExperiment, ApiError } from "@/lib/api";
import type { FounderDecision } from "@/lib/types";

const DECISIONS: {
  id: FounderDecision;
  label: string;
  description: string;
  destructive?: boolean;
  primary?: boolean;
}[] = [
  {
    id: "iterate",
    label: "Iterate",
    description:
      "Refine the landing page or positioning and keep collecting signal before committing.",
  },
  {
    id: "proceed",
    label: "Move forward",
    description:
      "Validation looks promising — proceed to build the MVP or next experiment phase.",
    primary: true,
  },
  {
    id: "pivot",
    label: "Pivot",
    description:
      "Shift the idea based on what you learned. This archives the current experiment.",
    destructive: true,
  },
  {
    id: "kill",
    label: "Kill",
    description:
      "Stop pursuing this idea. The experiment will be archived with a kill outcome.",
    destructive: true,
  },
];

interface DecisionPanelProps {
  experimentId: string;
  onDecision: (decision: FounderDecision) => void;
}

export function DecisionPanel({
  experimentId,
  onDecision,
}: DecisionPanelProps) {
  const [submitting, setSubmitting] = useState<FounderDecision | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDecision(decision: FounderDecision) {
    const option = DECISIONS.find((d) => d.id === decision);
    if (option?.destructive) {
      const confirmed = window.confirm(
        decision === "kill"
          ? "Are you sure you want to kill this experiment? This cannot be undone."
          : "Are you sure you want to pivot? This will archive the current experiment.",
      );
      if (!confirmed) return;
    }

    setSubmitting(decision);
    setError(null);
    try {
      await archiveExperiment(experimentId, decision);
      onDecision(decision);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Could not save your decision. Please try again."
          : "Could not save your decision. Please try again.",
      );
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <section className="fv-card p-6">
      <h2 className="text-lg font-semibold text-[var(--fv-text)]">Your decision</h2>
      <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
        What do you want to do next based on this insight?
      </p>

      {error && (
        <p className="mt-4 text-sm text-red-300">{error}</p>
      )}

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {DECISIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            disabled={submitting !== null}
            onClick={() => handleDecision(option.id)}
            className={`flex flex-col p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
              option.primary
                ? "fv-btn-primary flex-col items-start rounded-xl"
                : option.destructive
                  ? "fv-btn-ghost rounded-xl border-[rgba(239,68,68,0.3)] hover:border-[rgba(239,68,68,0.5)] hover:text-red-300"
                  : "fv-btn-ghost rounded-xl"
            }`}
          >
            <span className="flex items-center gap-2 text-sm font-semibold">
              {submitting === option.id && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {option.label}
            </span>
            <span
              className={`mt-2 text-xs leading-relaxed ${
                option.primary
                  ? "text-fv-bg/70"
                  : "text-[var(--fv-text-muted)]"
              }`}
            >
              {option.description}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
