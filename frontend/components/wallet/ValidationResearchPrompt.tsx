"use client";

import { Coins, Sparkles } from "lucide-react";
import { VALIDATION_PAYWALL_CREDITS } from "@/lib/pricing";

interface ValidationResearchPromptProps {
  onStart: () => void;
  loading?: boolean;
}

/**
 * Shown after Chapter 3 (refinement finalize) — prompts user to run validation.
 */
export function ValidationResearchPrompt({
  onStart,
  loading = false,
}: ValidationResearchPromptProps) {
  return (
    <div className="fv-msg-enter mx-auto my-6 w-full max-w-full lg:max-w-[680px]">
      <div className="fv-validation-research-prompt">
        <div className="flex items-start gap-3">
          <span className="fv-validation-research-prompt-icon">
            <Sparkles className="h-5 w-5" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-[var(--fv-text)]">
              Ready to validate your idea?
            </p>
            <p className="mt-1 text-sm leading-relaxed text-[var(--fv-text-muted)]">
              Run deep research, get a structured report, and generate a
              tracked landing page.
            </p>
            <p className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-[var(--fv-text)]">
              <Coins className="h-4 w-4 text-[var(--fv-accent)]" aria-hidden />
              {VALIDATION_PAYWALL_CREDITS} Credits
            </p>
            <button
              type="button"
              onClick={onStart}
              disabled={loading}
              className="fv-btn-primary mt-4 px-4 py-2.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Starting…" : "Run validation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
