"use client";

import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { Check } from "lucide-react";
import { getExperiment } from "@/lib/api";

const POLL_INTERVAL_MS = 5000;

interface LandingGenerationProgressProps {
  experimentId: string;
  onComplete: () => void;
}

const STAGES = [
  "Analyzing your research and building strategy…",
  "Writing conversion copy for each section…",
] as const;

export function LandingGenerationProgress({
  experimentId,
  onComplete,
}: LandingGenerationProgressProps) {
  const [activeStage, setActiveStage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setActiveStage(1);
    }, 45000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function poll() {
      try {
        const data = await getExperiment(experimentId);
        if (cancelled) return;

        if (data.status === "LANDING_DRAFT" || data.status === "LANDING_LIVE") {
          if (intervalId) clearInterval(intervalId);
          onComplete();
        } else if (data.status === "RESEARCH_READY") {
          if (intervalId) clearInterval(intervalId);
          setError("Landing page generation failed. Please try again.");
        }
      } catch {
        if (!cancelled) {
          setError("Could not check generation status. Retrying…");
        }
      }
    }

    poll();
    intervalId = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [experimentId, onComplete]);

  return (
    <div className="fv-card p-6">
      <h2 className="text-[16px] font-bold text-[var(--fv-text)]">
        Generating your landing page…
      </h2>
      <p className="mt-1 text-[14px] text-[var(--fv-text-muted)]">
        This usually takes 1–2 minutes
      </p>

      <div className="mt-6">
        {STAGES.map((label, index) => {
          const state =
            index < activeStage
              ? "completed"
              : index === activeStage
                ? "active"
                : "pending";
          const isLast = index === STAGES.length - 1;

          return (
            <div key={label}>
              <div className="flex items-center gap-3 py-2.5">
                <span
                  className={`stage-dot ${
                    state === "completed"
                      ? "done"
                      : state === "active"
                        ? "active"
                        : "pending"
                  }`}
                />
                <span
                  className={`flex-1 text-[13px] ${
                    state === "completed"
                      ? "text-[#34D399]"
                      : state === "active"
                        ? "text-[var(--fv-text)]"
                        : "text-[#475569]"
                  }`}
                >
                  {label}
                </span>
                {state === "completed" && (
                  <Check className="h-[13px] w-[13px] shrink-0 text-[#10B981]" />
                )}
                {state === "active" && <span className="fv-stage-spinner" />}
              </div>
              {!isLast && (
                <div
                  className="ml-[3px] h-px"
                  style={{ background: "rgba(255,255,255,0.04)" }}
                />
              )}
            </div>
          );
        })}
      </div>

      {error && (
        <p className="mt-4 text-sm text-[var(--fv-warning)]">{error}</p>
      )}
    </div>
  );
}
