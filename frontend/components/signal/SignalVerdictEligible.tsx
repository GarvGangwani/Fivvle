"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useSignalGenerateInsight } from "./useSignalGenerateInsight";

type Props = {
  experimentId: string;
  archived: boolean;
  onInsightStarted: () => void;
};

/** Verdict Eligible — threshold crossed, no insight yet. */
export function SignalVerdictEligible({
  experimentId,
  archived,
  onInsightStarted,
}: Props) {
  const { generating, error, requestGenerate, paywallModal, credits } =
    useSignalGenerateInsight(experimentId, { onStarted: onInsightStarted });

  return (
    <div className="space-y-4">
      <section className="border-2 border-border-master bg-surface-card p-6 shadow-brutal-md">
        <div className="mb-3 inline-block border-2 border-border-master bg-brutalist-yellow px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm">
          Threshold crossed
        </div>
        <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
          Enough signal to draw a verdict
        </h2>
        <p className="mt-3 text-body-md text-ink-secondary">
          Your live page has met the bar for an Insight report — page views,
          signups, or days live. Generate the report when you&apos;re ready.
        </p>

        {archived ? (
          <p className="mt-6 border-2 border-border-master bg-surface-elevated px-3 py-2 font-mono text-mono-sm uppercase text-ink-secondary">
            Archived — generate is unavailable
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
                <Sparkles className="h-4 w-4" aria-hidden />
              )}
              {generating
                ? "Starting insight…"
                : `Generate Insight — ${credits} Credits`}
            </button>
          </>
        )}
      </section>
      {paywallModal}
    </div>
  );
}
