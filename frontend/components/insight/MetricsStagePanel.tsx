"use client";

import { useEffect, useState } from "react";
import { DistributeSection } from "@/components/distribution/DistributeSection";
import { MetricsWidget } from "@/components/insight/MetricsWidget";
import { MetricsAnalysisPrompt } from "@/components/wallet/MetricsAnalysisPrompt";
import { useMetricsPaywallGate } from "@/components/wallet/useMetricsPaywallGate";
import { getMetricsAccess, unlockMetrics } from "@/lib/api";
import { shouldShowMetricsAnalysisPrompt } from "@/lib/metrics-flow";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import { METRICS_PAYWALL_CREDITS } from "@/lib/wallet-paywall";
import { useWallet } from "@/lib/wallet-context";
import { ErrorBanner } from "@/components/ui/ErrorBanner";

interface MetricsStagePanelProps {
  experimentId: string;
  experimentStatus: string;
  experimentName: string;
  landingSlug: string | null;
  showDistribute: boolean;
  onInsightStarted: () => void;
}

function readUnlockError(err: unknown): string {
  return readPaidActionError(err, {
    fallbackRequired: METRICS_PAYWALL_CREDITS,
    fallback: "Could not unlock metrics. Please try again.",
  });
}

export function MetricsStagePanel({
  experimentId,
  experimentStatus,
  experimentName,
  landingSlug,
  showDistribute,
  onInsightStarted,
}: MetricsStagePanelProps) {
  const [metricsUnlocked, setMetricsUnlocked] = useState(false);
  const [accessLoading, setAccessLoading] = useState(true);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const { refresh, applyWalletPatch } = useWallet();
  const { requestMetricsAnalysis, paywallModal } = useMetricsPaywallGate();

  useEffect(() => {
    let cancelled = false;
    setAccessLoading(true);
    void getMetricsAccess(experimentId)
      .then(({ unlocked }) => {
        if (cancelled) return;
        setMetricsUnlocked(unlocked);
      })
      .catch(() => {
        if (!cancelled) {
          setMetricsUnlocked(false);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAccessLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const showPrompt = shouldShowMetricsAnalysisPrompt(
    experimentStatus,
    metricsUnlocked,
  );

  function handleAnalyzeMetrics() {
    setUnlockError(null);
    requestMetricsAnalysis(async () => {
      try {
        const result = await unlockMetrics(experimentId);
        await syncWalletAfterPaidAction(
          refresh,
          applyWalletPatch,
          result.credits_balance,
        );
        setMetricsUnlocked(true);
      } catch (err) {
        setUnlockError(readUnlockError(err));
        throw err;
      }
    });
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="space-y-4">
        {unlockError ? (
          <ErrorBanner
            message={unlockError}
            onDismiss={() => setUnlockError(null)}
          />
        ) : null}

        {showDistribute && landingSlug && (
          <DistributeSection
            experimentId={experimentId}
            slug={landingSlug}
            experimentName={experimentName}
          />
        )}

        {accessLoading ? (
          <div className="fv-card px-6 py-8 text-center text-sm text-[var(--fv-text-muted)]">
            Checking metrics access…
          </div>
        ) : showPrompt ? (
          <MetricsAnalysisPrompt onStart={handleAnalyzeMetrics} />
        ) : (
          <MetricsWidget
            experimentId={experimentId}
            experimentStatus={experimentStatus}
            onInsightStarted={onInsightStarted}
          />
        )}
      </div>
      {paywallModal}
    </div>
  );
}
