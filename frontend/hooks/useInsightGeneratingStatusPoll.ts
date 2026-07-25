"use client";

import { useEffect } from "react";
import {
  pollIntervalForStatus,
  shouldPollExperimentStatus,
} from "@/lib/experiment-stages";
import type { ExperimentStatus } from "@/lib/types";

/**
 * Polls canvas experiment status while insight generation is in flight.
 * Does not keep a private status copy — calls `onExperimentRefresh` so the
 * canvas remains the single source of truth (same helpers as the retired
 * detail panel: `shouldPollExperimentStatus` / `pollIntervalForStatus`).
 */
export function useInsightGeneratingStatusPoll(options: {
  status: ExperimentStatus;
  /** Overlay open on Signal act. */
  enabled: boolean;
  onExperimentRefresh?: () => Promise<void>;
}): void {
  const { status, enabled, onExperimentRefresh } = options;

  useEffect(() => {
    if (!enabled) return;
    if (status !== "INSIGHT_GENERATING") return;
    if (!shouldPollExperimentStatus(status)) return;
    if (!onExperimentRefresh) return;

    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;
    const intervalMs = pollIntervalForStatus(status);

    const clearPoll = () => {
      if (intervalId != null) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const tick = () => {
      if (cancelled) return;
      if (document.visibilityState !== "visible") return;
      void onExperimentRefresh().catch(() => {
        /* transient — next tick retries */
      });
    };

    const startPolling = () => {
      clearPoll();
      if (cancelled) return;
      intervalId = setInterval(tick, intervalMs);
    };

    const onVisibilityChange = () => {
      if (cancelled) return;
      if (document.visibilityState === "visible") {
        tick();
        startPolling();
      } else {
        clearPoll();
      }
    };

    tick();
    if (document.visibilityState === "visible") {
      startPolling();
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      clearPoll();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [status, enabled, onExperimentRefresh]);
}
