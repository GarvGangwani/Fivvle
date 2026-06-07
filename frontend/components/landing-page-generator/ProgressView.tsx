"use client";

import type { JobStatus } from "@/lib/types";

interface ProgressViewProps {
  job: JobStatus | null;
  error: string | null;
  onRetry?: () => void;
}

const STAGES = [
  { min: 0, label: "Queued" },
  { min: 10, label: "Parsing validation report" },
  { min: 30, label: "Extracting customer & market intelligence" },
  { min: 60, label: "Formulating landing page strategy" },
  { min: 75, label: "Writing conversion copy" },
  { min: 90, label: "Generating visual theme" },
  { min: 100, label: "Complete" },
];

export function ProgressView({ job, error, onRetry }: ProgressViewProps) {
  const progress = job?.progress ?? 0;
  const message = job?.message ?? "Initializing pipeline…";
  const status = job?.status ?? "queued";
  const failed = status === "failed" || !!error;

  const activeStage =
    [...STAGES].reverse().find((s) => progress >= s.min) ?? STAGES[0];

  return (
    <div className="mx-auto w-full max-w-2xl space-y-10">
      <div className="space-y-2 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">
          {failed ? "Generation failed" : "Generating your landing page"}
        </h2>
        <p className="text-[var(--fv-text-muted)]">
          {failed
            ? "The AI pipeline could not complete. Your output was not saved as a successful generation."
            : "Section-routed extractors run in parallel — no full-report prompting."}
        </p>
      </div>

      <div
        className={`fv-card p-8 ${
          failed ? "border-red-500/40 bg-red-500/5" : ""
        }`}
      >
        {!failed && (
          <>
            <div className="mb-6 flex items-center justify-between text-sm">
              <span className="font-medium text-[var(--fv-accent)]">
                {activeStage.label}
              </span>
              <span className="text-[var(--fv-text-muted)]">{progress}%</span>
            </div>
            <div className="mb-6 h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(progress, 100)}%`,
                  background: "linear-gradient(90deg, #06b6d4, #3b82f6)",
                }}
              />
            </div>
          </>
        )}

        <p className="font-mono text-sm text-[var(--fv-text-soft)]">
          {failed ? job?.error ?? error : message}
        </p>
        <p className="mt-2 text-xs uppercase tracking-wider text-[var(--fv-text-muted)]">
          Status: {status}
        </p>

        {failed && (
          <div className="mt-6 space-y-3">
            <p className="text-sm text-red-300">
              {job?.message ??
                error ??
                "AI generation failed. Please retry. If this persists, contact support."}
            </p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="fv-btn-primary px-6 py-2.5 text-sm"
              >
                Retry generation
              </button>
            )}
          </div>
        )}
      </div>

      {!failed && (
        <ul className="space-y-3">
          {STAGES.slice(1, -1).map((stage) => {
            const done = progress > stage.min;
            const current = activeStage.min === stage.min;
            return (
              <li
                key={stage.min}
                className={`flex items-center gap-3 text-sm ${
                  done
                    ? "text-emerald-400"
                    : current
                      ? "text-[var(--fv-text)]"
                      : "text-[var(--fv-text-muted)]"
                }`}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
                    done
                      ? "bg-emerald-500/20"
                      : current
                        ? "bg-[var(--fv-accent-muted)]"
                        : "bg-white/5"
                  }`}
                  style={current ? { animation: "fv-pulse-dot 1.5s infinite" } : undefined}
                >
                  {done ? "✓" : current ? "…" : ""}
                </span>
                {stage.label}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
