"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, RefreshCw, ArchiveRestore, Download } from "lucide-react";
import {
  confirmExperiment,
  exportWaitlistCsv,
  generateInsight,
  generateLandingPage,
  getExperiment,
  getWaitlistSignups,
  unarchiveExperiment,
  ApiError,
} from "@/lib/api";
import type { Experiment, FounderDecision, WaitlistSignupsResponse } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { DecisionPanel } from "@/components/insight/DecisionPanel";
import { InsightReportViewer } from "@/components/insight/InsightReportViewer";
import { MetricsWidget } from "@/components/insight/MetricsWidget";
import { LandingGenerationProgress } from "@/components/research/LandingGenerationProgress";
import { ResearchProgress } from "@/components/research/ResearchProgress";
import {
  TemplatePicker,
  type TemplateId,
} from "@/components/research/TemplatePicker";
import { ValidationReportPanel } from "@/components/research/ValidationReportPanel";
import { getExperimentDisplayName } from "@/lib/experiment-name";

const RESEARCH_IN_PROGRESS = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
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
    <section className="fv-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">
          Waitlist ({waitlist.total} signup{waitlist.total === 1 ? "" : "s"})
        </h2>
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

      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

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
    </section>
  );
}

interface ExperimentDetailPanelProps {
  experimentId: string;
  rawIdea?: string;
  nameRefreshKey?: number;
}

export function ExperimentDetailPanel({
  experimentId,
  rawIdea = "",
  nameRefreshKey = 0,
}: ExperimentDetailPanelProps) {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [generatingLp, setGeneratingLp] = useState(false);
  const [retryingInsight, setRetryingInsight] = useState(false);
  const [unarchiving, setUnarchiving] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId | null>(
    null,
  );
  const [reportOpen, setReportOpen] = useState(false);

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

  const handleResearchComplete = useCallback(() => {
    void loadExperiment();
  }, [loadExperiment]);

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
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <div className="fv-skeleton h-8 w-36 rounded" />
          <div className="fv-skeleton h-6 w-24 rounded-full" />
        </div>
        <div className="fv-skeleton mb-4 h-48 rounded-xl" />
        <div className="fv-skeleton h-32 rounded-xl" />
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
  const pageTitle = getExperimentDisplayName({
    name: experiment.name,
    raw_idea: rawIdea,
  });

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="sr-only">{pageTitle}</h1>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <StatusBadge status={status} />
      </div>

      {error && (
        <div className="fv-error mb-6 px-4 py-3 text-sm">{error}</div>
      )}

      {hasValidationReport && (
        <div className="mb-6">
          <button
            type="button"
            onClick={() => setReportOpen(true)}
            className="view-report-btn"
          >
            View Validation Report
          </button>
        </div>
      )}

      {RESEARCH_IN_PROGRESS.has(status) && (
        <ResearchProgress
          experimentId={experimentId}
          onComplete={handleResearchComplete}
        />
      )}

      {status === "RESEARCH_READY" && (
        <div className="space-y-6">
          <TemplatePicker
            selectedId={selectedTemplate}
            onSelect={setSelectedTemplate}
            onGenerate={handleGenerateLandingPage}
            generating={generatingLp}
          />
        </div>
      )}

      {status === "RESEARCH_FAILED" && (
        <div className="fv-error px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-red-300">
            Research failed
          </h2>
          <p className="mt-2 text-sm text-red-200/80">
            Something went wrong during market research. You can retry and
            we&apos;ll pick up where we left off.
          </p>
          <button
            type="button"
            onClick={handleRetryResearch}
            disabled={retrying}
            className="fv-btn-ghost mt-6 inline-flex items-center gap-2 border-[rgba(239,68,68,0.3)] px-5 py-2.5 text-sm font-semibold text-red-300 hover:border-[rgba(239,68,68,0.5)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {retrying ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Retry research
          </button>
        </div>
      )}

      {status === "LANDING_GENERATING" && (
        <LandingGenerationProgress
          experimentId={experimentId}
          onComplete={loadExperiment}
        />
      )}

      {status === "LANDING_LIVE" && (
        <div className="space-y-6">
          <MetricsWidget
            experimentId={experimentId}
            onInsightStarted={loadExperiment}
          />
          <div className="fv-card px-6 py-8">
            <h2 className="text-lg font-semibold text-[var(--fv-text)]">
              Landing page is live
            </h2>
            <p className="mt-2 text-sm text-[var(--fv-text-soft)]">
              Your landing page is published and collecting traffic.
            </p>
            <Link
              href={`/experiment/${experimentId}/landing-page`}
              className="fv-btn-primary mt-6 inline-flex px-5 py-2.5 text-sm no-underline"
            >
              Open landing page editor
            </Link>
          </div>
        </div>
      )}

      {status === "LANDING_DRAFT" && (
        <div className="fv-card px-6 py-8">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">
            Landing page draft ready
          </h2>
          <p className="mt-2 text-sm text-[var(--fv-text-soft)]">
            Review and customize your landing page before publishing.
          </p>
          <Link
            href={`/experiment/${experimentId}/landing-page`}
            className="fv-btn-primary mt-6 inline-flex px-5 py-2.5 text-sm no-underline"
          >
            Review & customize landing page
          </Link>
        </div>
      )}

      {status === "INSIGHT_GENERATING" && (
        <div className="fv-card flex flex-col items-center px-6 py-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--fv-accent)]" />
          <p className="mt-4 text-sm font-medium text-[var(--fv-text)]">
            Generating insight report…
          </p>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
            This usually takes under a minute.
          </p>
        </div>
      )}

      {status === "INSIGHT_READY" && (
        <div className="space-y-8">
          <InsightReportViewer experimentId={experimentId} />
          <DecisionPanel
            experimentId={experimentId}
            onDecision={handleDecision}
          />
        </div>
      )}

      {status === "INSIGHT_FAILED" && (
        <div className="fv-error px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-red-300">
            Insight generation failed
          </h2>
          <p className="mt-2 text-sm text-red-200/80">
            Something went wrong while building your insight report.
          </p>
          <button
            type="button"
            onClick={handleRetryInsight}
            disabled={retryingInsight}
            className="fv-btn-ghost mt-6 inline-flex items-center gap-2 border-[rgba(239,68,68,0.3)] px-5 py-2.5 text-sm font-semibold text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {retryingInsight ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Retry insight generation
          </button>
        </div>
      )}

      {status === "ARCHIVED" && (
        <div className="fv-card px-6 py-8 text-center">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">
            Experiment archived
          </h2>
          <p className="mt-2 text-sm text-[var(--fv-text-soft)]">
            This experiment is archived. Restore it to review reports and
            continue where you left off.
          </p>
          <button
            type="button"
            onClick={handleUnarchive}
            disabled={unarchiving}
            className="fv-btn-ghost mt-6 inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
          >
            {unarchiving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArchiveRestore className="h-4 w-4" />
            )}
            Unarchive
          </button>
        </div>
      )}

      {!RESEARCH_IN_PROGRESS.has(status) &&
        status !== "RESEARCH_READY" &&
        status !== "RESEARCH_FAILED" &&
        status !== "LANDING_DRAFT" &&
        status !== "LANDING_LIVE" &&
        status !== "LANDING_GENERATING" &&
        status !== "INSIGHT_GENERATING" &&
        status !== "INSIGHT_READY" &&
        status !== "INSIGHT_FAILED" &&
        status !== "ARCHIVED" && (
          <div className="fv-card px-6 py-8 text-center">
            <p className="text-sm text-[var(--fv-text-soft)]">
              This experiment is in{" "}
              <span className="font-medium text-[var(--fv-text)]">
                {status.replace(/_/g, " ").toLowerCase()}
              </span>{" "}
              status.
            </p>
            {(status === "DRAFT" ||
              status === "REFINING" ||
              status === "REFINED") && (
              <Link
                href="/new"
                className="mt-4 inline-block text-sm font-semibold text-[var(--fv-accent)] no-underline hover:text-[var(--fv-accent-hover)]"
              >
                Continue in chat
              </Link>
            )}
          </div>
        )}

      {showWaitlistSection && (
        <div className="mt-6">
          <WaitlistSection experimentId={experimentId} />
        </div>
      )}

      <ValidationReportPanel
        experimentId={experimentId}
        open={reportOpen}
        onClose={() => setReportOpen(false)}
      />
    </div>
  );
}
