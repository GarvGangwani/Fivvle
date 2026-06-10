"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Loader2,
  RefreshCw,
  ArchiveRestore,
  Download,
  Eye,
  ExternalLink,
} from "lucide-react";
import {
  confirmExperiment,
  exportWaitlistCsv,
  generateInsight,
  generateLandingPage,
  getExperiment,
  getLandingPage,
  getWaitlistSignups,
  unarchiveExperiment,
  ApiError,
} from "@/lib/api";
import type { Experiment, FounderDecision, WaitlistSignupsResponse } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { DecisionPanel } from "@/components/insight/DecisionPanel";
import { InsightReportViewer } from "@/components/insight/InsightReportViewer";
import { MetricsWidget } from "@/components/insight/MetricsWidget";
import { LandingGenerationProgress } from "@/components/research/LandingGenerationProgress";
import {
  TemplatePicker,
  type TemplateId,
} from "@/components/research/TemplatePicker";
import { ReportCanvas } from "@/components/research/ReportCanvas";
import { DistributeSection } from "@/components/distribution/DistributeSection";
import { getExperimentDisplayName } from "@/lib/experiment-name";

const DISTRIBUTE_VISIBLE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "COMPLETED",
  "ARCHIVED",
]);

const WAITLIST_VISIBLE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

function formatWaitlistDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

interface WaitlistSectionProps {
  experimentId: string;
}

function WaitlistSection({ experimentId }: WaitlistSectionProps) {
  const [waitlist, setWaitlist] = useState<WaitlistSignupsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadWaitlist() {
      setLoading(true);
      try {
        const data = await getWaitlistSignups(experimentId);
        if (!cancelled) {
          setWaitlist(data);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setError("Could not load waitlist signups.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadWaitlist();

    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      await exportWaitlistCsv(experimentId);
    } catch {
      setError("Could not export waitlist. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  if (loading || !waitlist || waitlist.total === 0) {
    return null;
  }

  return (
    <details className="fv-card mb-4 p-4">
      <summary className="cursor-pointer text-sm font-semibold text-[var(--fv-text)]">
        Waitlist ({waitlist.total} signup{waitlist.total === 1 ? "" : "s"})
      </summary>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => void handleExport()}
          disabled={exporting}
          className="fv-btn-ghost inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
        >
          {exporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export CSV
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/[0.08] text-[var(--fv-text-muted)]">
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Signed up</th>
            </tr>
          </thead>
          <tbody>
            {waitlist.signups.map((signup) => (
              <tr
                key={signup.id}
                className="border-b border-white/[0.04] text-[var(--fv-text-soft)]"
              >
                <td className="px-3 py-3 text-[var(--fv-text)]">{signup.email}</td>
                <td className="px-3 py-3">{signup.source_tag ?? "—"}</td>
                <td className="px-3 py-3">{formatWaitlistDate(signup.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

interface ExperimentDetailPanelProps {
  experimentId: string;
  rawIdea?: string;
  nameRefreshKey?: number;
}

export function ExperimentDetailPanel({
  experimentId,
  nameRefreshKey = 0,
}: ExperimentDetailPanelProps) {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [generatingLp, setGeneratingLp] = useState(false);
  const [retryingInsight, setRetryingInsight] = useState(false);
  const [unarchiving, setUnarchiving] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [showInsight, setShowInsight] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [landingSlug, setLandingSlug] = useState<string | null>(null);

  const loadExperiment = useCallback(async () => {
    try {
      const data = await getExperiment(experimentId);
      setExperiment(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "Experiment not found."
          : "Could not load experiment.",
      );
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    setLoading(true);
    void loadExperiment();
  }, [loadExperiment, nameRefreshKey]);

  useEffect(() => {
    if (
      experiment?.status !== "INSIGHT_GENERATING" &&
      experiment?.status !== "LANDING_GENERATING"
    ) {
      return;
    }

    const intervalMs =
      experiment.status === "LANDING_GENERATING" ? 5000 : 3000;
    const intervalId = setInterval(() => {
      void loadExperiment();
    }, intervalMs);

    return () => clearInterval(intervalId);
  }, [experiment?.status, loadExperiment]);

  useEffect(() => {
    if (!experiment || !DISTRIBUTE_VISIBLE_STATUSES.has(experiment.status)) {
      setLandingSlug(null);
      return;
    }

    let cancelled = false;

    async function loadSlug() {
      try {
        const lp = await getLandingPage(experimentId);
        if (!cancelled && lp.slug) {
          setLandingSlug(lp.slug);
        }
      } catch {
        if (!cancelled) {
          setLandingSlug(null);
        }
      }
    }

    void loadSlug();

    return () => {
      cancelled = true;
    };
  }, [experiment, experimentId]);

  async function handleRetryResearch() {
    setRetrying(true);
    try {
      await confirmExperiment(experimentId);
      await loadExperiment();
    } catch {
      setError("Could not restart research. Please try again.");
    } finally {
      setRetrying(false);
    }
  }

  async function handleGenerateLandingPage() {
    if (!selectedTemplate) return;
    setGeneratingLp(true);
    try {
      await generateLandingPage(experimentId, { template_id: selectedTemplate });
      setShowTemplatePicker(false);
      await loadExperiment();
    } catch {
      setError("Could not start landing page generation. Please try again.");
    } finally {
      setGeneratingLp(false);
    }
  }

  async function handleRetryInsight() {
    setRetryingInsight(true);
    try {
      await generateInsight(experimentId);
      await loadExperiment();
    } catch {
      setError("Could not restart insight generation. Please try again.");
    } finally {
      setRetryingInsight(false);
    }
  }

  function handleDecision(_decision: FounderDecision) {
    void loadExperiment();
  }

  async function handleUnarchive() {
    setUnarchiving(true);
    try {
      await unarchiveExperiment(experimentId);
      await loadExperiment();
    } catch {
      setError("Could not restore experiment. Please try again.");
    } finally {
      setUnarchiving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full min-h-[400px] flex-col">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="fv-skeleton h-6 w-24 rounded-full" />
        </div>
        <div className="fv-skeleton min-h-0 flex-1 rounded-xl" />
      </div>
    );
  }

  if (error && !experiment) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-red-300">{error}</p>
      </div>
    );
  }

  if (!experiment) return null;

  const status = experiment.status;
  const hasValidationReport = experiment.validation_report != null;
  const showWaitlistSection = WAITLIST_VISIBLE_STATUSES.has(status);
  const showDistributeSection =
    DISTRIBUTE_VISIBLE_STATUSES.has(status) && landingSlug !== null;
  const experimentDisplayName = experiment.name?.trim()
    ? experiment.name.trim()
    : getExperimentDisplayName({ name: null, raw_idea: "" });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 flex shrink-0 flex-wrap items-center gap-2">
        <StatusBadge status={status} />

        {hasValidationReport && (
          <button
            type="button"
            onClick={() => setReportOpen(true)}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold"
          >
            <Eye className="h-3.5 w-3.5" />
            Validation report
          </button>
        )}

        {status === "RESEARCH_READY" && (
          <button
            type="button"
            onClick={() => setShowTemplatePicker((v) => !v)}
            className="fv-btn-ghost px-3 py-1.5 text-xs font-semibold"
          >
            Generate landing page
          </button>
        )}

        {(status === "LANDING_DRAFT" || status === "LANDING_LIVE") && (
          <Link
            href={`/experiment/${experimentId}/landing-page`}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold no-underline"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Landing page editor
          </Link>
        )}

        {status === "LANDING_LIVE" && (
          <button
            type="button"
            onClick={() => setShowMetrics((v) => !v)}
            className="fv-btn-ghost px-3 py-1.5 text-xs font-semibold"
          >
            Live metrics
          </button>
        )}

        {(status === "INSIGHT_READY" || status === "COMPLETED") && (
          <button
            type="button"
            onClick={() => setShowInsight((v) => !v)}
            className="fv-btn-ghost px-3 py-1.5 text-xs font-semibold"
          >
            Insight report
          </button>
        )}

        {status === "RESEARCH_FAILED" && (
          <button
            type="button"
            onClick={() => void handleRetryResearch()}
            disabled={retrying}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-300 disabled:opacity-50"
          >
            {retrying ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Retry research
          </button>
        )}

        {status === "INSIGHT_FAILED" && (
          <button
            type="button"
            onClick={() => void handleRetryInsight()}
            disabled={retryingInsight}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-300 disabled:opacity-50"
          >
            {retryingInsight ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Retry insight
          </button>
        )}

        {status === "ARCHIVED" && (
          <button
            type="button"
            onClick={() => void handleUnarchive()}
            disabled={unarchiving}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
          >
            {unarchiving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ArchiveRestore className="h-3.5 w-3.5" />
            )}
            Unarchive
          </button>
        )}
      </div>

      {error && (
        <div className="fv-error mb-3 shrink-0 px-4 py-2 text-sm">{error}</div>
      )}

      {showTemplatePicker && status === "RESEARCH_READY" && (
        <div className="fv-card mb-4 shrink-0 p-4">
          <TemplatePicker
            selectedId={selectedTemplate}
            onSelect={setSelectedTemplate}
            onGenerate={handleGenerateLandingPage}
            generating={generatingLp}
          />
        </div>
      )}

      {status === "LANDING_GENERATING" && (
        <div className="mb-4 shrink-0">
          <LandingGenerationProgress
            experimentId={experimentId}
            onComplete={loadExperiment}
          />
        </div>
      )}

      {showDistributeSection && landingSlug && (
        <DistributeSection
          experimentId={experimentId}
          slug={landingSlug}
          experimentName={experimentDisplayName}
        />
      )}

      {showMetrics && status === "LANDING_LIVE" && (
        <div className="mb-4 shrink-0">
          <MetricsWidget
            experimentId={experimentId}
            onInsightStarted={loadExperiment}
          />
        </div>
      )}

      {showInsight && (status === "INSIGHT_READY" || status === "COMPLETED") && (
        <div className="mb-4 max-h-[40vh] shrink-0 space-y-4 overflow-y-auto">
          <InsightReportViewer experimentId={experimentId} />
          <DecisionPanel
            experimentId={experimentId}
            onDecision={handleDecision}
          />
        </div>
      )}

      {showWaitlistSection && (
        <WaitlistSection experimentId={experimentId} />
      )}

      <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-[var(--fv-border)]">
        <ChatInterface experimentId={experimentId} />
      </div>

      {reportOpen && (
        <div className="fixed inset-0 z-50 bg-[var(--fv-bg)]">
          <ReportCanvas
            experimentId={experimentId}
            onClose={() => setReportOpen(false)}
            mobile
          />
        </div>
      )}
    </div>
  );
}
