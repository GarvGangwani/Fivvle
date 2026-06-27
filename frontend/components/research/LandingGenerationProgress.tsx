"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check } from "lucide-react";
import { getExperiment } from "@/lib/api";

const POLL_INTERVAL_MS = 2000;
const FAILURE_CONFIRM_POLLS = 2;

interface LandingGenerationProgressProps {
  experimentId: string;
  onComplete: () => void;
  onFailed?: () => void;
}

const STAGES = [
  "Analyzing your research and building strategy…",
  "Writing conversion copy for each section…",
] as const;

export function LandingGenerationProgress({
  experimentId,
  onComplete,
  onFailed,
}: LandingGenerationProgressProps) {
  const [activeStage, setActiveStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onFailedRef = useRef(onFailed);
  const researchReadyStreakRef = useRef(0);

  useEffect(() => {
    onCompleteRef.current = onComplete;
    onFailedRef.current = onFailed;
  }, [onComplete, onFailed]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setActiveStage(1);
    }, 45000);
    return () => clearTimeout(timer);
  }, []);

  const pollStatus = useCallback(async () => {
    const data = await getExperiment(experimentId);

    if (data.status === "LANDING_DRAFT" || data.status === "LANDING_LIVE") {
      researchReadyStreakRef.current = 0;
      onCompleteRef.current();
      return "done" as const;
    }

    if (data.status === "LANDING_GENERATING") {
      researchReadyStreakRef.current = 0;
      return "generating" as const;
    }

    if (data.status === "RESEARCH_READY") {
      researchReadyStreakRef.current += 1;
      if (researchReadyStreakRef.current >= FAILURE_CONFIRM_POLLS) {
        setError("Landing page generation failed. Please try again.");
        onFailedRef.current?.();
        return "failed" as const;
      }
      return "generating" as const;
    }

    researchReadyStreakRef.current = 0;
    return "generating" as const;
  }, [experimentId]);

  useEffect(() => {
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function poll() {
      try {
        const result = await pollStatus();
        if (cancelled) return;
        if (result === "done" || result === "failed") {
          if (intervalId) clearInterval(intervalId);
        }
      } catch {
        if (!cancelled) {
          setError("Could not check generation status. Retrying…");
        }
      }
    }

    void poll();
    intervalId = setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [pollStatus]);

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
                      ? "text-fv-success"
                      : state === "active"
                        ? "text-[var(--fv-text)]"
                        : "text-fv-text-dim"
                  }`}
                >
                  {label}
                </span>
                {state === "completed" && (
                  <Check className="h-[13px] w-[13px] shrink-0 text-fv-success" />
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
