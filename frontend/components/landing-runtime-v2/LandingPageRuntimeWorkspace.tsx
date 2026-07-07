"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, FlaskConical, Loader2, RefreshCw } from "lucide-react";
import { LandingPagePreview } from "@/components/landing-page-generator/LandingPagePreview";
import { RuntimeRenderer } from "@/components/landing-runtime-v2/RuntimeRenderer";
import { RuntimeExportMenu } from "@/components/landing-runtime-v2/RuntimeExportMenu";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  ApiError,
  generateLandingPageRuntime,
  getExperiment,
  getLandingPage,
  getLandingPageRuntime,
} from "@/lib/api";
import { resolveLandingPageEditorData } from "@/lib/landing-page-data";
import type { LandingPageV2GenerationStatus } from "@/lib/landing-page-v2-types";
import type { LandingPage } from "@/lib/types";

const POLL_MS = 4000;

const PHASE_LABELS: Record<string, string> = {
  planning_narrative: "Stage 1: Narrative Architect…",
  creative_direction: "Stage 2: Creative Director…",
  visual_composition: "Stage 3: Visual Composer…",
  component_planning: "Stage 4: Component Planner…",
};

export function LandingPageRuntimeWorkspace({
  experimentId,
}: {
  experimentId: string;
}) {
  const [runtimeStatus, setRuntimeStatus] =
    useState<LandingPageV2GenerationStatus | null>(null);
  const [v1LandingPage, setV1LandingPage] = useState<LandingPage | null>(null);
  const [projectName, setProjectName] = useState("Untitled project");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [experiment, runtime, v1Result] = await Promise.all([
        getExperiment(experimentId),
        getLandingPageRuntime(experimentId),
        getLandingPage(experimentId).catch((err) => {
          if (err instanceof ApiError && err.status === 404) return null;
          throw err;
        }),
      ]);
      setProjectName(experiment.name?.trim() || "Untitled project");
      setRuntimeStatus(runtime);
      setV1LandingPage(v1Result);
      setGenerating(runtime.generation_status === "generating");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load previews.");
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!generating) return;
    const timer = window.setInterval(() => {
      void getLandingPageRuntime(experimentId)
        .then((next) => {
          setRuntimeStatus(next);
          if (next.generation_status !== "generating") {
            setGenerating(false);
          }
        })
        .catch(() => {
          /* keep polling */
        });
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [experimentId, generating]);

  const onGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      await generateLandingPageRuntime(experimentId, {
        page_goal: "waitlist",
      });
      const next = await getLandingPageRuntime(experimentId);
      setRuntimeStatus(next);
    } catch (err) {
      setGenerating(false);
      setError(
        err instanceof Error ? err.message : "Failed to start generation.",
      );
    }
  };

  const v1Resolved = v1LandingPage
    ? resolveLandingPageEditorData(v1LandingPage, projectName)
    : null;

  const phaseLabel =
    runtimeStatus?.generation_phase &&
    PHASE_LABELS[runtimeStatus.generation_phase]
      ? PHASE_LABELS[runtimeStatus.generation_phase]
      : "Generating runtime page…";

  if (loading) {
    return <LoadingState label="Loading landing page runtime…" />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col px-4 py-4 sm:px-6">
      <PageHeader
        compact
        title={
          <span className="inline-flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-[var(--fv-accent)]" />
            Landing Page Runtime
          </span>
        }
        description="Experimental narrative-driven runtime. Version 1 template generator is unchanged."
        badge={
          <span className="fv-badge fv-badge-muted text-xs">Experimental</span>
        }
        actions={
          <>
            <RuntimeExportMenu spec={runtimeStatus?.spec} projectName={projectName} />
            <Link
              href={`/experiment/${experimentId}?stage=landing`}
              className="fv-btn-secondary inline-flex items-center gap-1.5 text-sm"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              V1 editor
            </Link>
            <button
              type="button"
              className="fv-btn-primary inline-flex items-center gap-1.5 text-sm"
              disabled={generating}
              onClick={() => void onGenerate()}
            >
              {generating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              {runtimeStatus?.spec ? "Regenerate runtime" : "Generate runtime"}
            </button>
          </>
        }
      />

      {error && (
        <ErrorBanner
          message={error}
          onDismiss={() => setError(null)}
          className="mb-4"
        />
      )}

      {runtimeStatus?.generation_status === "failed" &&
        runtimeStatus.error_detail && (
          <ErrorBanner message={runtimeStatus.error_detail} className="mb-4" />
        )}

      {generating && !runtimeStatus?.spec && (
        <LoadingState label={phaseLabel} />
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <PreviewPanel
          title="Runtime — Narrative + Spec"
          subtitle={
            runtimeStatus?.spec
              ? `${runtimeStatus.spec.pipeline.narrative.business_archetype.replace(/_/g, " ")} · ${runtimeStatus.spec.components.length} components`
              : "No spec yet"
          }
        >
          {runtimeStatus?.spec ? (
            <div className="h-full overflow-auto rounded-lg border border-[var(--fv-border)]">
              <RuntimeRenderer
                spec={runtimeStatus.spec}
                resolvedAssets={runtimeStatus.resolved_assets}
                publicationSlug={runtimeStatus.publication_slug}
              />
            </div>
          ) : (
            !generating && (
              <EmptyPreview
                message="Generate a runtime spec to preview the narrative-driven renderer."
                actionLabel="Generate runtime"
                onAction={() => void onGenerate()}
              />
            )
          )}
        </PreviewPanel>

        <PreviewPanel
          title="Version 1 — Templates"
          subtitle={
            v1Resolved
              ? `${v1Resolved.templateId} template`
              : "No V1 landing page yet"
          }
        >
          {v1Resolved ? (
            <div className="h-[min(720px,70vh)] min-h-[420px] overflow-hidden rounded-lg border border-[var(--fv-border)]">
              <LandingPagePreview
                copy={v1Resolved.copy}
                page={v1Resolved.page}
                projectName={v1Resolved.projectName}
                templateId={v1Resolved.templateId}
                forEditor
                isPublished={Boolean(v1LandingPage?.live_at)}
                publicationSlug={
                  v1LandingPage?.live_at ? v1LandingPage.slug : undefined
                }
                experimentId={experimentId}
              />
            </div>
          ) : (
            <EmptyPreview
              message="V1 landing page not generated yet."
              actionLabel="Open V1 editor"
              href={`/experiment/${experimentId}?stage=landing`}
            />
          )}
        </PreviewPanel>
      </div>

      {runtimeStatus?.spec && !runtimeStatus.publication_slug && (
        <p className="mt-3 text-xs text-[var(--fv-text-muted)]">
          Publish V1 to enable the locked waitlist form in runtime preview.
          Signup, analytics, and conversion tracking always use Fivvle backends.
        </p>
      )}
    </div>
  );
}

function PreviewPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-3 sm:p-4">
      <header className="mb-3 shrink-0">
        <h2 className="text-sm font-semibold text-[var(--fv-text)]">{title}</h2>
        <p className="text-xs text-[var(--fv-text-muted)]">{subtitle}</p>
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}

function EmptyPreview({
  message,
  actionLabel,
  onAction,
  href,
}: {
  message: string;
  actionLabel: string;
  onAction?: () => void;
  href?: string;
}) {
  return (
    <div className="flex h-full min-h-[280px] flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-[var(--fv-border)] p-6 text-center">
      <p className="max-w-sm text-sm text-[var(--fv-text-muted)]">{message}</p>
      {href ? (
        <Link href={href} className="fv-btn-secondary text-sm">
          {actionLabel}
        </Link>
      ) : (
        <button type="button" className="fv-btn-primary text-sm" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
