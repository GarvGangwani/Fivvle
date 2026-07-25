"use client";

import { Loader2, RefreshCw } from "lucide-react";
import type { FounderDecision } from "@/lib/types";
import { SignalFounderDecisionPanel } from "./SignalFounderDecisionPanel";
import { SignalInsightReport } from "./SignalInsightReport";
import { useSignalGenerateInsight } from "./useSignalGenerateInsight";

type Props = {
  experimentId: string;
  archived: boolean;
  founderDecision: FounderDecision | null;
  founderDecisionAt: string | null;
  founderDecisionNote: string | null;
  founderDecisionVersion: number | null;
  onInsightStarted: () => void;
  onDecisionRecorded: () => void;
};

/**
 * Verdict Ready — report + founder decision + regenerate.
 * Regenerate re-debits insightReport credits every time — cost is on the control.
 */
export function SignalVerdictReady({
  experimentId,
  archived,
  founderDecision,
  founderDecisionAt,
  founderDecisionNote,
  founderDecisionVersion,
  onInsightStarted,
  onDecisionRecorded,
}: Props) {
  const { generating, error, requestGenerate, paywallModal, credits } =
    useSignalGenerateInsight(experimentId, { onStarted: onInsightStarted });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-border-master pb-4">
        <div>
          <div className="mb-2 inline-block border-2 border-border-master bg-brutalist-yellow px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm">
            Ready
          </div>
          <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
            Insight report
          </h2>
        </div>

        {archived ? (
          <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
            Archived — read-only
          </p>
        ) : (
          <div className="flex flex-col items-stretch gap-1 sm:items-end">
            <button
              type="button"
              onClick={requestGenerate}
              disabled={generating}
              className="flex items-center justify-center gap-2 border-2 border-border-master bg-surface-card px-4 py-2 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-transform enabled:hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <RefreshCw className="h-4 w-4" aria-hidden />
              )}
              {generating
                ? "Starting…"
                : `Regenerate — ${credits} Credits`}
            </button>
            <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
              Charges {credits} credits each run
            </p>
          </div>
        )}
      </div>

      {error ? (
        <p
          role="alert"
          className="border-2 border-border-master bg-surface-elevated px-3 py-2 text-body-sm text-ink-secondary"
        >
          {error}
        </p>
      ) : null}

      <SignalInsightReport experimentId={experimentId} />

      <SignalFounderDecisionPanel
        experimentId={experimentId}
        archived={archived}
        initialDecision={founderDecision}
        initialAt={founderDecisionAt}
        initialNote={founderDecisionNote}
        initialVersion={founderDecisionVersion}
        onRecorded={onDecisionRecorded}
      />

      {paywallModal}
    </div>
  );
}
