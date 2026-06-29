"use client";

import { Coins, Sparkles } from "lucide-react";
import { INSIGHT_PAYWALL_CREDITS } from "@/lib/pricing";

interface InsightUnlockPromptProps {
  onStart: () => void;
  loading?: boolean;
  variant?: "view" | "generate";
}

/**
 * Shown before the insight report is unlocked (Insight stage or Metrics CTA).
 */
export function InsightUnlockPrompt({
  onStart,
  loading = false,
  variant = "view",
}: InsightUnlockPromptProps) {
  const isGenerate = variant === "generate";

  return (
    <div className="fv-validation-research-prompt">
      <div className="flex items-start gap-3">
        <span className="fv-validation-research-prompt-icon">
          <Sparkles className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-base font-semibold text-[var(--fv-text)]">
            {isGenerate
              ? "Ready for your insight report?"
              : "Unlock your insight report"}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-[var(--fv-text-muted)]">
            {isGenerate
              ? "Generate a combined cognitive and behavioral report with a clear proceed, iterate, pivot, or kill recommendation."
              : "View your combined research and landing page findings with an AI recommendation and key takeaways."}
          </p>
          <p className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-[var(--fv-text)]">
            <Coins className="h-4 w-4 text-[var(--fv-accent)]" aria-hidden />
            {INSIGHT_PAYWALL_CREDITS} Credits
          </p>
          <button
            type="button"
            onClick={onStart}
            disabled={loading}
            className="fv-btn-primary mt-4 px-4 py-2.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading
              ? isGenerate
                ? "Starting…"
                : "Unlocking…"
              : isGenerate
                ? "Generate insight"
                : "Unlock insight"}
          </button>
        </div>
      </div>
    </div>
  );
}
