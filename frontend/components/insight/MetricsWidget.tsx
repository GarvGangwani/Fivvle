"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  BarChart3,
  Loader2,
  MapPin,
  MousePointerClick,
  Sparkles,
  Users,
} from "lucide-react";
import {
  generateInsight,
  getExperimentAnalytics,
  ApiError,
} from "@/lib/api";
import type { ExperimentAnalytics, SignupLocationBucket } from "@/lib/types";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { useInsightPaywallGate } from "@/components/wallet/useInsightPaywallGate";
import {
  canRequestInsightGeneration,
  isInsightGenerationInProgress,
} from "@/lib/insight-flow";
import {
  INSIGHT_PAYWALL_CREDITS,
  isInsightUnlocked,
} from "@/lib/wallet-paywall";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import { useWallet } from "@/lib/wallet-context";

const POLL_INTERVAL_MS = 15000;

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

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function formatLocation(bucket: SignupLocationBucket): string {
  const parts = [bucket.city, bucket.region, bucket.country].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "Unknown";
}

interface MetricsWidgetProps {
  experimentId: string;
  experimentStatus: string;
  onInsightStarted?: () => void;
}

export function MetricsWidget({
  experimentId,
  experimentStatus,
  onInsightStarted,
}: MetricsWidgetProps) {
  const [analytics, setAnalytics] = useState<ExperimentAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generationRequested, setGenerationRequested] = useState(false);
  const [insightUnlocked, setInsightUnlocked] = useState(false);
  const prevStatusRef = useRef(experimentStatus);
  const submitInFlightRef = useRef(false);
  const { requestInsightUnlock, paywallModal } = useInsightPaywallGate();
  const { refresh: refreshWallet, applyWalletPatch } = useWallet();

  useEffect(() => {
    setInsightUnlocked(isInsightUnlocked(experimentId));
  }, [experimentId]);

  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = experimentStatus;

    if (isInsightGenerationInProgress(experimentStatus)) {
      setGenerationRequested(true);
      return;
    }

    if (
      prev === "INSIGHT_GENERATING" &&
      (experimentStatus === "INSIGHT_READY" ||
        experimentStatus === "INSIGHT_FAILED")
    ) {
      setGenerationRequested(false);
    }
  }, [experimentStatus]);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await getExperimentAnalytics(experimentId);
      setAnalytics(data);
      setError(null);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        setError("Could not load metrics.");
      }
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    loadAnalytics();
    const intervalId = setInterval(loadAnalytics, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [loadAnalytics]);

  async function runGenerateInsight() {
    if (!analytics || !analytics.insight_threshold_met) return;
    if (submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setGenerating(true);
    setGenerationRequested(true);
    setError(null);
    try {
      const result = await generateInsight(experimentId);
      await syncWalletAfterPaidAction(
        refreshWallet,
        applyWalletPatch,
        result.credits_balance,
      );
      setInsightUnlocked(true);
      onInsightStarted?.();
    } catch (err) {
      const detail = readApiErrorDetail(err);
      const alreadyRunning =
        err instanceof ApiError &&
        err.status === 409 &&
        typeof detail === "string" &&
        detail.includes("INSIGHT_GENERATING");
      if (!alreadyRunning) {
        setGenerationRequested(false);
      }
      if (err instanceof ApiError && err.status === 409) {
        if (detail?.includes("Insufficient data")) {
          setError(
            "Not enough data yet. You need at least 10 page views, 1 signup, or 7 days live.",
          );
        } else if (alreadyRunning) {
          setError(
            "Insight generation is already running. Open the Insight tab to check progress.",
          );
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
  }

  function handleGenerateInsight() {
    if (!analytics || !analytics.insight_threshold_met) return;
    if (
      generating ||
      generationRequested ||
      isInsightGenerationInProgress(experimentStatus)
    ) {
      return;
    }

    if (insightUnlocked) {
      void runGenerateInsight();
      return;
    }

    requestInsightUnlock(async () => {
      await runGenerateInsight();
    });
  }

  if (loading) {
    return <LoadingState label="Loading metrics…" />;
  }

  if (!analytics) {
    return (
      <div className="fv-card px-6 py-8 text-center">
        <p className="text-sm text-[var(--fv-text-muted)]">
          {error ?? "Metrics will appear once your landing page is live."}
        </p>
      </div>
    );
  }

  const thresholdMet = analytics.insight_threshold_met;
  const insightGenerating =
    isInsightGenerationInProgress(experimentStatus) || generationRequested;
  const canGenerateInsight =
    canRequestInsightGeneration(experimentStatus) &&
    thresholdMet &&
    !generationRequested &&
    !generating;
  const sources = Object.keys(analytics.views_by_source).sort(
    (a, b) => (analytics.views_by_source[b] ?? 0) - (analytics.views_by_source[a] ?? 0),
  );

  return (
    <div className="fv-section-card">
      <div className="mb-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-[var(--fv-text)]">
          <BarChart3 className="h-5 w-5 text-[var(--fv-accent)]" />
          Live metrics
        </h2>
        <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
          {analytics.days_live === 0
            ? "Published today"
            : `${analytics.days_live} day${analytics.days_live === 1 ? "" : "s"} live`}
          {" · "}
          Share your link to gather behavioral signal.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-4">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            <MousePointerClick className="h-3.5 w-3.5" />
            Page views
          </div>
          <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-[var(--fv-text)]">
            {analytics.total_page_views.toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-4">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            <Users className="h-3.5 w-3.5" />
            Signups
          </div>
          <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-[var(--fv-text)]">
            {analytics.total_signups.toLocaleString()}
          </p>
        </div>
        <div className="col-span-2 rounded-xl border border-[color-mix(in_srgb,var(--fv-accent)_25%,transparent)] bg-[color-mix(in_srgb,var(--fv-accent)_8%,transparent)] p-4 sm:col-span-1">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            Conversion rate
          </p>
          <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-[var(--fv-accent)]">
            {formatPercent(analytics.conversion_rate)}
          </p>
        </div>
      </div>

      {sources.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 text-sm font-semibold text-[var(--fv-text)]">
            Source breakdown
          </h3>
          <div className="space-y-2">
            {sources.map((source) => {
              const views = analytics.views_by_source[source] ?? 0;
              const signups = analytics.signups_by_source[source] ?? 0;
              const rate = analytics.conversion_rate_by_source[source] ?? 0;
              return (
                <div
                  key={source}
                  className="fv-card flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
                >
                  <span className="font-medium text-[var(--fv-text-soft)]">{source}</span>
                  <span className="font-mono text-[var(--fv-text-muted)]">
                    {views} views · {signups} signups · {formatPercent(rate)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {(analytics.signups_by_location ?? []).length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--fv-text)]">
            <MapPin className="h-4 w-4 text-[var(--fv-accent)]" />
            Signup locations
          </h3>
          <div className="space-y-2">
            {(analytics.signups_by_location ?? []).map((bucket, index) => (
              <div
                key={`${bucket.city ?? ""}-${bucket.region ?? ""}-${bucket.country ?? ""}-${index}`}
                className="fv-card flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
              >
                <span className="font-medium text-[var(--fv-text-soft)]">
                  {formatLocation(bucket)}
                </span>
                <span className="font-mono text-[var(--fv-text-muted)]">
                  {bucket.count} signup{bucket.count === 1 ? "" : "s"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <ErrorBanner message={error} className="mt-4" />}

      <div className="mt-6 border-t border-[var(--fv-border)] pt-6">
        {insightGenerating ? (
          <div className="flex items-center gap-2 text-sm text-[var(--fv-text-muted)]">
            <Loader2 className="h-4 w-4 animate-spin text-[var(--fv-accent)]" />
            Generating insight report… Check the Insight tab for progress.
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={handleGenerateInsight}
              disabled={!canGenerateInsight || generating}
              className="fv-btn-primary w-full justify-center px-5 py-2.5 text-sm sm:w-auto disabled:cursor-not-allowed"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {generating
                ? "Starting insight…"
                : experimentStatus === "INSIGHT_READY" ||
                    experimentStatus === "INSIGHT_FAILED"
                  ? "Regenerate insight"
                  : insightUnlocked
                    ? "Generate insight"
                    : `Unlock & generate — ${INSIGHT_PAYWALL_CREDITS} Credits`}
            </button>
            {!thresholdMet && (
              <p className="mt-2 text-xs text-[var(--fv-text-muted)]">
                Waiting for enough signal to generate an insight report.
              </p>
            )}
          </>
        )}
      </div>
      {paywallModal}
    </div>
  );
}
