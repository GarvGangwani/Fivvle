"use client";

import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { getResearchStatus, ApiError } from "@/lib/api";
import type { ResearchStatus } from "@/lib/types";
import {
  PhaseIndicator,
  RESEARCH_PHASE_IDS,
} from "./PhaseIndicator";

const POLL_INTERVAL_MS = 3000;

const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

interface InlineResearchProgressProps {
  experimentId: string;
  onComplete?: () => void;
}

export function InlineResearchProgress({
  experimentId,
  onComplete,
}: InlineResearchProgressProps) {
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function poll() {
      try {
        const data = await getResearchStatus(experimentId);
        if (cancelled) return;

        setStatus(data);
        setError(null);

        if (data.status === "RESEARCH_READY") {
          if (intervalId) clearInterval(intervalId);
          onComplete?.();
        } else if (data.status === "RESEARCH_FAILED") {
          if (intervalId) clearInterval(intervalId);
        }
      } catch {
        if (cancelled) return;
        setError("Could not load research status. Retrying…");
      }
    }

    poll();
    intervalId = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [experimentId, onComplete]);

  const isComplete = status?.status === "RESEARCH_READY";
  const isFailed = status?.status === "RESEARCH_FAILED";

  const currentPhase =
    status && RESEARCH_ACTIVE_STATUSES.has(status.status)
      ? status.status
      : isComplete
        ? "RESEARCH_SYNTHESIZING"
        : "RESEARCHING";

  return (
    <div className="border-b border-[var(--fv-border)] py-6">
      <div className="mx-auto max-w-[680px]">
        <div className="flex items-start gap-3">
          <div
            className="fv-f-logo"
            style={{ width: 24, height: 24, fontSize: 12 }}
            aria-hidden
          >
            F
          </div>
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              Fivvle
            </span>
            <div className="fv-msg-ai">
              <div className="mb-3 flex items-center gap-2">
                <Activity className="h-[14px] w-[14px] text-[var(--fv-accent)]" />
                <span className="text-[13px] font-bold text-[var(--fv-accent)]">
                  {isComplete
                    ? "Research Complete"
                    : isFailed
                      ? "Research Failed"
                      : "Deep Research Running"}
                </span>
              </div>

              {!isFailed && (
                <PhaseIndicator
                  currentPhase={isComplete ? "RESEARCH_SYNTHESIZING" : currentPhase}
                  phases={[...RESEARCH_PHASE_IDS]}
                  variant="inline"
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
