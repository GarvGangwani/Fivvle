"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, generateInsight } from "@/lib/api";
import { useInsightPaywallGate } from "@/components/wallet/useInsightPaywallGate";
import { isInsightUnlocked, unlockInsight } from "@/lib/wallet-paywall";
import { INSIGHT_PAYWALL_CREDITS } from "@/lib/pricing";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import { useWallet } from "@/lib/wallet-context";

function readApiErrorDetail(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
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
 * Shared generate / regenerate / retry path — mirrors MetricsWidget verbatim
 * (paywall gate → generateInsight → syncWalletAfterPaidAction + 402/502 handling).
 */
export function useSignalGenerateInsight(
  experimentId: string,
  options: {
    onStarted?: () => void;
  } = {},
) {
  const { onStarted } = options;
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitInFlightRef = useRef(false);
  const { requestInsightUnlock, paywallModal } = useInsightPaywallGate();
  const { refresh: refreshWallet, applyWalletPatch } = useWallet();

  const runGenerateInsight = useCallback(async () => {
    if (submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setGenerating(true);
    setError(null);
    try {
      const result = await generateInsight(experimentId);
      await syncWalletAfterPaidAction(
        refreshWallet,
        applyWalletPatch,
        result.credits_balance,
      );
      unlockInsight(experimentId);
      onStarted?.();
    } catch (err) {
      const detail = readApiErrorDetail(err);
      const alreadyRunning =
        err instanceof ApiError &&
        err.status === 409 &&
        typeof detail === "string" &&
        detail.includes("INSIGHT_GENERATING");

      if (err instanceof ApiError && err.status === 409) {
        if (detail?.includes("Insufficient data")) {
          setError(
            "Not enough data yet. You need at least 10 page views, 1 signup, or 7 days live.",
          );
        } else if (alreadyRunning) {
          setError("Insight generation is already running.");
          onStarted?.();
        } else if (detail) {
          setError(detail);
        } else {
          setError("Cannot generate insight in the current experiment state.");
        }
      } else if (err instanceof ApiError && err.status === 402) {
        setError(
          readPaidActionError(err, {
            fallbackRequired: INSIGHT_PAYWALL_CREDITS,
            fallback:
              "Not enough credits to generate the insight report. Open your wallet to buy more.",
          }),
        );
      } else if (err instanceof ApiError && err.status === 502) {
        await refreshWallet();
        setError(readPaidActionError(err));
      } else {
        setError("Could not start insight generation. Please try again.");
      }
    } finally {
      submitInFlightRef.current = false;
      setGenerating(false);
    }
  }, [experimentId, refreshWallet, applyWalletPatch, onStarted]);

  const requestGenerate = useCallback(() => {
    if (generating) return;

    if (isInsightUnlocked(experimentId)) {
      void runGenerateInsight();
      return;
    }

    requestInsightUnlock(async () => {
      await runGenerateInsight();
    });
  }, [experimentId, generating, requestInsightUnlock, runGenerateInsight]);

  return {
    generating,
    error,
    clearError: () => setError(null),
    requestGenerate,
    paywallModal,
    credits: INSIGHT_PAYWALL_CREDITS,
  };
}
