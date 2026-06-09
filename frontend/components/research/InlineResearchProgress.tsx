"use client";

import { useEffect, useState } from "react";
import { Activity, Eye } from "lucide-react";
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
  onViewReport?: () => void;
}

export function InlineResearchProgress({
  experimentId,
  onComplete,
  onViewReport,
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
    <div className="flex justify-start">
      <div className="w-full max-w-[80%]">
        <div className="mb-1.5 flex items-center gap-2">
          <div className="fv-f-logo" style={{ width: 22, height: 22, fontSize: 11 }}>
            F
          </div>
          <span className="text-[12px] font-medium text-fv-text-dim">Fivvle</span>
        </div>
        <div className="fv-msg-ai max-w-full">
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
            <>
              <p className="mt-3 text-[14px] leading-relaxed text-[var(--fv-text-soft)]">
                Your market validation report is ready. Review the findings and
                recommendation before generating your landing page.
              </p>
              {onViewReport && (
                <button
                  type="button"
                  onClick={onViewReport}
                  className="view-report-btn mt-4"
                >
                  <Eye className="h-4 w-4" />
                  View Validation Report
                </button>
              )}
            </>
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
  );
}
