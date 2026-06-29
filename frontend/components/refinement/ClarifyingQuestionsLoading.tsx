"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import "./refinement-ascent.css";

interface ClarifyingQuestionsLoadingProps {
  questionNumber: number;
  phase?: "submitting" | "syncing";
  onRetry?: () => void;
}

/** Shown while waiting for the next clarifying question — not the chat typing indicator. */
export function ClarifyingQuestionsLoading({
  questionNumber,
  phase = "submitting",
  onRetry,
}: ClarifyingQuestionsLoadingProps) {
  const [showSlowHint, setShowSlowHint] = useState(false);

  useEffect(() => {
    setShowSlowHint(false);
    const timer = window.setTimeout(() => setShowSlowHint(true), 25_000);
    return () => window.clearTimeout(timer);
  }, [questionNumber, phase]);

  const statusLabel =
    phase === "syncing"
      ? "Checking for your next question…"
      : "Preparing your next question…";

  return (
    <div className="fv-msg-enter mx-auto w-full max-w-full lg:max-w-[42rem] ra-clarify-wrap">
      <div className="ra-clarify-panel ra-clarify-panel-loading" aria-busy="true">
        <div className="ra-clarify-header">
          <h3 className="ra-clarify-title">Sharpen your idea</h3>
          <p className="ra-clarify-count">Question {questionNumber}</p>
        </div>

        <div className="ra-questions-loading-body">
          <div className="ra-questions-loading-skeleton" aria-hidden>
            <div className="ra-questions-loading-line ra-questions-loading-line-title" />
            <div className="ra-questions-loading-option" />
            <div className="ra-questions-loading-option" />
            <div className="ra-questions-loading-option ra-questions-loading-option-short" />
          </div>

          <div className="ra-questions-loading-status">
            <Loader2 className="h-4 w-4 animate-spin text-[var(--fv-accent)]" />
            <span>{statusLabel}</span>
          </div>

          {showSlowHint && (
            <div className="ra-questions-loading-slow">
              <p className="ra-questions-loading-slow-text">
                {phase === "syncing"
                  ? "Still waiting on Fivvle. You can refresh to pull the latest questions."
                  : "This is taking longer than usual. Fivvle is still working on your next question."}
              </p>
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="fv-btn-ghost px-3 py-1.5 text-sm"
                >
                  Refresh
                </button>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
