"use client";

import { useEffect, useState } from "react";
import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

type Props = {
  projectName?: string | null;
};

export function ExperimentLoadingScreen({ projectName }: Props) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setProgress((p) => {
        if (p >= 80) return p;
        return Math.min(80, p + Math.random() * 15);
      });
    }, 200);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas-bg p-6">
      <div className="pointer-events-none absolute inset-0 canvas-grid-bg opacity-30" />

      <div className="relative flex w-full max-w-md flex-col gap-6 rounded-lg border-2 border-border-master bg-surface-card p-8 shadow-brutal-lg">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-col">
            <span className="mb-2 font-mono text-mono-sm uppercase tracking-wider text-brand-primary">
              OPENING WORKSPACE
            </span>
            {projectName ? (
              <h2 className="font-display text-headline-lg uppercase leading-tight tracking-tight text-ink-primary">
                {projectName}
              </h2>
            ) : (
              <BrutalistSkeleton variant="block" height="h-8" width="w-48" />
            )}
          </div>
          <div className="mt-2 flex shrink-0 gap-1">
            <span className="h-2 w-2 animate-pulse bg-brand-primary" />
            <span className="h-2 w-2 bg-brand-primary/40" />
            <span className="h-2 w-2 bg-brand-primary/10" />
          </div>
        </div>

        <div className="w-full">
          <div className="relative h-4 w-full overflow-hidden rounded-sm border-2 border-border-master bg-surface-card">
            <div
              className="h-full bg-brand-primary transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between">
            <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
              LOADING CANVAS
            </span>
            <span className="font-mono text-mono-sm font-bold tabular-nums text-ink-primary">
              {Math.floor(progress)}%
            </span>
          </div>
        </div>

        <div className="flex items-end justify-between border-t-2 border-border-master/20 pt-4">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 animate-ping bg-brand-primary" />
            <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
              FIVVLE
            </span>
          </div>
          <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
            v1.0
          </span>
        </div>
      </div>
    </div>
  );
}
