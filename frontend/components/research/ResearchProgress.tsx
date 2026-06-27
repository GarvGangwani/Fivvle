"use client";

import { useEffect, useRef, useState } from "react";
import { getResearchStatus, ApiError } from "@/lib/api";
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

interface ResearchProgressProps {
  experimentId: string;
  onComplete: () => void;
}

const POLL_INTERVAL_MS = 3000;

export function ResearchProgress({
  experimentId,
  onComplete,
}: ResearchProgressProps) {
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const completedNotifiedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const notifyCompleteOnce = () => {
      if (completedNotifiedRef.current) return;
      completedNotifiedRef.current = true;
      onComplete();
    };

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
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? "Could not load research status. Retrying…"
            : "Could not load research status.",
        );
      }
    }

    completedNotifiedRef.current = false;
    void poll();
    intervalId = setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [experimentId, onComplete]);

  const currentPhase = resolveResearchPhase(status?.status);
  const isComplete = isResearchComplete(status?.status);

  return (
    <div className="mx-auto max-w-lg">
      <div className="mb-6">
        <h2 className="text-[16px] font-bold text-[var(--fv-text)]">
          {isComplete ? "Research complete" : "Research in progress"}
        </h2>
        <p className="mt-1 text-[14px] text-[var(--fv-text-muted)]">
          This usually takes 2–4 minutes. You can leave this page — we&apos;ll
          email you when it&apos;s done.
        </p>
        {status?.phase_label && (
          <p className="mt-3 text-sm font-medium text-[var(--fv-accent)]">
            {status.phase_label}
          </p>
        )}
      </div>

      {error && (
        <p className="mb-4 text-center text-sm text-[var(--fv-warning)]">{error}</p>
      )}

      <div className="fv-card p-6">
        <PhaseIndicator
          currentPhase={currentPhase}
          phases={[...RESEARCH_PHASE_IDS]}
        />
      </div>
    </div>
  );
}
