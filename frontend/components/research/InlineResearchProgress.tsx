"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, CheckCircle2 } from "lucide-react";
import { getResearchStatus } from "@/lib/api";
import type { ResearchStatus } from "@/lib/types";
import {
  isResearchComplete,
  isResearchFailed,
  isResearchInProgress,
  resolveResearchPhase,
} from "@/lib/research-status";
import {
  PhaseIndicator,
  RESEARCH_PHASE_IDS,
} from "./PhaseIndicator";
import { ResearchActivityFeed } from "./ResearchActivityFeed";
import { useResearchActivityLog } from "./useResearchActivityLog";
import { FivvleLogo } from "@/components/layout/FivvleLogo";

const POLL_INTERVAL_MS = 3000;

interface InlineResearchProgressProps {
  experimentId: string;
  onComplete?: () => void;
  /** When true, show completed bar immediately (report already exists). */
  reportReady?: boolean;
}

export function InlineResearchProgress({
  experimentId,
  onComplete,
  reportReady = false,
}: InlineResearchProgressProps) {
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const completedNotifiedRef = useRef(false);

  useEffect(() => {
    const notifyCompleteOnce = () => {
      if (completedNotifiedRef.current) return;
      completedNotifiedRef.current = true;
      onComplete?.();
    };

    if (reportReady) {
      notifyCompleteOnce();
      return;
    }

    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function poll() {
      try {
        const data = await getResearchStatus(experimentId);
        if (cancelled) return;

        setStatus(data);
        setError(null);

        if (isResearchComplete(data.status)) {
          if (intervalId) clearInterval(intervalId);
          notifyCompleteOnce();
        } else if (isResearchFailed(data.status)) {
          if (intervalId) clearInterval(intervalId);
        }
      } catch {
        if (cancelled) return;
        setError("Could not load research status. Retrying…");
      }
    }

    completedNotifiedRef.current = false;
    void poll();
    intervalId = setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [experimentId, onComplete, reportReady]);

  const apiStatus = status?.status;
  const isComplete = reportReady || isResearchComplete(apiStatus);
  const isFailed = isResearchFailed(apiStatus);
  const isRunning = isResearchInProgress(apiStatus);

  const currentPhase = isComplete
    ? "RESEARCH_READY"
    : resolveResearchPhase(apiStatus);

  const activityLines = useResearchActivityLog(status, isComplete, isRunning);

  return (
    <div className="border-b border-[var(--fv-border)] py-6">
      <div className="mx-auto max-w-[680px]">
        <div className="flex items-start gap-3">
          <FivvleLogo size={24} />
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              Fivvle
            </span>
            <div className="fv-msg-ai">
              <div className="mb-3 flex items-center gap-2">
                {isComplete ? (
                  <CheckCircle2 className="h-[14px] w-[14px] text-[var(--fv-success)]" />
                ) : (
                  <Activity
                    className={`h-[14px] w-[14px] ${
                      isFailed
                        ? "text-[var(--fv-warning)]"
                        : "text-[var(--fv-accent)]"
                    }`}
                  />
                )}
                <span
                  className={`text-[13px] font-bold ${
                    isComplete
                      ? "text-[var(--fv-success)]"
                      : isFailed
                        ? "text-[var(--fv-warning)]"
                        : "text-[var(--fv-accent)]"
                  }`}
                >
                  {isComplete
                    ? "Research complete"
                    : isFailed
                      ? "Research failed"
                      : isRunning
                        ? "Deep research running"
                        : "Preparing research…"}
                </span>
              </div>

              {!isFailed && (
                <PhaseIndicator
                  currentPhase={currentPhase}
                  phases={[...RESEARCH_PHASE_IDS]}
                  variant="horizontal"
                />
              )}

              {!isFailed && (isRunning || isComplete) && (
                <ResearchActivityFeed
                  lines={activityLines}
                  isComplete={isComplete}
                />
              )}

              {isComplete && (
                <p className="mt-3 text-[14px] leading-relaxed text-[var(--fv-text-soft)]">
                  Your market validation report is ready. Review the findings and
                  recommendation before generating your landing page.
                </p>
              )}

              {isFailed && (
                <p className="text-[14px] text-[var(--fv-warning)]">
                  {status?.error_detail ??
                    "Something went wrong during research. Please try again from your experiment page."}
                </p>
              )}

              {error && !isComplete && !isFailed && (
                <p className="mt-2 text-[12px] text-[var(--fv-warning)]">{error}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
