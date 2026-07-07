# Bug 2 — Conversion Rate Mismatch — Investigation Dump

Context: CineFund experiment shows 4 views / 1 signup as 100% on /metrics and 25% on the dashboard card.

## 1. Site A — /metrics tab

**Primary component:** `frontend/components/insight/MetricsWidget.tsx` (rendered by `MetricsStagePanel` when metrics are unlocked)

**Parent shell:** `frontend/components/insight/MetricsStagePanel.tsx`

**Secondary display on same tab:** `frontend/components/distribution/DistributeSection.tsx` (distribution header stats)

**Endpoint(s) called:** `GET /experiments/{id}/analytics` via `getExperimentAnalytics()` in `frontend/lib/api.ts`

**Also called (access gate, not conversion):** `GET /experiments/{id}/metrics-access`, `POST /experiments/{id}/unlock-metrics`

**Conversion expression (MetricsWidget):** `formatPercent(analytics.conversion_rate)` where `formatPercent(rate) => \`${(rate * 100).toFixed(1)}%\``

**Conversion expression (DistributeSection):** same — `formatPercent(analytics.conversion_rate)` with identical helper

**Calculation location:** Backend pre-computes `conversion_rate` (0–1 ratio); frontend multiplies by 100 for display only.

### `frontend/components/insight/MetricsStagePanel.tsx`

```tsx
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
```

### `frontend/components/insight/MetricsWidget.tsx`

```tsx
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

function meetsInsightThreshold(analytics: ExperimentAnalytics): boolean {
  return analytics.total_page_views >= 10 || analytics.total_signups >= 1;
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
    if (!analytics || !meetsInsightThreshold(analytics)) return;
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
    if (!analytics || !meetsInsightThreshold(analytics)) return;
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

  const thresholdMet = meetsInsightThreshold(analytics);
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
                Need at least 10 page views or 1 signup to generate an insight
                report.
              </p>
            )}
          </>
        )}
      </div>
      {paywallModal}
    </div>
  );
}
```

### `frontend/components/distribution/DistributeSection.tsx`

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getExperimentAnalytics, ApiError } from "@/lib/api";
import type { ExperimentAnalytics } from "@/lib/types";
import { ShareLinksPanel } from "./ShareLinksPanel";

const DISTRIBUTION_TIPS = [
  "Post in 2-3 relevant communities where your target users hang out",
  "Share with 10 people who have the problem your idea solves — not just friends",
  "Add the link to your social media bios for passive traffic",
  "Write a short post explaining the problem, not your solution — link at the end",
] as const;

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

interface DistributeSectionProps {
  experimentId: string;
  slug: string;
  experimentName: string;
}

export function DistributeSection({
  experimentId,
  slug,
  experimentName,
}: DistributeSectionProps) {
  const [analytics, setAnalytics] = useState<ExperimentAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await getExperimentAnalytics(experimentId);
      setAnalytics(data);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        setAnalytics(null);
      }
    } finally {
      setAnalyticsLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    void loadAnalytics();
    const intervalId = setInterval(loadAnalytics, 15000);
    return () => clearInterval(intervalId);
  }, [loadAnalytics]);

  return (
    <section
      id="distribute"
      className="fv-card mb-4 shrink-0 scroll-mt-6 p-4 sm:p-5"
      aria-labelledby="distribute-heading"
    >
      <div className="mb-4">
        <h2
          id="distribute-heading"
          className="text-base font-semibold text-[var(--fv-text)]"
        >
          Drive traffic to your page
        </h2>
        <p className="mt-1 text-[13px] text-[var(--fv-text-muted)]">
          Share your landing page to collect real interest signals
        </p>
      </div>

      {analyticsLoading ? (
        <div className="mb-4 flex items-center gap-2 text-[13px] text-[var(--fv-text-muted)]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading metrics…
        </div>
      ) : analytics ? (
        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-[var(--fv-text-soft)]">
          <span>
            <span className="font-mono font-semibold text-[var(--fv-accent)]">
              {analytics.total_page_views.toLocaleString()}
            </span>
            {" views"}
          </span>
          <span className="text-[var(--fv-text-dim)]">·</span>
          <span>
            <span className="font-mono font-semibold text-[var(--fv-accent)]">
              {analytics.total_signups.toLocaleString()}
            </span>
            {" signups"}
          </span>
          <span className="text-[var(--fv-text-dim)]">·</span>
          <span>
            <span className="font-mono font-semibold text-[var(--fv-accent)]">
              {formatPercent(analytics.conversion_rate)}
            </span>
            {" conversion"}
          </span>
        </div>
      ) : null}

      <ShareLinksPanel slug={slug} experimentName={experimentName} />

      <div className="mt-5 border-t border-[var(--fv-border)] pt-4">
        <p className="mb-2 text-[12px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
          Quick tips
        </p>
        <ul className="space-y-2 text-[13px] text-[var(--fv-text-soft)]">
          {DISTRIBUTION_TIPS.map((tip) => (
            <li key={tip} className="flex gap-2">
              <span className="shrink-0 text-[var(--fv-accent)]" aria-hidden>
                →
              </span>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
```

### `frontend/lib/api.ts` (relevant exports)

```typescript
export async function getExperimentAnalytics(
  id: string,
): Promise<ExperimentAnalytics> {
  return apiFetch<ExperimentAnalytics>(`/experiments/${id}/analytics`);
}
export async function getMetricsAccess(
  experimentId: string,
): Promise<MetricsAccessResponse> {
  return apiFetch<MetricsAccessResponse>(
    `/experiments/${experimentId}/metrics-access`,
  );
}
export async function unlockMetrics(
  experimentId: string,
): Promise<UnlockMetricsResponse> {
  return apiFetch<UnlockMetricsResponse>(
    `/experiments/${experimentId}/unlock-metrics`,
    { method: "POST", body: {} },
  );
}
```

### `frontend/lib/types.ts` (relevant types)

```typescript
export interface ExperimentAnalytics {
  total_page_views: number;
  total_signups: number;
  unique_visitors: number;
  conversion_rate: number;
  views_by_source: Record<string, number>;
  signups_by_source: Record<string, number>;
  conversion_rate_by_source: Record<string, number>;
  signups_by_location: SignupLocationBucket[];
  days_live: number;
  warm_network_bias_index?: number;
}

export interface ResearchTakeaway {
  claim: string;
  cited_finding_ids: string[];
  source_type: TakeawaySourceType;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface TrafficSummary {
  narrative: string;
  headline_metric: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
  source_type: TakeawaySourceType;
}

export interface ConversionSourceCommentary {
  source_name: string;
  views: number;
  signups: number;
  conversion_rate: number;
  commentary: string;
  confidence: "high" | "medium" | "low";
}

export interface ConversionBySource {
  per_source: ConversionSourceCommentary[];
  warm_network_bias_commentary: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface InsightReport {
  traffic_summary: TrafficSummary;
  conversion_by_source: ConversionBySource;
  research_takeaways: ResearchTakeaway[];
  recommendation_type: InsightRecommendationType;
  recommendation: string;
  recommendation_confidence: "high" | "medium" | "low";
  recommendation_rationale: string;
  what_would_change_this: string;
}

export interface GenerateInsightResponse {
  experiment_id: string;
  status: string;
  credits_balance: number;
}

export interface ArchiveExperimentResponse {
  experiment_id: string;
  status: string;
}

export interface DeleteExperimentResponse {
  experiment_id: string;
  deleted: boolean;
}
export interface SignupLocationBucket {
  city: string | null;
  region: string | null;
  country: string | null;
  count: number;
}

export interface ExperimentAnalytics {
  total_page_views: number;
  total_signups: number;
  unique_visitors: number;
  conversion_rate: number;
  views_by_source: Record<string, number>;
  signups_by_source: Record<string, number>;
  conversion_rate_by_source: Record<string, number>;
  signups_by_location: SignupLocationBucket[];
  days_live: number;
  warm_network_bias_index?: number;
}

export interface ResearchTakeaway {
  claim: string;
  cited_finding_ids: string[];
  source_type: TakeawaySourceType;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface TrafficSummary {
  narrative: string;
  headline_metric: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
  source_type: TakeawaySourceType;
}

export interface ConversionSourceCommentary {
  source_name: string;
  views: number;
  signups: number;
  conversion_rate: number;
  commentary: string;
  confidence: "high" | "medium" | "low";
}

export interface ConversionBySource {
  per_source: ConversionSourceCommentary[];
  warm_network_bias_commentary: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface InsightReport {
  traffic_summary: TrafficSummary;
  conversion_by_source: ConversionBySource;
  research_takeaways: ResearchTakeaway[];
  recommendation_type: InsightRecommendationType;
  recommendation: string;
  recommendation_confidence: "high" | "medium" | "low";
  recommendation_rationale: string;
  what_would_change_this: string;
}

export interface GenerateInsightResponse {
  experiment_id: string;
  status: string;
  credits_balance: number;
}

export interface ArchiveExperimentResponse {
  experiment_id: string;
  status: string;
}

export interface DeleteExperimentResponse {
  experiment_id: string;
  deleted: boolean;
}
```

## 2. Site B — Dashboard card

**Primary component:** `frontend/components/dashboard/ProjectCard.tsx`

**List page:** `frontend/components/dashboard/DashboardContent.tsx` calls `listExperiments()`

**Endpoint(s) called:** `GET /experiments` via `listExperiments()` in `frontend/lib/api.ts`

**Fields read:** `experiment.card_stats.page_views`, `experiment.card_stats.waitlist_signups`

**Conversion expression:** `formatConversion(stats.page_views, stats.waitlist_signups)` where `formatConversion(views, signups) => views <= 0 ? "—" : `\`${((signups / views) * 100).toFixed(1)}%\``

**Calculation location:** Frontend divides signups by page_views (raw row counts from API); no `conversion_rate` field on list response.

### `frontend/components/dashboard/DashboardContent.tsx`

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Archive, Lightbulb, Plus, Sparkles } from "lucide-react";
import { listExperiments, ApiError } from "@/lib/api";
import type { ExperimentSummary } from "@/lib/types";
import { ProjectCard } from "./ProjectCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { PageHeader } from "@/components/ui/PageHeader";

type LoadState =
  | { status: "loading" }
  | { status: "success"; experiments: ExperimentSummary[] }
  | { status: "error"; message: string };

function ProjectGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="fv-skeleton h-52 rounded-2xl" />
      ))}
    </div>
  );
}

export function DashboardContent() {
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  const fetchExperiments = useCallback(async () => {
    try {
      const experiments = await listExperiments();
      setLoadState({ status: "success", experiments });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        return;
      }
      if (err instanceof ApiError) {
        setLoadState({
          status: "error",
          message: "Could not load projects. Please try again.",
        });
      } else {
        setLoadState({
          status: "error",
          message: "Could not load projects. Please try again.",
        });
      }
    }
  }, []);

  useEffect(() => {
    void fetchExperiments();
  }, [fetchExperiments]);

  if (loadState.status === "loading") {
    return (
      <div className="p-4 sm:p-6">
        <div className="fv-skeleton mb-8 h-10 w-48 rounded-lg" />
        <ProjectGridSkeleton />
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="flex items-center justify-center p-6 py-20">
        <ErrorBanner message={loadState.message} className="max-w-md" />
      </div>
    );
  }

  const { experiments } = loadState;

  if (experiments.length === 0) {
    return (
      <EmptyState
        icon={<Lightbulb className="h-7 w-7 text-[var(--fv-accent)]" />}
        title="No projects yet"
        description="Start your first validation — describe an idea and Fivvle will research the market, generate a landing page, and measure real interest."
        action={
          <Link
            href="/new"
            className="fv-btn-primary inline-flex items-center gap-2 px-6 py-2.5 text-sm no-underline"
          >
            <Sparkles className="h-4 w-4" />
            Create your first project
          </Link>
        }
      />
    );
  }

  return (
    <div className="p-4 sm:p-6">
      <PageHeader
        title="Your projects"
        description="Track validation progress across research, landing pages, and behavioral signal."
        actions={
          <Link
            href="/new"
            className="fv-btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm no-underline"
          >
            <Plus className="h-4 w-4" />
            New project
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {experiments.map((experiment) => (
          <ProjectCard
            key={experiment.id}
            experiment={experiment}
            onClick={() => router.push(`/experiment/${experiment.id}`)}
          />
        ))}

        <Link
          href="/new"
          className="fv-project-card fv-project-card-add no-underline"
        >
          <div className="flex flex-col items-center gap-2 text-[var(--fv-text-muted)]">
            <Plus className="h-8 w-8" />
            <span className="text-sm font-medium">New project</span>
          </div>
        </Link>
      </div>

      <div className="mt-8 border-t border-[var(--fv-border)] pt-6">
        <Link
          href="/archived"
          className="inline-flex items-center gap-2 text-sm text-[var(--fv-text-muted)] no-underline transition-colors hover:text-[var(--fv-text)]"
        >
          <Archive className="h-4 w-4" />
          View archived projects
        </Link>
      </div>
    </div>
  );
}
```

### `frontend/components/dashboard/ProjectCard.tsx`

```tsx
"use client";

import { ArrowRight, BarChart3, Coins, Eye, Lock, MousePointerClick, Users } from "lucide-react";
import type { ExperimentSummary } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format-time";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { METRICS_PAYWALL_CREDITS } from "@/lib/pricing";
import { StatusBadge } from "./StatusBadge";

const LIVE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
]);

const STAGE_HINTS: Record<string, string> = {
  DRAFT: "Idea captured",
  REFINING: "AI refinement in progress",
  REFINED: "Ready to start research",
  RESEARCHING: "Market research running",
  RESEARCH_PLANNING: "Planning research",
  RESEARCH_SEARCHING: "Searching sources",
  RESEARCH_READING: "Reading sources",
  RESEARCH_REFLECTING: "Reflecting on findings",
  RESEARCH_SYNTHESIZING: "Writing validation report",
  RESEARCH_READY: "Validation report ready",
  RESEARCH_FAILED: "Research needs attention",
  LANDING_GENERATING: "Generating landing page",
  LANDING_DRAFT: "Landing page ready to publish",
  LANDING_LIVE: "Live — collecting traffic",
  INSIGHT_GENERATING: "Generating insight report",
  INSIGHT_READY: "Insight report ready",
  INSIGHT_FAILED: "Insight generation failed",
  COMPLETED: "Validation complete",
  ARCHIVED: "Archived",
};

function formatCount(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (value >= 10_000) {
    return `${Math.round(value / 1000)}k`;
  }
  if (value >= 1_000) {
    return `${(value / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  }
  return value.toLocaleString();
}

function formatConversion(views: number, signups: number): string {
  if (views <= 0) return "—";
  return `${((signups / views) * 100).toFixed(1)}%`;
}

interface ProjectCardProps {
  experiment: ExperimentSummary;
  onClick: () => void;
}

export function ProjectCard({ experiment, onClick }: ProjectCardProps) {
  const name = getExperimentDisplayName(experiment);
  const stats = experiment.card_stats;
  const isLive = LIVE_STATUSES.has(experiment.status);
  const showStats = isLive && stats != null;
  const showMetricsLocked = isLive && stats == null;
  const stageHint = STAGE_HINTS[experiment.status] ?? "In progress";

  return (
    <button
      type="button"
      onClick={onClick}
      className="fv-project-card group text-left"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="min-w-0 flex-1 truncate text-base font-semibold text-[var(--fv-text)] group-hover:text-[var(--fv-accent)]">
          {name}
        </h3>
        <StatusBadge status={experiment.status} />
      </div>

      <p className="line-clamp-2 min-h-[2.75rem] text-sm leading-relaxed text-[var(--fv-text-muted)]">
        {experiment.raw_idea?.trim() ?? ""}
      </p>

      {showStats ? (
        <div className="fv-project-card-stats">
          <div className="fv-project-stat">
            <Eye className="fv-project-stat-icon" aria-hidden />
            <span className="fv-project-stat-value">{formatCount(stats.page_views)}</span>
            <span className="fv-project-stat-label">Views</span>
          </div>
          <div className="fv-project-stat">
            <Users className="fv-project-stat-icon" aria-hidden />
            <span className="fv-project-stat-value">
              {formatCount(stats.waitlist_signups)}
            </span>
            <span className="fv-project-stat-label">Signups</span>
          </div>
          <div className="fv-project-stat">
            <MousePointerClick className="fv-project-stat-icon" aria-hidden />
            <span className="fv-project-stat-value">
              {formatConversion(stats.page_views, stats.waitlist_signups)}
            </span>
            <span className="fv-project-stat-label">Conv.</span>
          </div>
        </div>
      ) : showMetricsLocked ? (
        <div className="fv-project-metrics-locked" aria-label="Metrics locked">
          <div className="fv-project-metrics-locked-head">
            <span className="fv-project-metrics-locked-icon-wrap">
              <BarChart3 className="h-4 w-4" aria-hidden />
              <Lock className="fv-project-metrics-locked-badge" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--fv-text-soft)]">
                Behavioral metrics locked
              </p>
              <p className="mt-0.5 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                Unlock on the Metrics tab to see views, signups, and conversion.
              </p>
            </div>
          </div>
          <p className="fv-project-metrics-locked-cost">
            <Coins className="h-3.5 w-3.5 text-[var(--fv-accent)]" aria-hidden />
            {METRICS_PAYWALL_CREDITS} Credits
          </p>
        </div>
      ) : (
        <p className="fv-project-stage-hint">{stageHint}</p>
      )}

      <div className="fv-project-card-footer">
        <span className="text-xs text-[var(--fv-text-dim)]">
          Updated {formatRelativeTime(experiment.updated_at)}
        </span>
        <ArrowRight className="h-4 w-4 text-[var(--fv-text-dim)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--fv-accent)]" />
      </div>
    </button>
  );
}
```

### `frontend/lib/api.ts` (relevant exports)

```typescript
export async function listExperiments(options?: {
  archived?: boolean;
}): Promise<ExperimentSummary[]> {
  const params = new URLSearchParams();
  if (options?.archived) {
    params.set("archived", "true");
  }
  const query = params.toString();
  return apiFetch<ExperimentSummary[]>(
    query ? `/experiments?${query}` : "/experiments",
  );
}
```

### `frontend/lib/types.ts` (relevant types)

```typescript
export interface ExperimentCardStats {
  page_views: number;
  waitlist_signups: number;
}

export interface ExperimentSummary {
  id: string;
  slug: string | null;
  name?: string | null;
  raw_idea: string;
  status: string;
  created_at: string;
  updated_at: string;
  card_stats?: ExperimentCardStats | null;
}

export interface ExperimentDetail extends ExperimentSummary {
  refined_idea: RefinedIdea | null;
  landing_page: LandingPageData | null;
  validation_report_id: string | null;
  insight_report_id: string | null;
}

export interface GenerateLandingPageRequest {
  page_goal?: string;
  template_id?: string;
}

export interface GenerateLandingPageResponse {
  experiment_id: string;
  status: string;
}

export interface JobStatus {
  id: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
}

export interface ResearchStatus {
  status: string;
  phase_label: string | null;
  phases_completed: string[];
  last_updated_at: string;
  error_detail: string | null;
}

export interface ExperimentValidationReportSummary {
  overall_recommendation: string | null;
  total_finding_count: number;
  total_citation_count: number;
}

/** GET /experiments/{id} response shape */
export interface Experiment {
  id: string;
  name?: string | null;
  raw_idea?: string | null;
  status: string;
  thread_id?: string | null;
  validation_report: ExperimentValidationReportSummary | null;
}

// --- Clarifying question block (refinement pre-research) ---
export interface ExperimentSummary {
  id: string;
  slug: string | null;
  name?: string | null;
  raw_idea: string;
  status: string;
  created_at: string;
  updated_at: string;
  card_stats?: ExperimentCardStats | null;
}

export interface ExperimentDetail extends ExperimentSummary {
  refined_idea: RefinedIdea | null;
  landing_page: LandingPageData | null;
  validation_report_id: string | null;
  insight_report_id: string | null;
}

export interface GenerateLandingPageRequest {
  page_goal?: string;
  template_id?: string;
}

export interface GenerateLandingPageResponse {
  experiment_id: string;
  status: string;
}

export interface JobStatus {
  id: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
}

export interface ResearchStatus {
  status: string;
  phase_label: string | null;
  phases_completed: string[];
  last_updated_at: string;
  error_detail: string | null;
}

export interface ExperimentValidationReportSummary {
  overall_recommendation: string | null;
  total_finding_count: number;
  total_citation_count: number;
}

/** GET /experiments/{id} response shape */
export interface Experiment {
  id: string;
  name?: string | null;
  raw_idea?: string | null;
  status: string;
  thread_id?: string | null;
  validation_report: ExperimentValidationReportSummary | null;
}

// --- Clarifying question block (refinement pre-research) ---
```

## 3. Backend routes

### `backend/app/routers/experiments.py`

```py
"""Experiment router — POST /experiments, POST /experiments/{id}/refine,
POST /experiments/{id}/confirm, GET /experiments/{id}, GET /experiments/{id}/research-status.

Per .cursorrules «API Design»: router functions are thin (5-15 lines each).
All domain logic lives in app.services.*.

Per AGENTS.md «Authentication and authorization»:
- Authentication: Depends(get_current_user) — verifies Firebase ID token, returns User.
- Authorization (ownership): checked SEPARATELY with an explicit comparison before any
  mutation. Ownership failure returns 404, not 403 — never reveal that the experiment
  exists for a different user.

Per AGENTS.md «Error handling»:
- LLM exceptions → 502 with generic message; full detail goes to structlog + Sentry only.
- Domain exceptions → 409 with specific but non-leaking message.
- ValueError (input) → 400.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.enums import DispatchTrigger, ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.db.models.waitlist_signup import WaitlistSignup
from app.db.session import get_session
from app.dispatchers.dependencies import (
    get_dispatcher_dep,
    get_insight_dispatcher_dep,
    get_landing_page_dispatcher_dep,
)
from app.dispatchers.in_process_landing_page import landing_generation_in_progress
from app.services.landing_page_revalidate import notify_live_landing_page_changed
from app.utils.landing_page_public import is_landing_page_editable, is_public_landing_page_accessible
from app.utils.landing_page_urls import build_public_landing_page_url
from app.utils.wallet_http import debit_for_service_or_raise, refund_for_service
from app.utils.experiment_naming import (
    sync_landing_page_project_name,
    validate_landing_slug,
)
from app.dispatchers.protocol import (
    DispatchError,
    InsightDispatcher,
    LandingPageDispatcher,
    ResearchDispatcher,
)
from app.logging_config import get_logger
from app.pricing import SERVICE_PRICING
from app.reliability.rate_limit import AUTH_RATE_LIMIT, limiter, user_key
from app.schemas.api_responses import (
    AnalyticsResponse,
    ArchiveExperimentResponse,
    ArchiveRequest,
    DeleteExperimentRequest,
    DeleteExperimentResponse,
    InsightReportResponse,
    LandingPagePatchRequest,
    LandingPageResponse,
    LandingPageSlugAvailabilityResponse,
    LogoUploadResponse,
    MetricsAccessResponse,
    SectionImageUploadResponse,
    PublishLandingPageRequest,
    PublishResponse,
    UnlockMetricsResponse,
    ValidationReportResponse,
    WaitlistSignupItem,
    WaitlistSignupsResponse,
)
from app.schemas.experiment import (
    ConfirmResearchResponse,
    CreateExperimentRequest,
    ExperimentListItemResponse,
    ExperimentResponse,
    RegenerateRefinementRequest,
    RenameExperimentRequest,
    ResearchStatusResponse,
)
from app.schemas.validation_report import ValidationReport as ValidationReportSchema
from app.services.analytics_aggregator import (
    LandingPageNotLiveError,
    build_analytics_aggregate,
)
from app.services.dispatch_service import transition_to_researching_and_dispatch
from app.services.experiment_dashboard_stats import build_experiment_card_stats_map
from app.services.experiment_service import (
    InvalidExperimentState,
    RefinementLimitExceeded,
    create_experiment_with_refinement,
    delete_experiment,
    infer_status_after_unarchive,
    regenerate_refinement,
)
from app.services.logo_upload_service import (
    LogoUploadError,
    upload_landing_page_logo,
    upload_landing_page_section_image,
)
from app.services.research_phase_mapping import get_phase_label, get_phases_completed
from app.services.wallet_service import (
    InsufficientCredits,
    get_or_create_wallet,
    has_purchased_service_for_experiment,
    purchase_service_for_experiment,
)
from app.utils.wallet_http import insufficient_credits_http

_logger = get_logger(__name__)

# 30/min/user for the polling endpoint — per the spec.
_RESEARCH_STATUS_RATE_LIMIT = "30/minute"

_WAITLIST_EXPORT_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _ensure_landing_page_editable(experiment: Experiment) -> None:
    """Reject landing-page mutations when archived, generating, or pre-landing."""
    if experiment.status == ExperimentStatus.LANDING_GENERATING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Landing page is regenerating. Try again shortly.",
        )
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived projects cannot be edited.",
        )
    if not is_landing_page_editable(experiment.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Landing page cannot be edited in the current project stage.",
        )


def _ensure_metrics_access_allowed(experiment: Experiment) -> None:
    if experiment.status == ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived projects cannot unlock metrics.",
        )
    if not is_public_landing_page_accessible(experiment.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Metrics are available after your landing page is live.",
        )


_RESEARCH_ACTIVE_STATUSES: frozenset[ExperimentStatus] = frozenset(
    {
        ExperimentStatus.RESEARCHING,
        ExperimentStatus.RESEARCH_PLANNING,
        ExperimentStatus.RESEARCH_SEARCHING,
        ExperimentStatus.RESEARCH_READING,
        ExperimentStatus.RESEARCH_REFLECTING,
        ExperimentStatus.RESEARCH_SYNTHESIZING,
    }
)


async def _get_owned_experiment_for_update(
    db: AsyncSession,
    *,
    experiment_id: UUID,
    user_id: UUID,
) -> Experiment:
    """Load an experiment row with FOR UPDATE for billing-critical transitions."""
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id).with_for_update()
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )
    return experiment


class ExperimentValidationReportSummary(BaseModel):
    """Aggregates for smoke / dashboards — not the full ValidationReport JSON."""

    model_config = ConfigDict(extra="forbid")

    overall_recommendation: str | None = None
    total_finding_count: int = Field(ge=0)
    total_citation_count: int = Field(ge=0)


class GenerateInsightResponse(BaseModel):
    """Response from POST /experiments/{id}/generate-insight.

    Returned with HTTP 202. The actual InsightReport is built asynchronously;
    the frontend polls GET /experiments/{id} for status transitions until
    status reaches INSIGHT_READY or INSIGHT_FAILED.
    """

    model_config = ConfigDict(from_attributes=True)

    experiment_id: UUID
    status: ExperimentStatus = Field(
        description="Set to INSIGHT_GENERATING by this endpoint immediately on dispatch."
    )
    credits_balance: int = Field(ge=0)


class GenerateLandingPageRequest(BaseModel):
    """Optional body for POST /experiments/{id}/generate-landing-page."""

    model_config = ConfigDict(extra="forbid")

    page_goal: str = Field(
        default="waitlist",
        description="Primary conversion goal (waitlist, interest, or contact).",
    )
    template_id: str = Field(
        default="dark-premium",
        description="Designer template ID to apply (e.g. dark-premium, bold-v1).",
    )
    regeneration_hint: str | None = Field(
        default=None,
        description=(
            "Optional nonce/hint to force a distinct regeneration output "
            "(e.g. section name + timestamp)."
        ),
    )


class GenerateLandingPageResponse(BaseModel):
    """Response from POST /experiments/{id}/generate-landing-page.

    Returned with HTTP 202. Landing page copy and layout are built asynchronously;
    the frontend polls GET /experiments/{id} for status transitions until
    status reaches LANDING_DRAFT or returns to RESEARCH_READY on failure.
    """

    model_config = ConfigDict(from_attributes=True)

    experiment_id: UUID
    status: ExperimentStatus = Field(
        description="Set to LANDING_GENERATING by this endpoint immediately on dispatch."
    )


class GetExperimentDetailResponse(BaseModel):
    """GET /experiments/{id} — minimal experiment row + optional report aggregates."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str | None = None
    raw_idea: str
    status: ExperimentStatus
    thread_id: UUID | None = None
    validation_report: ExperimentValidationReportSummary | None = None


def _aggregate_validation_report(raw: dict) -> ExperimentValidationReportSummary:
    qfs = raw.get("questions_and_findings") or []
    finding_count = sum(len(qf.get("findings") or []) for qf in qfs)
    citation_count = 0
    for qf in qfs:
        for f in qf.get("findings") or []:
            citation_count += len(f.get("citations") or [])
    for comp in raw.get("competitors") or []:
        citation_count += len(comp.get("citations") or [])
    rec = raw.get("overall_recommendation")
    if rec is not None and not isinstance(rec, str):
        rec = str(rec)
    return ExperimentValidationReportSummary(
        overall_recommendation=rec,
        total_finding_count=finding_count,
        total_citation_count=citation_count,
    )

router = APIRouter(prefix="/experiments", tags=["experiments"])


# ---------------------------------------------------------------------------
# GET /experiments — list current user's experiments (before /{experiment_id})
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ExperimentListItemResponse], status_code=status.HTTP_200_OK)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def list_experiments(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    archived: Annotated[bool, Query(description="When true, return archived projects only")] = False,
) -> list[ExperimentListItemResponse]:
    query = select(Experiment).where(Experiment.user_id == current_user.id)
    if archived:
        query = query.where(Experiment.status == ExperimentStatus.ARCHIVED)
    else:
        query = query.where(Experiment.status != ExperimentStatus.ARCHIVED)
    result = await db.execute(query.order_by(Experiment.updated_at.desc()))
    experiments = list(result.scalars().all())
    stats_map = await build_experiment_card_stats_map(
        db,
        experiments,
        user_id=current_user.id,
    )

    items: list[ExperimentListItemResponse] = []
    for experiment in experiments:
        base = ExperimentResponse.model_validate(experiment)
        items.append(
            ExperimentListItemResponse(
                **base.model_dump(),
                card_stats=stats_map.get(experiment.id),
            )
        )
    return items


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def create_experiment(
    request: Request,
    response: Response,
    body: CreateExperimentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Experiment:
    user_id = str(current_user.id)  # cache before try — avoids lazy-load on broken session
    try:
        return await create_experiment_with_refinement(
            db,
            current_user,
            body.raw_idea,
            body.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("experiment creation failed", error_type=type(exc).__name__, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Refinement failed, please try again",
        ) from exc


@router.post(
    "/{experiment_id}/refine",
    response_model=ExperimentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def refine_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: RegenerateRefinementRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    # 404 for not found AND wrong owner — never reveal existence to non-owners (AGENTS.md).
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    try:
        return await regenerate_refinement(db, experiment, body.feedback)
    except RefinementLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Regeneration limit reached for this experiment",
        ) from None
    except InvalidExperimentState:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment is not in a state that allows regeneration",
        ) from None
    except Exception as exc:
        _logger.error(
            "experiment regeneration failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Refinement failed, please try again",
        ) from exc


# ---------------------------------------------------------------------------
# POST /experiments/{id}/confirm — trigger research, 202 response
# ---------------------------------------------------------------------------

@router.post(
    "/{experiment_id}/confirm",
    response_model=ConfirmResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def confirm_research(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    dispatcher: Annotated[ResearchDispatcher, Depends(get_dispatcher_dep)],
) -> ConfirmResearchResponse:
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )

    if experiment.status in _RESEARCH_ACTIVE_STATUSES:
        status_url = str(request.url_for("get_research_status", experiment_id=experiment_id))
        wallet = await get_or_create_wallet(db, current_user.id)
        return ConfirmResearchResponse(
            experiment_id=experiment_id,
            status=experiment.status,
            status_url=status_url,
            credits_balance=wallet.credits_balance,
        )

    if experiment.status not in {
        ExperimentStatus.REFINED,
        ExperimentStatus.RESEARCH_FAILED,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in REFINED or RESEARCH_FAILED status to confirm "
                f"research (current: {experiment.status})"
            ),
        )

    await debit_for_service_or_raise(
        db,
        user_id=current_user.id,
        service="fullValidationFlow",
        experiment_id=experiment_id,
    )
    await db.commit()

    try:
        await transition_to_researching_and_dispatch(
            db,
            experiment,
            DispatchTrigger.USER_CONFIRM,
            dispatcher,
        )
    except InvalidExperimentState:
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="fullValidationFlow",
            reason="invalid experiment state",
            experiment_id=experiment_id,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in REFINED or RESEARCH_FAILED status to confirm "
                f"research (current: {experiment.status})"
            ),
        ) from None
    except DispatchError as exc:
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="fullValidationFlow",
            reason="research dispatch failed",
            experiment_id=experiment_id,
        )
        await db.commit()
        _logger.error(
            "dispatch failed",
            error_type=type(exc).__name__,
            experiment_id=str(experiment_id),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start research pipeline, please try again",
        ) from exc

    status_url = str(request.url_for("get_research_status", experiment_id=experiment_id))
    wallet = await get_or_create_wallet(db, current_user.id)
    return ConfirmResearchResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.RESEARCHING,
        status_url=status_url,
        credits_balance=wallet.credits_balance,
    )


async def _check_min_insight_data(
    db: AsyncSession, experiment_id: UUID
) -> tuple[int, int, int]:
    """Compute (page_view_count, signup_count, days_live) for the experiment.

    Returns the triple even when min-data is not met — the caller decides
    whether to raise 409 based on these numbers.

    days_live is 0 when LandingPage is missing or live_at is None — in that
    case the (LANDING_LIVE status precondition) should have blocked the call
    earlier, but we return 0 defensively.
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    from sqlalchemy import func  # noqa: PLC0415

    from app.db.models.landing_page import LandingPage  # noqa: PLC0415
    from app.db.models.page_view import PageView  # noqa: PLC0415
    from app.db.models.waitlist_signup import WaitlistSignup  # noqa: PLC0415

    views_stmt = select(func.count(PageView.id)).where(
        PageView.experiment_id == experiment_id
    )
    signups_stmt = select(func.count(WaitlistSignup.id)).where(
        WaitlistSignup.experiment_id == experiment_id
    )
    landing_stmt = select(LandingPage.live_at).where(
        LandingPage.experiment_id == experiment_id
    )

    views_result = await db.execute(views_stmt)
    signups_result = await db.execute(signups_stmt)
    landing_result = await db.execute(landing_stmt)

    page_view_count = int(views_result.scalar_one() or 0)
    signup_count = int(signups_result.scalar_one() or 0)
    live_at = landing_result.scalar_one_or_none()

    if live_at is None:
        days_live = 0
    else:
        days_live = max((datetime.now(timezone.utc) - live_at).days, 0)

    return page_view_count, signup_count, days_live


@router.post(
    "/{experiment_id}/generate-insight",
    response_model=GenerateInsightResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_insight(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    insight_dispatcher: Annotated[InsightDispatcher, Depends(get_insight_dispatcher_dep)],
) -> GenerateInsightResponse:
    """User-triggered insight generation per b4-insight-generator.md.

    Allowed source statuses: LANDING_LIVE (first generation), INSIGHT_READY (regen),
    INSIGHT_FAILED (retry). Any other status returns 409.

    Min-data guard: at least one of (≥10 page views, ≥1 signup, ≥7 days live).
    Below the threshold → 409 with a guidance message.

    On dispatch, transitions status to INSIGHT_GENERATING and commits before
    awaiting the dispatcher. The dispatcher transitions to terminal state
    (INSIGHT_READY or INSIGHT_FAILED) asynchronously. On DispatchError, rolls
    back to INSIGHT_FAILED and returns 502.
    """
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )

    if experiment.status == ExperimentStatus.INSIGHT_GENERATING:
        wallet = await get_or_create_wallet(db, current_user.id)
        return GenerateInsightResponse(
            experiment_id=experiment_id,
            status=ExperimentStatus.INSIGHT_GENERATING,
            credits_balance=wallet.credits_balance,
        )

    allowed_source_statuses = {
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
    }
    if experiment.status not in allowed_source_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in LANDING_LIVE, INSIGHT_READY, or INSIGHT_FAILED "
                f"status to generate insight (current: {experiment.status.value})."
            ),
        )

    page_view_count, signup_count, days_live = await _check_min_insight_data(
        db, experiment_id
    )
    meets_threshold = (
        page_view_count >= 10 or signup_count >= 1 or days_live >= 7
    )
    if not meets_threshold:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Insufficient data for insight generation. Need at least one of: "
                "10 page views, 1 signup, or 7 days since landing page went live. "
                f"Current: {page_view_count} views, {signup_count} signups, "
                f"{days_live} day(s) live."
            ),
        )

    await debit_for_service_or_raise(
        db,
        user_id=current_user.id,
        service="insightReport",
        experiment_id=experiment_id,
    )

    experiment.status = ExperimentStatus.INSIGHT_GENERATING
    await db.commit()

    try:
        await insight_dispatcher.dispatch(experiment_id)
    except DispatchError as exc:
        _logger.error(
            "insight dispatch failed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        experiment = await _get_owned_experiment_for_update(
            db,
            experiment_id=experiment_id,
            user_id=current_user.id,
        )
        experiment.status = ExperimentStatus.INSIGHT_FAILED
        await refund_for_service(
            db,
            user_id=current_user.id,
            service="insightReport",
            reason="insight dispatch failed",
            experiment_id=experiment_id,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start insight generation, please try again",
        ) from exc

    wallet = await get_or_create_wallet(db, current_user.id)
    return GenerateInsightResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.INSIGHT_GENERATING,
        credits_balance=wallet.credits_balance,
    )


@router.post(
    "/{experiment_id}/generate-landing-page",
    response_model=GenerateLandingPageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def generate_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: GenerateLandingPageRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    landing_page_dispatcher: Annotated[
        LandingPageDispatcher, Depends(get_landing_page_dispatcher_dep)
    ],
) -> GenerateLandingPageResponse:
    """User-triggered landing page generation per ADR 0022.

    Allowed source statuses: RESEARCH_READY (first generation), LANDING_DRAFT
    (regen). LANDING_GENERATING returns 202 idempotently. Any other status
    returns 409.

    On dispatch, transitions status to LANDING_GENERATING and commits before
    awaiting the dispatcher. The dispatcher transitions to terminal state
    (LANDING_DRAFT or RESEARCH_READY on failure) asynchronously. On
    DispatchError, rolls back to RESEARCH_READY and returns 502.
    """
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id)
    )
    experiment = result.scalar_one_or_none()

    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
        )

    stuck_generating = False
    if experiment.status == ExperimentStatus.LANDING_GENERATING:
        settings = get_settings()
        stuck_generating = (
            settings.dispatcher_mode == "in_process"
            and not landing_generation_in_progress(experiment_id)
        )
        if not stuck_generating:
            return GenerateLandingPageResponse(
                experiment_id=experiment_id,
                status=ExperimentStatus.LANDING_GENERATING,
            )

    allowed_source_statuses = {
        ExperimentStatus.RESEARCH_READY,
        ExperimentStatus.LANDING_DRAFT,
        ExperimentStatus.LANDING_LIVE,
    }
    if stuck_generating:
        allowed_source_statuses.add(ExperimentStatus.LANDING_GENERATING)
    if experiment.status not in allowed_source_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Experiment must be in RESEARCH_READY, LANDING_DRAFT, or LANDING_LIVE status "
                f"to generate landing page (current: {experiment.status.value})."
            ),
        )

    was_live = experiment.status == ExperimentStatus.LANDING_LIVE
    experiment.status = ExperimentStatus.LANDING_GENERATING
    await db.commit()

    try:
        await landing_page_dispatcher.dispatch(
            experiment_id,
            body.page_goal,
            body.template_id,
            body.regeneration_hint,
            was_live,
        )
    except DispatchError as exc:
        _logger.error(
            "landing page dispatch failed",
            experiment_id=str(experiment_id),
            error_type=type(exc).__name__,
        )
        experiment.status = ExperimentStatus.RESEARCH_READY
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start landing page generation, please try again",
        ) from exc

    return GenerateLandingPageResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.LANDING_GENERATING,
    )


# ---------------------------------------------------------------------------
# GET /experiments/{id}/research-status — polling endpoint, 30/min/user
# ---------------------------------------------------------------------------


@router.get(
    "/{experiment_id}/research-status",
    response_model=ResearchStatusResponse,
    status_code=status.HTTP_200_OK,
    name="get_research_status",
)
@limiter.limit(_RESEARCH_STATUS_RATE_LIMIT, key_func=user_key)
async def get_research_status(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResearchStatusResponse:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    return ResearchStatusResponse(
        status=experiment.status,
        phase_label=get_phase_label(experiment.status),
        phases_completed=get_phases_completed(experiment.status),
        last_updated_at=experiment.updated_at,
        error_detail=experiment.research_error_detail
        if experiment.status == ExperimentStatus.RESEARCH_FAILED
        else None,
    )


# ---------------------------------------------------------------------------
# Sub-resource reads and mutations (must register before GET /{experiment_id})
# ---------------------------------------------------------------------------


@router.get(
    "/{experiment_id}/validation-report",
    response_model=ValidationReportResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_validation_report(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ValidationReportResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    report_result = await db.execute(
        select(ValidationReport).where(ValidationReport.experiment_id == experiment_id),
    )
    report = report_result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation report not found")

    return ValidationReportSchema.model_validate(report.raw_report)


@router.get(
    "/{experiment_id}/landing-page",
    response_model=LandingPageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    return LandingPageResponse.model_validate(landing_page)


@router.post(
    "/{experiment_id}/landing-page/logo",
    response_model=LogoUploadResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def upload_landing_page_logo_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LogoUploadResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    _ensure_landing_page_editable(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    if lp_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    file_bytes = await file.read()
    try:
        result = upload_landing_page_logo(
            experiment_id=experiment_id,
            user_id=current_user.id,
            file_bytes=file_bytes,
        )
    except LogoUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error(
            "logo upload failed",
            experiment_id=str(experiment_id),
            user_id=str(current_user.id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Logo upload failed. Try again or paste an image URL.",
        ) from exc

    logo_url = result.logo_url
    if logo_url.startswith("/"):
        logo_url = str(request.base_url).rstrip("/") + logo_url

    return LogoUploadResponse(logo_url=logo_url, filename=result.filename)


@router.post(
    "/{experiment_id}/landing-page/section-image",
    response_model=SectionImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def upload_landing_page_section_image_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SectionImageUploadResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    _ensure_landing_page_editable(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    if lp_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    file_bytes = await file.read()
    try:
        result = upload_landing_page_section_image(
            experiment_id=experiment_id,
            user_id=current_user.id,
            file_bytes=file_bytes,
        )
    except LogoUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error(
            "section image upload failed",
            experiment_id=str(experiment_id),
            user_id=str(current_user.id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image upload failed. Try again with a smaller PNG, JPEG, or WebP file.",
        ) from exc

    image_url = result.image_url
    if image_url.startswith("/"):
        image_url = str(request.base_url).rstrip("/") + image_url

    return SectionImageUploadResponse(image_url=image_url, filename=result.filename)


@router.get(
    "/{experiment_id}/landing-page/slug-availability",
    response_model=LandingPageSlugAvailabilityResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def check_landing_page_slug_availability(
    request: Request,
    response: Response,
    experiment_id: UUID,
    slug: Annotated[str, Query(min_length=1, max_length=40)],
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageSlugAvailabilityResponse:
    """Check whether a slug is free for this landing page.

    Compares against all landing pages in the database (unique constraint).
    ``taken_by_live`` is true when another *published* page already uses the slug.
    """
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    try:
        normalized = validate_landing_slug(slug)
    except ValueError as exc:
        return LandingPageSlugAvailabilityResponse(
            slug=slug.strip().lower(),
            available=False,
            taken_by_live=False,
            message=str(exc),
        )

    existing_result = await db.execute(
        select(LandingPage).where(LandingPage.slug == normalized),
    )
    existing = existing_result.scalar_one_or_none()
    if existing is None or existing.id == landing_page.id:
        return LandingPageSlugAvailabilityResponse(
            slug=normalized,
            available=True,
            taken_by_live=False,
            message="This URL is available.",
        )

    taken_by_live = existing.live_at is not None
    message = (
        "This URL is already used by a live published page."
        if taken_by_live
        else "This URL is already taken by another project."
    )
    return LandingPageSlugAvailabilityResponse(
        slug=normalized,
        available=False,
        taken_by_live=taken_by_live,
        message=message,
    )


@router.patch(
    "/{experiment_id}/landing-page",
    response_model=LandingPageResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def patch_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: LandingPagePatchRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LandingPageResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    _ensure_landing_page_editable(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    previous_slug = landing_page.slug

    if body.template_id is not None:
        landing_page.template_id = body.template_id
    if body.copy_json is not None:
        landing_page.copy_json = body.copy_json
    if body.page_json is not None:
        landing_page.page_json = body.page_json
    if body.slug is not None:
        try:
            normalized_slug = validate_landing_slug(body.slug)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        conflict_result = await db.execute(
            select(LandingPage).where(
                LandingPage.slug == normalized_slug,
                LandingPage.id != landing_page.id,
            ),
        )
        if conflict_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This URL is already taken. Choose a different slug.",
            )
        landing_page.slug = normalized_slug

    await db.commit()
    await db.refresh(landing_page)

    if landing_page.live_at is not None and experiment.status != ExperimentStatus.ARCHIVED:
        await notify_live_landing_page_changed(
            db,
            landing_page,
            previous_slug=previous_slug,
        )

    return LandingPageResponse.model_validate(landing_page)


@router.post(
    "/{experiment_id}/landing-page/publish",
    response_model=PublishResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def publish_landing_page(
    request: Request,
    response: Response,
    experiment_id: UUID,
    _body: PublishLandingPageRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PublishResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    if experiment.status != ExperimentStatus.LANDING_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment must be in LANDING_DRAFT status to publish the landing page",
        )

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Landing page not found")

    now = datetime.now(timezone.utc)
    landing_page.live_at = now
    experiment.status = ExperimentStatus.LANDING_LIVE
    await db.commit()
    await db.refresh(landing_page)

    await notify_live_landing_page_changed(db, landing_page)

    public_url = build_public_landing_page_url(landing_page.slug)
    return PublishResponse(
        message="Landing page published",
        slug=landing_page.slug,
        public_url=public_url,
    )


@router.get(
    "/{experiment_id}/metrics-access",
    response_model=MetricsAccessResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_metrics_access(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MetricsAccessResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    unlocked = await has_purchased_service_for_experiment(
        db,
        user_id=current_user.id,
        service="metricsAnalysis",
        experiment_id=experiment_id,
    )
    return MetricsAccessResponse(unlocked=unlocked)


@router.post(
    "/{experiment_id}/unlock-metrics",
    response_model=UnlockMetricsResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def unlock_metrics(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UnlockMetricsResponse:
    experiment = await _get_owned_experiment_for_update(
        db,
        experiment_id=experiment_id,
        user_id=current_user.id,
    )
    _ensure_metrics_access_allowed(experiment)

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None or landing_page.live_at is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not available until the landing page is published",
        )

    try:
        _tx, already_unlocked = await purchase_service_for_experiment(
            db,
            user_id=current_user.id,
            service="metricsAnalysis",
            experiment_id=experiment_id,
        )
    except InsufficientCredits as exc:
        raise insufficient_credits_http(exc) from exc

    await db.commit()
    wallet = await get_or_create_wallet(db, current_user.id)
    return UnlockMetricsResponse(
        unlocked=True,
        already_unlocked=already_unlocked,
        credits_balance=wallet.credits_balance,
    )


@router.get(
    "/{experiment_id}/analytics",
    response_model=AnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_experiment_analytics(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnalyticsResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    if not await has_purchased_service_for_experiment(
        db,
        user_id=current_user.id,
        service="metricsAnalysis",
        experiment_id=experiment_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "metrics_not_unlocked",
                "required": SERVICE_PRICING["metricsAnalysis"],
            },
        )

    try:
        aggregate = await build_analytics_aggregate(db, experiment_id)
    except LandingPageNotLiveError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not available until the landing page is published",
        ) from None

    return AnalyticsResponse(
        total_page_views=aggregate.total_page_views,
        total_signups=aggregate.total_signups,
        unique_visitors=aggregate.unique_visitors,
        conversion_rate=aggregate.conversion_rate,
        views_by_source=aggregate.views_by_source,
        signups_by_source=aggregate.signups_by_source,
        conversion_rate_by_source=aggregate.conversion_rate_by_source,
        signups_by_location=aggregate.signups_by_location,
        days_live=aggregate.days_live,
    )


def _waitlist_export_filename(experiment: Experiment) -> str:
    base = (experiment.name or experiment.slug or str(experiment.id)).strip()
    safe = _WAITLIST_EXPORT_FILENAME_RE.sub("-", base).strip("-._") or "experiment"
    return f"{safe[:80]}-waitlist.csv"


@router.get(
    "/{experiment_id}/waitlist/export",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def export_experiment_waitlist(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    signups_result = await db.execute(
        select(WaitlistSignup)
        .where(WaitlistSignup.experiment_id == experiment_id)
        .order_by(WaitlistSignup.ts.desc()),
    )
    signups = list(signups_result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "source_tag", "city", "region", "country", "signed_up_at"])
    for signup in signups:
        writer.writerow(
            [
                signup.email,
                signup.source_tag or "",
                signup.geo_city or "",
                signup.geo_region or "",
                signup.geo_country or "",
                signup.ts.isoformat(),
            ]
        )

    filename = _waitlist_export_filename(experiment)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{experiment_id}/waitlist",
    response_model=WaitlistSignupsResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def list_experiment_waitlist(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WaitlistSignupsResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    signups_result = await db.execute(
        select(WaitlistSignup)
        .where(WaitlistSignup.experiment_id == experiment_id)
        .order_by(WaitlistSignup.ts.desc()),
    )
    signups = list(signups_result.scalars().all())

    return WaitlistSignupsResponse(
        signups=[
            WaitlistSignupItem(
                id=signup.id,
                email=signup.email,
                source_tag=signup.source_tag,
                geo_city=signup.geo_city,
                geo_region=signup.geo_region,
                geo_country=signup.geo_country,
                created_at=signup.ts,
            )
            for signup in signups
        ],
        total=len(signups),
    )


@router.get(
    "/{experiment_id}/insight-report",
    response_model=InsightReportResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_insight_report(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InsightReportResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    report_result = await db.execute(
        select(InsightReport).where(InsightReport.experiment_id == experiment_id),
    )
    report = report_result.scalar_one_or_none()
    if report is None or report.raw_output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight report not found")

    return InsightReportResponse.model_validate(report.raw_output)


@router.delete(
    "/{experiment_id}",
    response_model=DeleteExperimentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def delete_experiment_endpoint(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: DeleteExperimentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DeleteExperimentResponse:
    """Permanently delete a project. Requires body ``{"confirmation": "CONFIRM"}``."""
    if body.confirmation != "CONFIRM":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Type "CONFIRM" exactly to delete this project',
        )

    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    await delete_experiment(db, experiment)
    await db.commit()

    return DeleteExperimentResponse(experiment_id=experiment_id)


@router.post(
    "/{experiment_id}/archive",
    response_model=ArchiveExperimentResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def archive_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: ArchiveRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArchiveExperimentResponse:
    exp_result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    experiment = exp_result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    if experiment.status == ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment is already archived",
        )

    experiment.status = ExperimentStatus.ARCHIVED
    await db.commit()

    return ArchiveExperimentResponse(
        experiment_id=experiment_id,
        status=ExperimentStatus.ARCHIVED,
    )


@router.post(
    "/{experiment_id}/unarchive",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def unarchive_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    result = await db.execute(
        select(Experiment)
        .options(
            selectinload(Experiment.validation_report),
            selectinload(Experiment.landing_page),
            selectinload(Experiment.insight_report),
        )
        .where(Experiment.id == experiment_id),
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    if experiment.status != ExperimentStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Experiment is not archived",
        )

    experiment.status = infer_status_after_unarchive(experiment)
    await db.commit()

    summary = None
    if experiment.validation_report is not None:
        summary = _aggregate_validation_report(experiment.validation_report.raw_report)

    return GetExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        raw_idea=experiment.raw_idea,
        status=experiment.status,
        thread_id=experiment.thread_id,
        validation_report=summary,
    )


@router.patch(
    "/{experiment_id}/name",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def rename_experiment(
    request: Request,
    response: Response,
    experiment_id: UUID,
    body: RenameExperimentRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment_id),
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    stripped = body.name.strip()
    if not stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name must not be empty",
        )

    experiment.name = stripped

    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id),
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is not None:
        landing_page.page_json = sync_landing_page_project_name(
            landing_page.page_json if isinstance(landing_page.page_json, dict) else {},
            stripped,
        )

    await db.commit()

    summary = None
    if experiment.validation_report is not None:
        summary = _aggregate_validation_report(experiment.validation_report.raw_report)

    return GetExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        raw_idea=experiment.raw_idea,
        status=experiment.status,
        thread_id=experiment.thread_id,
        validation_report=summary,
    )


# ---------------------------------------------------------------------------
# GET /experiments/{id} — owner detail + ValidationReport aggregates (smoke / FE)
# ---------------------------------------------------------------------------


@router.get(
    "/{experiment_id}",
    response_model=GetExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AUTH_RATE_LIMIT, key_func=user_key)
async def get_experiment_detail(
    request: Request,
    response: Response,
    experiment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GetExperimentDetailResponse:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.validation_report))
        .where(Experiment.id == experiment_id),
    )
    experiment = result.scalar_one_or_none()
    if experiment is None or experiment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    summary = None
    if experiment.validation_report is not None:
        summary = _aggregate_validation_report(experiment.validation_report.raw_report)

    return GetExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        raw_idea=experiment.raw_idea,
        status=experiment.status,
        thread_id=experiment.thread_id,
        validation_report=summary,
    )
```

## 4. Backend services

### `backend/app/services/analytics_aggregator.py`

```py
"""Analytics aggregator — derives AnalyticsAggregate from landing-page telemetry.

Pure DB-read service: no LLM calls, no writes, no status transitions.
Produces the structured input contract for the B4 insight generator LLM
(``docs/planning/b4-insight-generator.md`` §4.1).

Per AGENTS.md "Logging hygiene":
    Log experiment_id and aggregate counts only — never emails, IPs, or source_tag
    values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.landing_page import LandingPage
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.integrations.ip_geolocation import location_label
from app.logging_config import get_logger
from app.schemas.insight import AnalyticsAggregate, SignupLocationBucket

_logger = get_logger(__name__)

# v1 heuristic — refine after observing real founder tagging patterns.
# Source tags treated as "warm" for warm_network_bias_index calculation.
# Matching is case-insensitive substring match against source_tag.
WARM_SOURCE_TAG_PATTERNS: tuple[str, ...] = (
    "twitter",
    "linkedin",
    "discord",
    "slack",
    "personal",
    "founder",
    "warm",
    "friends",
    "network",
)


class LandingPageNotLiveError(Exception):
    """Raised when the experiment has no LandingPage with a non-null live_at."""


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_source_tag(source_tag: str | None) -> str:
    return source_tag if source_tag is not None else "unknown"


def _is_warm_source(source_tag: str) -> bool:
    if source_tag == "unknown":
        return False
    lower = source_tag.lower()
    return any(pattern in lower for pattern in WARM_SOURCE_TAG_PATTERNS)


def _percentile_p90(sorted_times: list[int]) -> int:
    idx = int(0.9 * (len(sorted_times) - 1))
    return sorted_times[idx]


def _build_signups_by_location(
    waitlist_signups: list[WaitlistSignup],
) -> list[SignupLocationBucket]:
    counts: dict[tuple[str | None, str | None, str | None], int] = {}
    for signup in waitlist_signups:
        key = (signup.geo_city, signup.geo_region, signup.geo_country)
        counts[key] = counts.get(key, 0) + 1

    buckets = [
        SignupLocationBucket(
            city=city,
            region=region,
            country=country,
            count=count,
        )
        for (city, region, country), count in counts.items()
    ]
    buckets.sort(
        key=lambda bucket: (
            -bucket.count,
            location_label(city=bucket.city, region=bucket.region, country=bucket.country),
        )
    )
    return buckets


async def build_analytics_aggregate(
    db: AsyncSession,
    experiment_id: UUID,
) -> AnalyticsAggregate:
    """Build AnalyticsAggregate from page_views + waitlist_signups + landing_page.

    Raises LandingPageNotLiveError if the experiment has no live landing page
    (the aggregator is meant to be called only after Stage 4 publish).
    """
    lp_result = await db.execute(
        select(LandingPage).where(LandingPage.experiment_id == experiment_id)
    )
    landing_page = lp_result.scalar_one_or_none()
    if landing_page is None or landing_page.live_at is None:
        raise LandingPageNotLiveError(
            f"Experiment {experiment_id} has no published landing page (live_at is null)"
        )

    now = datetime.now(timezone.utc)
    days_live = max(0, (now - landing_page.live_at).days)
    live_date = landing_page.live_at.astimezone(timezone.utc).date()

    pv_result = await db.execute(
        select(PageView)
        .where(PageView.experiment_id == experiment_id)
        .order_by(PageView.ts.asc())
    )
    page_views = list(pv_result.scalars().all())

    ws_result = await db.execute(
        select(WaitlistSignup)
        .where(WaitlistSignup.experiment_id == experiment_id)
        .order_by(WaitlistSignup.ts.asc())
    )
    waitlist_signups = list(ws_result.scalars().all())

    total_page_views = len(page_views)
    total_signups = len(waitlist_signups)

    data_quality_notes: list[str] = []

    non_null_ips = {pv.ip_address for pv in page_views if pv.ip_address is not None}
    if total_page_views > 0 and len(non_null_ips) == 0:
        unique_visitors = total_page_views
        data_quality_notes.append(
            "All page views missing IP address — unique-visitor count falls back to total views."
        )
    else:
        unique_visitors = len(non_null_ips)

    if unique_visitors > 0:
        conversion_rate = _clamp01(total_signups / unique_visitors)
    else:
        conversion_rate = 0.0

    views_by_source: dict[str, int] = {}
    for pv in page_views:
        tag = _normalize_source_tag(pv.source_tag)
        views_by_source[tag] = views_by_source.get(tag, 0) + 1

    signups_by_source: dict[str, int] = {}
    for ws in waitlist_signups:
        tag = _normalize_source_tag(ws.source_tag)
        signups_by_source[tag] = signups_by_source.get(tag, 0) + 1

    conversion_rate_by_source: dict[str, float] = {}
    for tag, view_count in views_by_source.items():
        if view_count > 0:
            rate = signups_by_source.get(tag, 0) / view_count
        else:
            rate = 0.0
        conversion_rate_by_source[tag] = _clamp01(rate)

    if total_page_views > 0:
        warm_view_count = sum(
            count
            for tag, count in views_by_source.items()
            if _is_warm_source(tag)
        )
        warm_network_bias_index = _clamp01(warm_view_count / total_page_views)
    else:
        warm_network_bias_index = 0.0

    non_null_times = [
        pv.time_on_page_sec
        for pv in page_views
        if pv.time_on_page_sec is not None
    ]
    if len(non_null_times) == 0:
        time_on_page_p50_seconds = 0
        time_on_page_p90_seconds = 0
        if total_page_views > 0:
            data_quality_notes.append(
                "No time_on_page data captured — percentiles default to 0."
            )
    else:
        sorted_times = sorted(non_null_times)
        time_on_page_p50_seconds = int(median(sorted_times))
        time_on_page_p90_seconds = _percentile_p90(sorted_times)

    views_by_day: list[int] = []
    signups_by_day: list[int] = []
    for day_idx in range(days_live):
        views_by_day.append(
            sum(
                1
                for pv in page_views
                if (pv.ts.astimezone(timezone.utc).date() - live_date).days == day_idx
            )
        )
        signups_by_day.append(
            sum(
                1
                for ws in waitlist_signups
                if (ws.ts.astimezone(timezone.utc).date() - live_date).days == day_idx
            )
        )

    drop_off_signals: dict[str, str] = {}
    if total_page_views > 50 and total_signups == 0:
        drop_off_signals["zero_conversion"] = (
            "≥50 views with zero signups — check CTA visibility or value proposition clarity"
        )
    if time_on_page_p90_seconds > 0 and time_on_page_p50_seconds == 0:
        drop_off_signals["bimodal_engagement"] = (
            "Engagement distribution is bimodal — half of visitors leave instantly, "
            "the other half spend significant time"
        )

    if total_page_views > 0:
        for tag, count in views_by_source.items():
            if count > 0.9 * total_page_views:
                data_quality_notes.append(
                    f"Traffic concentrated on a single source ({tag}) — "
                    "results may not generalize."
                )
                break

    if days_live > 0 and total_page_views == 0:
        data_quality_notes.append(
            f"Landing page has been live {days_live} day(s) with zero traffic — "
            "distribute the URL before generating insights."
        )

    if total_page_views > 0 and days_live > 0:
        daily_avg = total_page_views / max(days_live, 1)
        spike_threshold = 5 * daily_avg
        for idx, day_views in enumerate(views_by_day):
            if day_views > spike_threshold:
                data_quality_notes.append(
                    f"Day {idx} traffic spike ({day_views} views) is >5x the daily "
                    "average — possible bot or campaign event."
                )

    aggregate = AnalyticsAggregate(
        days_live=days_live,
        total_page_views=total_page_views,
        unique_visitors=unique_visitors,
        total_signups=total_signups,
        conversion_rate=conversion_rate,
        views_by_source=views_by_source,
        signups_by_source=signups_by_source,
        conversion_rate_by_source=conversion_rate_by_source,
        signups_by_location=_build_signups_by_location(waitlist_signups),
        warm_network_bias_index=warm_network_bias_index,
        time_on_page_p50_seconds=time_on_page_p50_seconds,
        time_on_page_p90_seconds=time_on_page_p90_seconds,
        signups_by_day=signups_by_day,
        views_by_day=views_by_day,
        drop_off_signals=drop_off_signals,
        data_quality_notes=data_quality_notes,
    )

    _logger.info(
        "analytics aggregate built",
        experiment_id=str(experiment_id),
        days_live=days_live,
        total_page_views=total_page_views,
        total_signups=total_signups,
        unique_source_count=len(views_by_source),
        warm_network_bias_index=warm_network_bias_index,
    )

    return aggregate
```

### `backend/app/services/experiment_dashboard_stats.py`

```py
"""Batch behavioral metrics for dashboard experiment cards."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ExperimentStatus
from app.db.models.experiment import Experiment
from app.db.models.page_view import PageView
from app.db.models.waitlist_signup import WaitlistSignup
from app.schemas.experiment import ExperimentCardStats
from app.services.wallet_service import list_experiments_with_purchased_service

_LIVE_LANDING_STATUSES = frozenset(
    {
        ExperimentStatus.LANDING_LIVE,
        ExperimentStatus.INSIGHT_GENERATING,
        ExperimentStatus.INSIGHT_READY,
        ExperimentStatus.INSIGHT_FAILED,
        ExperimentStatus.COMPLETED,
    }
)


async def build_experiment_card_stats_map(
    db: AsyncSession,
    experiments: list[Experiment],
    *,
    user_id: UUID,
) -> dict[UUID, ExperimentCardStats]:
    """Return page-view and waitlist counts for live projects with metrics unlocked."""
    live_ids = [exp.id for exp in experiments if exp.status in _LIVE_LANDING_STATUSES]
    if not live_ids:
        return {}

    unlocked_ids = await list_experiments_with_purchased_service(
        db,
        user_id=user_id,
        service="metricsAnalysis",
        experiment_ids=live_ids,
    )
    if not unlocked_ids:
        return {}

    views_stmt = (
        select(PageView.experiment_id, func.count(PageView.id))
        .where(PageView.experiment_id.in_(unlocked_ids))
        .group_by(PageView.experiment_id)
    )
    signups_stmt = (
        select(WaitlistSignup.experiment_id, func.count(WaitlistSignup.id))
        .where(WaitlistSignup.experiment_id.in_(unlocked_ids))
        .group_by(WaitlistSignup.experiment_id)
    )

    views_result = await db.execute(views_stmt)
    signups_result = await db.execute(signups_stmt)

    views_by_id = {row[0]: int(row[1]) for row in views_result.all()}
    signups_by_id = {row[0]: int(row[1]) for row in signups_result.all()}

    stats: dict[UUID, ExperimentCardStats] = {}
    for experiment_id in unlocked_ids:
        stats[experiment_id] = ExperimentCardStats(
            page_views=views_by_id.get(experiment_id, 0),
            waitlist_signups=signups_by_id.get(experiment_id, 0),
        )
    return stats
```

### `backend/app/schemas/api_responses.py` (AnalyticsResponse)

```python
class AnalyticsResponse(BaseModel):
    """GET /experiments/{id}/analytics — live landing page metrics."""

    model_config = ConfigDict(extra="forbid")

    total_page_views: int = Field(ge=0)
    total_signups: int = Field(ge=0)
    unique_visitors: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=1.0)
    views_by_source: dict[str, int]
    signups_by_source: dict[str, int]
    conversion_rate_by_source: dict[str, float]
    signups_by_location: list[SignupLocationBucket] = Field(default_factory=list)
    days_live: int = Field(ge=0)
```

### `backend/app/schemas/experiment.py` (ExperimentCardStats, ExperimentListItemResponse)

```python
class ExperimentCardStats(BaseModel):
    """Lightweight behavioral metrics for dashboard project cards."""

    page_views: int = Field(ge=0)
    waitlist_signups: int = Field(ge=0)


class ExperimentListItemResponse(ExperimentResponse):
    """GET /experiments list item — behavioral metrics when metrics are unlocked."""

    card_stats: ExperimentCardStats | None = None
```

## 5. Models

### PageView

`backend/app/db/models/page_view.py`

```python
class PageView(Base):
    __tablename__ = "page_views"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Indexed for per-source analytics queries (conversion rate by source tag)
    source_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    time_on_page_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # INET supports both IPv4 and IPv6; nullable for privacy-respecting clients
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="page_views")
```

### WaitlistSignup

`backend/app/db/models/waitlist_signup.py`

```python
class WaitlistSignup(Base):
    __tablename__ = "waitlist_signups"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NOT unique — one person can sign up for multiple experiments
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    # Indexed for per-source conversion analytics
    source_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    geo_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    geo_region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    geo_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="waitlist_signups")
```

### Experiment

`backend/app/db/models/experiment.py`

```python
class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    raw_idea: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refined_idea: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    refinement_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    status: Mapped[ExperimentStatus] = mapped_column(
        SQLEnum(
            ExperimentStatus,
            name="experiment_status",
            native_enum=False,
            length=50,
        ),
        nullable=False,
        default=ExperimentStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Sanitized error string written by the state machine on RESEARCH_FAILED.
    # NULL on success. Never contains raw stack traces or API keys — see
    # research_engine_service.py _sanitize_error_detail().
    research_error_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Links experiment to chat thread; null for non-chat paths (admin, eval).
    thread_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Audit: user_confirm (/confirm) vs auto_fire (chat refinement complete).
    dispatch_trigger: Mapped[DispatchTrigger | None] = mapped_column(
        SQLEnum(
            DispatchTrigger,
            name="dispatch_trigger",
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )

    # --- Relationships ---
    user: Mapped[User] = relationship(back_populates="experiments")
    validation_report: Mapped[ValidationReport | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    landing_page: Mapped[LandingPage | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    landing_page_v2: Mapped[LandingPageV2Spec | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    insight_report: Mapped[InsightReport | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    page_views: Mapped[list[PageView]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    waitlist_signups: Mapped[list[WaitlistSignup]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    # No cascade — LLMCall/ExternalAPICall are audit records; survive experiment deletion.
    llm_calls: Mapped[list[LLMCall]] = relationship(back_populates="experiment")
    external_api_calls: Mapped[list[ExternalAPICall]] = relationship(
        back_populates="experiment"
    )
```

### LandingPage

`backend/app/db/models/landing_page.py`

```python
class LandingPage(Base):
    __tablename__ = "landing_pages"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # unique=True enforces the 1:1 constraint with Experiment at the DB level.
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Template and style identifiers — e.g. "minimal", "vibrant"
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)
    palette_id: Mapped[str] = mapped_column(String(50), nullable=False)
    font_pair_id: Mapped[str] = mapped_column(String(50), nullable=False)
    density: Mapped[LandingDensity] = mapped_column(
        SQLEnum(
            LandingDensity,
            name="landing_density",
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=LandingDensity.ROOMY,
    )
    enabled_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Hero copy
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    subheadline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    problem_desc: Mapped[str] = mapped_column(Text, nullable=False)
    solution_desc: Mapped[str] = mapped_column(Text, nullable=False)
    cta_text: Mapped[str] = mapped_column(String(100), nullable=False)
    cta_type: Mapped[LandingCtaType] = mapped_column(
        SQLEnum(
            LandingCtaType,
            name="landing_cta_type",
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=LandingCtaType.WAITLIST,
    )

    # Optional sections — structure validated at Pydantic layer
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    how_it_works: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    faq: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    founder_bio: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    copy_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    page_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Public URL slug — pattern ^[a-z0-9-]{6,40}$ enforced at Pydantic layer
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Publishing lifecycle timestamps — null until the relevant event occurs
    live_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_revalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Relationships ---
    experiment: Mapped[Experiment] = relationship(back_populates="landing_page")
```

### LandingPageV2Spec

`backend/app/db/models/landing_page_v2.py`

```python
class LandingPageV2Spec(Base):
    """Structured page specification for the V2 runtime (isolated from V1 rows)."""

    __tablename__ = "landing_page_v2_specs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    experiment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    spec_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="idle",
    )
    generation_phase: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default="idle",
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    experiment: Mapped[Experiment] = relationship(back_populates="landing_page_v2")
```

## 6. Shared metrics/analytics service (if exists)

`backend/app/services/analytics_aggregator.py` — included in §4 above. This is the single backend module that computes `conversion_rate` (`total_signups / unique_visitors`, where `unique_visitors` is COUNT DISTINCT `ip_address` with fallback to total row count). No separate `metrics_service.py` or `analytics_service.py` exists.

## Notes

1. **Site A (/metrics tab):** Conversion is **pre-computed on the backend** and returned as `conversion_rate` (float 0–1) on `GET /experiments/{id}/analytics`. The frontend displays it via `formatPercent(analytics.conversion_rate)` which multiplies by 100.

2. **Site B (dashboard card):** Conversion is **computed in the frontend** from two raw count fields on `GET /experiments` → `card_stats`. No `conversion_rate` field exists on the list response.

3. **Site A frontend expression (verbatim):** `return \`${(rate * 100).toFixed(1)}%\`;` applied to `analytics.conversion_rate` in MetricsWidget and DistributeSection.

4. **Site B frontend expression (verbatim):** `return \`${((signups / views) * 100).toFixed(1)}%\`;` in `formatConversion(stats.page_views, stats.waitlist_signups)`.

5. **Backend assignment of Site A field:** `get_experiment_analytics` in `backend/app/routers/experiments.py` sets `conversion_rate=aggregate.conversion_rate` where `aggregate = await build_analytics_aggregate(...)`. Inside `build_analytics_aggregate`: `conversion_rate = _clamp01(total_signups / unique_visitors)` with `unique_visitors = len(non_null_ips)` (distinct `PageView.ip_address` values; falls back to `total_page_views` if all IPs are null).

6. **Endpoints:** Site A uses `GET /experiments/{id}/analytics`. Site B uses `GET /experiments` (embedded `card_stats`). Different endpoints.

7. **PageView deduplication:** The `PageView` model has no `visitor_id`, `session_id`, or `fingerprint` field — only `ip_address`. The analytics aggregator deduplicates visitors by distinct `ip_address` for `unique_visitors` and thus overall `conversion_rate`. Per-source `conversion_rate_by_source` uses **raw view row counts** (`views_by_source`), not unique IPs. The dashboard card stats query uses `func.count(PageView.id)` — **no deduplication**, all rows counted.

8. **Multiply-by-100 asymmetry:** Both sites multiply a **ratio** by 100 for display. Site A's ratio is `signups / unique_visitors` (backend). Site B's ratio is `signups / page_views` (frontend). The bug for 4 views / 1 signup: if `unique_visitors=1` (one distinct IP) backend returns `conversion_rate=1.0` → **100%** on metrics; dashboard computes `1/4*100` → **25%**.

9. **Other asymmetries:** (a) Numerator/denominator mismatch: unique visitors vs total page view rows. (b) `total_page_views` on metrics tab shows raw count (4) while conversion uses unique visitors (1) — the headline numbers can look inconsistent. (c) Per-source breakdown on metrics uses views/signups row counts, not unique IPs. (d) Both paths require `metricsAnalysis` unlock for live experiments, but use different backend code paths. (e) `LandingPageV2Spec` is not referenced by either metrics endpoint; analytics reads `LandingPage.live_at` only.
