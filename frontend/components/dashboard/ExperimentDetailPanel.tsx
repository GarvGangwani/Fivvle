"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArchiveRestore,
  Archive,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  confirmExperiment,
  generateInsight,
  generateLandingPage,
  getExperiment,
  getLandingPage,
  unarchiveExperiment,
  ApiError,
} from "@/lib/api";
import { useWallet } from "@/lib/wallet-context";
import type { Experiment, FounderDecision, LandingPage } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { RefineStagePanel } from "@/components/refinement/RefineStagePanel";
import { InsightStagePanel } from "@/components/insight/InsightStagePanel";
import { MetricsStagePanel } from "@/components/insight/MetricsStagePanel";
import { LandingGenerationProgress } from "@/components/research/LandingGenerationProgress";
import {
  TemplatePicker,
  type TemplateId,
} from "@/components/research/TemplatePicker";
import { ReportCanvas } from "@/components/research/ReportCanvas";
import { EditorLayout } from "@/components/landing-page-editor/EditorLayout";
import { EditorLoadingSkeleton } from "@/components/landing-page-editor/EditorLoadingSkeleton";
import { ExperimentStageNav } from "@/components/experiment/ExperimentStageNav";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { EditableProjectName } from "@/components/experiment/EditableProjectName";
import { ArchiveProjectDialog } from "@/components/experiment/ArchiveProjectDialog";
import { DeleteProjectDialog } from "@/components/experiment/DeleteProjectDialog";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import {
  INSIGHT_PAYWALL_CREDITS,
  VALIDATION_PAYWALL_CREDITS,
} from "@/lib/wallet-paywall";
import {
  defaultStageForStatus,
  isStageUnlocked,
  pollIntervalForStatus,
  shouldPollExperimentStatus,
  shouldShowExperimentStageNav,
  type ExperimentStageId,
} from "@/lib/experiment-stages";
import { canViewLandingPageEditor } from "@/lib/landing-flow";

const DISTRIBUTE_VISIBLE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ARCHIVED",
]);

const LANDING_PAGE_LOAD_RETRIES = 8;
const LANDING_PAGE_LOAD_RETRY_MS = 1500;

function templateStorageKey(experimentId: string): string {
  return `fivvle_lp_template_${experimentId}`;
}

function readStoredTemplate(experimentId: string): TemplateId | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(templateStorageKey(experimentId));
    if (!raw) return null;
    return raw as TemplateId;
  } catch {
    return null;
  }
}

function storeTemplate(experimentId: string, templateId: TemplateId): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(templateStorageKey(experimentId), templateId);
  } catch {
    /* ignore */
  }
}

interface ExperimentDetailPanelProps {
  experimentId: string;
  rawIdea?: string;
  nameRefreshKey?: number;
  initialStage?: ExperimentStageId;
}

export function ExperimentDetailPanel({
  experimentId,
  nameRefreshKey = 0,
  initialStage,
}: ExperimentDetailPanelProps) {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [generatingLp, setGeneratingLp] = useState(false);
  const [retryingInsight, setRetryingInsight] = useState(false);
  const [unarchiving, setUnarchiving] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId | null>(null);
  const [activeStage, setActiveStage] = useState<ExperimentStageId>(
    initialStage ?? "refine",
  );
  const [landingSlug, setLandingSlug] = useState<string | null>(null);
  const [landingPage, setLandingPage] = useState<LandingPage | null>(null);
  const [landingPageLoading, setLandingPageLoading] = useState(false);
  const [landingPageError, setLandingPageError] = useState<string | null>(null);
  const [refinementFinalized, setRefinementFinalized] = useState(false);
  const { refresh: refreshWallet, applyWalletPatch } = useWallet();

  const loadExperiment = useCallback(async () => {
    try {
      const data = await getExperiment(experimentId);
      setExperiment(data);
      setError(null);
      if (data.status === "REFINED" || data.validation_report != null) {
        setRefinementFinalized(true);
      }
      setActiveStage((prev) => {
        if (isStageUnlocked(prev, data.status)) return prev;
        return defaultStageForStatus(data.status);
      });
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

  const loadLandingPage = useCallback(
    async (options: { retryOn404?: boolean } = {}) => {
      const retryOn404 = options.retryOn404 ?? false;
      setLandingPageLoading(true);
      setLandingPageError(null);

      const maxAttempts = retryOn404 ? LANDING_PAGE_LOAD_RETRIES : 1;
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        try {
          const lp = await getLandingPage(experimentId);
          setLandingPage(lp);
          if (lp.slug) setLandingSlug(lp.slug);
          setLandingPageLoading(false);
          return;
        } catch (err) {
          const is404 = err instanceof ApiError && err.status === 404;
          const canRetry = retryOn404 && is404 && attempt < maxAttempts - 1;
          if (canRetry) {
            await new Promise((resolve) => {
              setTimeout(resolve, LANDING_PAGE_LOAD_RETRY_MS);
            });
            continue;
          }
          setLandingPage(null);
          if (is404) {
            setLandingPageError(
              "Landing page not found. It may still be generating.",
            );
          } else {
            setLandingPageError("Could not load landing page.");
          }
          setLandingPageLoading(false);
          return;
        }
      }
    },
    [experimentId],
  );

  useEffect(() => {
    setLoading(true);
    void loadExperiment();
  }, [loadExperiment, nameRefreshKey]);

  useEffect(() => {
    if (!experiment || !shouldPollExperimentStatus(experiment.status)) {
      return;
    }
    const intervalMs = pollIntervalForStatus(experiment.status);
    const intervalId = setInterval(() => void loadExperiment(), intervalMs);
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
        if (!cancelled && lp.slug) setLandingSlug(lp.slug);
      } catch {
        if (!cancelled) setLandingSlug(null);
      }
    }
    void loadSlug();
    return () => {
      cancelled = true;
    };
  }, [experiment, experimentId]);

  useEffect(() => {
    if (activeStage !== "landing") return;
    if (!experiment || !canViewLandingPageEditor(experiment.status)) {
      setLandingPage(null);
      setLandingPageError(null);
      return;
    }
    void loadLandingPage({ retryOn404: true });
  }, [activeStage, experiment, loadLandingPage]);

  useEffect(() => {
    const stored = readStoredTemplate(experimentId);
    if (stored) {
      setSelectedTemplate(stored);
    }
  }, [experimentId]);

  const handleLandingGenerationComplete = useCallback(() => {
    void loadExperiment();
    void loadLandingPage({ retryOn404: true });
  }, [loadExperiment, loadLandingPage]);

  const handleLandingGenerationFailed = useCallback(() => {
    void loadExperiment();
  }, [loadExperiment]);

  async function handleRetryResearch() {
    setRetrying(true);
    setError(null);
    try {
      const result = await confirmExperiment(experimentId);
      await syncWalletAfterPaidAction(
        refreshWallet,
        applyWalletPatch,
        result.credits_balance,
      );
      await loadExperiment();
      setActiveStage("refine");
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        await refreshWallet();
      }
      setError(
        readPaidActionError(err, {
          fallbackRequired: VALIDATION_PAYWALL_CREDITS,
          fallback: "Could not restart research. Please try again.",
        }),
      );
    } finally {
      setRetrying(false);
    }
  }

  async function handleGenerateLandingPage() {
    if (!selectedTemplate) return;
    storeTemplate(experimentId, selectedTemplate);
    setGeneratingLp(true);
    try {
      await generateLandingPage(experimentId, { template_id: selectedTemplate });
      await loadExperiment();
      setActiveStage("landing");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 0) {
          setError("Could not reach the server. Check that the API is running.");
          return;
        }
        const body = err.body;
        if (
          body &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail: unknown }).detail === "string"
        ) {
          setError((body as { detail: string }).detail);
          return;
        }
      }
      setError("Could not start landing page generation. Please try again.");
    } finally {
      setGeneratingLp(false);
    }
  }

  async function handleRetryInsight() {
    if (retryingInsight) return;
    setRetryingInsight(true);
    setError(null);
    try {
      const result = await generateInsight(experimentId);
      await syncWalletAfterPaidAction(
        refreshWallet,
        applyWalletPatch,
        result.credits_balance,
      );
      await loadExperiment();
      setActiveStage("insight");
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        await refreshWallet();
        setError(
          "Could not start insight generation. Your credits have been refunded — please try again.",
        );
        return;
      }
      setError(
        readPaidActionError(err, {
          fallbackRequired: INSIGHT_PAYWALL_CREDITS,
          fallback: "Could not start insight generation. Please try again.",
        }),
      );
    } finally {
      setRetryingInsight(false);
    }
  }

  async function handleUnarchive() {
    setUnarchiving(true);
    try {
      await unarchiveExperiment(experimentId);
      notifyExperimentsChanged();
      await loadExperiment();
    } catch {
      setError("Could not restore experiment. Please try again.");
    } finally {
      setUnarchiving(false);
    }
  }

  function handleDecision(_decision: FounderDecision) {
    notifyExperimentsChanged();
    void loadExperiment();
  }

  if (loading) {
    return (
      <div className="flex h-full min-h-0 flex-col p-3 sm:p-4">
        <div className="fv-skeleton mb-3 h-9 w-64 rounded-lg" />
        <div className="fv-skeleton min-h-0 flex-1 rounded-xl" />
      </div>
    );
  }

  if (error && !experiment) {
    return (
      <div className="flex items-center justify-center p-6 py-20">
        <ErrorBanner message={error} className="max-w-md" />
      </div>
    );
  }

  if (!experiment) return null;

  const status = experiment.status;
  const hasValidationReport = experiment.validation_report != null;
  const showStageNav = shouldShowExperimentStageNav(
    status,
    hasValidationReport,
    refinementFinalized,
  );
  const experimentDisplayName = getExperimentDisplayName(experiment);
  const showDistribute =
    DISTRIBUTE_VISIBLE_STATUSES.has(status) && landingSlug !== null;

  const headerActions = (
    <>
      {status === "RESEARCH_FAILED" && (
        <button
          type="button"
          onClick={() => void handleRetryResearch()}
          disabled={retrying}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {retrying ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Retry research
        </button>
      )}
      {status === "INSIGHT_FAILED" && (
        <button
          type="button"
          onClick={() => void handleRetryInsight()}
          disabled={retryingInsight}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {retryingInsight ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Retry insight
        </button>
      )}
      {status === "ARCHIVED" && (
        <button
          type="button"
          onClick={() => void handleUnarchive()}
          disabled={unarchiving}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {unarchiving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArchiveRestore className="h-4 w-4" />
          )}
          Restore
        </button>
      )}
      {status !== "ARCHIVED" && (
        <button
          type="button"
          onClick={() => setArchiveDialogOpen(true)}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-[var(--fv-text-muted)] hover:text-[var(--fv-danger)]"
        >
          <Archive className="h-4 w-4" />
          Archive
        </button>
      )}
      <button
        type="button"
        onClick={() => setDeleteDialogOpen(true)}
        className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-[var(--fv-text-muted)] hover:text-[var(--fv-danger)]"
      >
        <Trash2 className="h-4 w-4" />
        Delete
      </button>
    </>
  );

  function renderStageContent(exp: Experiment) {
    const expStatus = exp.status;
    const expDisplayName = getExperimentDisplayName(exp);

    switch (activeStage) {
      case "refine":
        return (
          <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
            <RefineStagePanel
              experimentId={experimentId}
              onExperimentChange={loadExperiment}
              onRefinementFinalized={setRefinementFinalized}
            />
          </div>
        );

      case "report":
        if (!exp.validation_report) {
          return (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <LoadingState label="Research in progress — your report will appear here when ready." />
            </div>
          );
        }
        return (
          <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[var(--fv-border)]">
            <ReportCanvas
              experimentId={experimentId}
              embedded
              projectName={expDisplayName}
            />
          </div>
        );

      case "landing":
        if (expStatus === "LANDING_GENERATING") {
          return (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="fv-section-card">
                <LandingGenerationProgress
                  experimentId={experimentId}
                  onComplete={handleLandingGenerationComplete}
                  onFailed={handleLandingGenerationFailed}
                />
              </div>
            </div>
          );
        }
        if (canViewLandingPageEditor(expStatus)) {
          if (landingPageLoading) {
            return (
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <EditorLoadingSkeleton embedded />
              </div>
            );
          }
          if (landingPageError || !landingPage) {
            return (
              <div className="min-h-0 flex-1 overflow-y-auto">
                <ErrorBanner
                  message={landingPageError ?? "Landing page unavailable."}
                  className="max-w-lg"
                />
              </div>
            );
          }
          return (
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <EditorLayout
                embedded
                experimentId={experimentId}
                name={exp.name}
                rawIdea={exp.raw_idea ?? ""}
                experimentStatus={expStatus}
                landingPage={landingPage}
                onPublished={() => {
                  void loadExperiment();
                  void loadLandingPage();
                }}
                onExperimentRenamed={(nextName) => {
                  setExperiment((prev) =>
                    prev ? { ...prev, name: nextName } : prev,
                  );
                }}
                onRegenerateAll={() => {
                  void loadLandingPage();
                }}
              />
            </div>
          );
        }
        return (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="fv-section-card">
            <h3 className="text-lg font-semibold text-[var(--fv-text)]">
              Choose a template
            </h3>
            <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
              Pick a design for your validation landing page. You can customize
              all copy after generation.
            </p>
            <div className="mt-6">
              <TemplatePicker
                selectedId={selectedTemplate}
                onSelect={setSelectedTemplate}
                onGenerate={handleGenerateLandingPage}
                generating={generatingLp}
              />
            </div>
            </div>
          </div>
        );

      case "metrics":
        return (
          <MetricsStagePanel
            experimentId={experimentId}
            experimentStatus={expStatus}
            experimentName={expDisplayName}
            landingSlug={landingSlug}
            showDistribute={showDistribute}
            onInsightStarted={() => {
              setActiveStage("insight");
              void loadExperiment();
            }}
          />
        );

      case "insight":
        return (
          <InsightStagePanel
            experimentId={experimentId}
            experimentStatus={expStatus}
            onDecision={handleDecision}
          />
        );

      default:
        return null;
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col p-3 sm:p-4">
      <PageHeader
        compact
        title={
          <EditableProjectName
            experimentId={experimentId}
            name={experiment.name}
            rawIdea={experiment.raw_idea ?? ""}
            onRenamed={(nextName) => {
              setExperiment((prev) =>
                prev ? { ...prev, name: nextName } : prev,
              );
            }}
          />
        }
        badge={<StatusBadge status={status} />}
        actions={headerActions}
      />

      {error && (
        <ErrorBanner
          message={error}
          onDismiss={() => setError(null)}
          className="mb-4"
        />
      )}

      {showStageNav && (
        <ExperimentStageNav
          activeStage={activeStage}
          status={status}
          onStageChange={setActiveStage}
        />
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {renderStageContent(experiment)}
      </div>

      <ArchiveProjectDialog
        experimentId={experimentId}
        projectName={experimentDisplayName}
        open={archiveDialogOpen}
        onClose={() => setArchiveDialogOpen(false)}
      />
      <DeleteProjectDialog
        experimentId={experimentId}
        projectName={experimentDisplayName}
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      />
    </div>
  );
}
