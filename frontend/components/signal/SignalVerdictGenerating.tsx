"use client";

import { Loader2 } from "lucide-react";

/** Verdict Generating — status poll in SignalStagePanel drives completion. */
export function SignalVerdictGenerating() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 border-2 border-border-master bg-surface-card px-6 py-16 shadow-brutal-md">
      <div className="inline-block border-2 border-border-master bg-brutalist-yellow px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm">
        Generating
      </div>
      <Loader2
        className="h-8 w-8 animate-spin text-ink-primary"
        aria-hidden
      />
      <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
        Writing your insight report
      </h2>
      <p className="max-w-md text-center text-body-md text-ink-secondary">
        Combining research and live-page behavior. This usually takes a minute
        or two — leave this open.
      </p>
    </div>
  );
}
