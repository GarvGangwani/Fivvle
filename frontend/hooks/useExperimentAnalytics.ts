"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getExperimentAnalytics } from "@/lib/api";
import type { ExperimentAnalytics } from "@/lib/types";

const POLL_INTERVAL_MS = 15000;

export type UseExperimentAnalytics = {
  data: ExperimentAnalytics | null;
  /** True only for the first fetch of a given enabled session — not background polls. */
  loading: boolean;
  error: string | null;
  /** Set on terminal 409/404; polling stopped. Detail from `err.body` when present. */
  notAvailable: string | null;
  refetch: () => void;
};

function readApiErrorDetail(err: ApiError): string | null {
  const body = err.body;
  if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    typeof (body as { detail: unknown }).detail === "string"
  ) {
    return (body as { detail: string }).detail;
  }
  return null;
}

/**
 * Polls GET /experiments/{id}/analytics every 15s while `enabled`.
 * No threshold math — returns server fields as sent.
 */
export function useExperimentAnalytics(
  experimentId: string,
  enabled: boolean,
): UseExperimentAnalytics {
  const [data, setData] = useState<ExperimentAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notAvailable, setNotAvailable] = useState<string | null>(null);
  const [refetchEpoch, setRefetchEpoch] = useState(0);

  const terminalRef = useRef(false);
  const initialFetchDoneRef = useRef(false);
  const sessionKeyRef = useRef<string | null>(null);

  const refetch = useCallback(() => {
    terminalRef.current = false;
    setNotAvailable(null);
    setError(null);
    setRefetchEpoch((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!enabled) {
      sessionKeyRef.current = null;
      initialFetchDoneRef.current = false;
      return;
    }

    const sessionKey = experimentId;
    const isNewSession = sessionKeyRef.current !== sessionKey;
    sessionKeyRef.current = sessionKey;

    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;
    terminalRef.current = false;

    if (isNewSession) {
      initialFetchDoneRef.current = false;
      setData(null);
      setError(null);
      setNotAvailable(null);
      setLoading(true);
    }

    const clearPoll = () => {
      if (intervalId != null) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const markTerminal = (detail: string) => {
      terminalRef.current = true;
      setNotAvailable(detail);
      setError(null);
      clearPoll();
    };

    const fetchOnce = async () => {
      if (cancelled || terminalRef.current) return;
      if (
        typeof document !== "undefined" &&
        document.visibilityState !== "visible"
      ) {
        return;
      }

      try {
        const next = await getExperimentAnalytics(experimentId);
        if (cancelled) return;
        setData(next);
        setError(null);
        setNotAvailable(null);
      } catch (err) {
        if (cancelled) return;

        if (err instanceof ApiError) {
          // Terminal: archived / not-live — do not retry.
          if (err.status === 409 || err.status === 404) {
            markTerminal(
              readApiErrorDetail(err) ?? "Analytics are not available.",
            );
            return;
          }

          // Transient: network (status 0) or server error — keep data, retry next tick.
          if (err.status === 0 || err.status >= 500) {
            setError(
              readApiErrorDetail(err) ??
                (err.status === 0
                  ? "Network error. Retrying…"
                  : "Could not load analytics. Retrying…"),
            );
            return;
          }
        }

        // Other unexpected errors: surface and keep polling (transient).
        setError(
          err instanceof Error ? err.message : "Could not load analytics.",
        );
      } finally {
        if (!cancelled && !initialFetchDoneRef.current) {
          initialFetchDoneRef.current = true;
          setLoading(false);
        }
      }
    };

    const startPolling = () => {
      clearPoll();
      if (cancelled || terminalRef.current) return;
      intervalId = setInterval(() => {
        void fetchOnce();
      }, POLL_INTERVAL_MS);
    };

    const onVisibilityChange = () => {
      if (cancelled || terminalRef.current) return;
      if (document.visibilityState === "visible") {
        void fetchOnce().then(() => {
          if (!cancelled && !terminalRef.current) startPolling();
        });
      } else {
        clearPoll();
      }
    };

    void fetchOnce().then(() => {
      if (
        !cancelled &&
        !terminalRef.current &&
        document.visibilityState === "visible"
      ) {
        startPolling();
      }
    });

    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      clearPoll();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [experimentId, enabled, refetchEpoch]);

  return { data, loading, error, notAvailable, refetch };
}
