"use client";

import { useEffect, useState } from "react";
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

interface ResearchProgressProps {
  experimentId: string;
  onComplete: () => void;
}

export function ResearchProgress({
  experimentId,
  onComplete,
}: ResearchProgressProps) {
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
          onComplete();
        } else if (data.status === "RESEARCH_FAILED") {
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

    poll();
    intervalId = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [experimentId, onComplete]);

  const currentPhase =
    status && RESEARCH_ACTIVE_STATUSES.has(status.status)
      ? status.status
      : "RESEARCHING";

  return (
    <div className="mx-auto max-w-lg">
      <div className="mb-8 text-center">
        <h2 className="text-xl font-semibold text-[var(--fv-text)]">
          Research in progress
        </h2>
        <p className="mt-2 text-sm text-[var(--fv-text-muted)]">
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
