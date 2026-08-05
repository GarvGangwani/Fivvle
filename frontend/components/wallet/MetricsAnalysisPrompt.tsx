"use client";

import { BarChart3, Coins } from "lucide-react";
import { METRICS_PAYWALL_CREDITS } from "@/lib/pricing";

interface MetricsAnalysisPromptProps {
  onStart: () => void;
  loading?: boolean;
}

/**
 * Shown on the Metrics stage before behavioral analysis is unlocked.
 */
export function MetricsAnalysisPrompt({
  onStart,
  loading = false,
}: MetricsAnalysisPromptProps) {
  return (
    <div className="fv-validation-research-prompt">
      <div className="flex items-start gap-3">
        <span className="fv-validation-research-prompt-icon">
          <BarChart3 className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-base font-semibold text-[var(--fv-text)]">
            Your landing page is live
          </p>
          <p className="mt-1 text-sm leading-relaxed text-[var(--fv-text-muted)]">
            Unlock live metrics to see page views, signups, conversion by source,
            and where your waitlist signups are coming from.
          </p>
          <p className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-[var(--fv-text)]">
            <Coins className="h-4 w-4 text-accent" aria-hidden />
            {METRICS_PAYWALL_CREDITS} Credits
          </p>
          <button
            type="button"
            onClick={onStart}
            disabled={loading}
            className="fv-btn-primary mt-4 px-4 py-2.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Unlocking…" : "Analyze metrics"}
          </button>
        </div>
      </div>
    </div>
  );
}
