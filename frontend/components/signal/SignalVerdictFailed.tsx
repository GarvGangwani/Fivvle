"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useSignalGenerateInsight } from "./useSignalGenerateInsight";

type Props = {
  experimentId: string;
  archived: boolean;
  onInsightStarted: () => void;
};

/**
 * Verdict Failed — retry uses the same credit path as first generation.
 *
 * Client cannot tell dispatch-failure (refunded) from a later job failure
 * (not refunded). Copy states both cases and points at the wallet.
 */
export function SignalVerdictFailed({
  experimentId,
  archived,
  onInsightStarted,
}: Props) {
  const { generating, error, requestGenerate, paywallModal, credits } =
    useSignalGenerateInsight(experimentId, { onStarted: onInsightStarted });

  return (
    <div className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md">
      <div className="mb-3 inline-block border-2 border-border-master bg-surface-elevated px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-status-critical shadow-brutal-sm">
        Failed
      </div>
      <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
        Insight generation failed
      </h2>
      <p className="mt-3 text-body-md text-ink-secondary">
        Something went wrong while building the report. You can retry when
        you&apos;re ready.
      </p>
      <p className="mt-3 text-body-sm text-ink-secondary">
        Retry costs {credits} credits when the previous run was charged. If the
        attempt never started (dispatch failure), those credits were refunded
        automatically — check your wallet balance.
      </p>

      {archived ? (
        <p className="mt-6 border-2 border-border-master bg-surface-elevated px-3 py-2 font-mono text-mono-sm uppercase text-ink-secondary">
          Archived — retry is unavailable
        </p>
      ) : (
        <>
          {error ? (
            <p
              role="alert"
              className="mt-4 border-2 border-border-master bg-surface-elevated px-3 py-2 text-body-sm text-ink-secondary"
            >
              {error}
            </p>
          ) : null}
          <button
            type="button"
            onClick={requestGenerate}
            disabled={generating}
            className="mt-6 flex w-full items-center justify-center gap-2 border-2 border-border-master bg-brutalist-yellow px-5 py-3 font-label-md text-label-md uppercase tracking-wider text-ink-primary shadow-brutal-md transition-transform enabled:hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="h-4 w-4" aria-hidden />
            )}
            {generating
              ? "Starting retry…"
              : `Retry Insight — ${credits} Credits`}
          </button>
        </>
      )}
      {paywallModal}
    </div>
  );
}
