"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  Copy,
  ExternalLink,
  Eye,
  RefreshCw,
  Pencil,
  Rocket,
} from "lucide-react";
import type { CopyJson, LandingPage, PageJson } from "@/lib/types";
import {
  defaultColorModeForTemplate,
  PAGE_TEMPLATES,
  type TemplateId,
} from "@/lib/templates";
import { defaultPaletteForTemplate, inferColorModeFromPalette, resolveColorPalette } from "@/lib/color-palettes";
import { resolveBranding } from "@/lib/branding";
import {
  ApiError,
  generateLandingPage,
  getExperiment,
  getLandingPage,
  patchLandingPage,
  publishProject,
} from "@/lib/api";
import {
  resolveLandingPageEditorData,
  syncPageJsonSections,
} from "@/lib/landing-page-data";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import {
  canEditLandingPage,
  landingPageEditBlockedReason,
} from "@/lib/landing-flow";
import { EditableProjectName } from "@/components/experiment/EditableProjectName";
import { LandingPagePreview } from "@/components/landing-page-editor/LandingPagePreview";
import type { PreviewSaveStatus } from "@/components/landing-page-editor/PreviewSaveStatus";
import { useToast } from "@/components/ui/ToastProvider";
import { ShareLinksPanel, SHARE_CHANNELS } from "@/components/distribution/ShareLinksPanel";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { CopyFieldsEditor, type CopySectionId } from "./CopyFieldsEditor";
import { LandingPageSlugEditor } from "./LandingPageSlugEditor";
import { SurfaceStylePicker } from "./SurfaceStylePicker";
import { ColorThemePicker } from "@/components/landing-page-editor/ColorThemePicker";
import { BrandIconPicker } from "@/components/landing-page-editor/BrandIconPicker";
import { defaultSurfaceForTemplate, formatSurfaceSummary, resolveSurface } from "@/lib/surface";
import { buildPageForTemplatePreview } from "@/lib/template-preview-page";
import {
  buildPublicLandingPageUrl,
  formatPublicLandingHost,
} from "@/lib/landing-host";
import { CollapsibleSection } from "./CollapsibleSection";
import { TemplatePreviewThumb } from "./TemplatePreviewThumb";
import "./editor-panel.css";

type EditorTab = "content" | "design" | "publish";
type MobilePanel = "edit" | "preview";

interface EditorLayoutProps {
  experimentId: string;
  name: string | null | undefined;
  rawIdea: string;
  experimentStatus: string;
  landingPage: LandingPage;
  embedded?: boolean;
  onPublished?: () => void;
  onExperimentRenamed?: (name: string) => void;
  onRegenerateAll?: () => void;
}

export function EditorLayout({
  experimentId,
  name,
  rawIdea,
  experimentStatus,
  landingPage,
  embedded = false,
  onPublished,
  onExperimentRenamed,
  onRegenerateAll,
}: EditorLayoutProps) {
  const displayName = getExperimentDisplayName({ name, raw_idea: rawIdea });
  const resolved = resolveLandingPageEditorData(landingPage, displayName);

  const [editorTab, setEditorTab] = useState<EditorTab>("design");
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("edit");
  const [copy, setCopy] = useState<CopyJson>(resolved.copy);
  const [page, setPage] = useState<PageJson>(resolved.page);
  const [templateId, setTemplateId] = useState<TemplateId>(resolved.templateId);
  const [publishedSlug, setPublishedSlug] = useState(landingPage.slug);
  const [publishing, setPublishing] = useState(false);
  const [regeneratingAll, setRegeneratingAll] = useState(false);
  const [regeneratingSection, setRegeneratingSection] =
    useState<CopySectionId | null>(null);
  const [regenMessage, setRegenMessage] = useState<string | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveAbortRef = useRef<AbortController | null>(null);
  const savedFadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isRegeneratingRef = useRef(false);
  const [saveStatus, setSaveStatus] = useState<PreviewSaveStatus>("idle");
  const [saveErrorDetail, setSaveErrorDetail] = useState<string | null>(null);
  const { toast } = useToast();

  const projectName = resolved.projectName;
  const isLive = landingPage.live_at != null;
  const canEdit = canEditLandingPage(experimentStatus);
  const editBlockedReason = canEdit
    ? null
    : landingPageEditBlockedReason(experimentStatus);
  const publicUrl = publishedSlug
    ? buildPublicLandingPageUrl(publishedSlug)
    : null;
  const publicHost = publishedSlug
    ? formatPublicLandingHost(publishedSlug)
    : null;
  const isRegenerating = regeneratingAll || regeneratingSection !== null;

  useEffect(() => {
    isRegeneratingRef.current = isRegenerating;
  }, [isRegenerating]);

  useEffect(() => {
    if (isRegenerating) return;
    const next = resolveLandingPageEditorData(landingPage, displayName);
    setCopy(next.copy);
    setPage(next.page);
    setTemplateId(next.templateId);
    setPublishedSlug(landingPage.slug);
  }, [landingPage, displayName, isRegenerating]);

  const persistPatch = useCallback(
    (nextCopy: CopyJson, nextPage: PageJson, nextTemplateId: TemplateId) => {
      if (isRegeneratingRef.current) return;
      if (!canEditLandingPage(experimentStatus)) {
        setSaveErrorDetail(landingPageEditBlockedReason(experimentStatus));
        setSaveStatus("error");
        return;
      }
      if (savedFadeTimerRef.current) {
        clearTimeout(savedFadeTimerRef.current);
        savedFadeTimerRef.current = null;
      }
      setSaveErrorDetail(null);
      setSaveStatus("pending");
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        if (isRegeneratingRef.current) return;
        if (!canEditLandingPage(experimentStatus)) {
          setSaveErrorDetail(landingPageEditBlockedReason(experimentStatus));
          setSaveStatus("error");
          return;
        }
        setSaveStatus("saving");
        saveAbortRef.current?.abort();
        const controller = new AbortController();
        saveAbortRef.current = controller;
        void patchLandingPage(
          experimentId,
          {
            copy_json: nextCopy,
            page_json: nextPage,
            template_id: nextTemplateId,
          },
          { signal: controller.signal },
        )
          .then(() => {
            if (!controller.signal.aborted) {
              setSaveErrorDetail(null);
              setSaveStatus("saved");
              if (savedFadeTimerRef.current) clearTimeout(savedFadeTimerRef.current);
              savedFadeTimerRef.current = setTimeout(() => {
                setSaveStatus("idle");
              }, 2500);
            }
          })
          .catch((err: unknown) => {
            if (controller.signal.aborted) return;
            if (err instanceof ApiError) {
              const detail =
                typeof err.body === "object" &&
                err.body !== null &&
                "detail" in err.body &&
                typeof (err.body as { detail: unknown }).detail === "string"
                  ? (err.body as { detail: string }).detail
                  : null;
              if (detail) {
                setSaveErrorDetail(detail);
              } else if (err.status === 0) {
                setSaveErrorDetail(
                  "Could not reach the server. Check your connection.",
                );
              } else {
                setSaveErrorDetail("Could not save changes. Please try again.");
              }
            } else {
              setSaveErrorDetail("Could not save changes. Please try again.");
            }
            setSaveStatus("error");
          });
      }, 500);
    },
    [experimentId, experimentStatus],
  );

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      if (savedFadeTimerRef.current) clearTimeout(savedFadeTimerRef.current);
    };
  }, []);

  const handleTemplateSelect = (id: TemplateId) => {
    setTemplateId(id);
    const nextPage = buildPageForTemplatePreview(page, copy, id);
    setPage(nextPage);
    persistPatch(copy, nextPage, id);
  };

  const handleCopyChange = (nextCopy: CopyJson) => {
    setCopy(nextCopy);
    const nextPage = syncPageJsonSections(
      { ...page, template_id: templateId },
      nextCopy,
    );
    setPage(nextPage);
    persistPatch(nextCopy, nextPage, templateId);
  };

  const handlePageDesignChange = (nextPage: PageJson) => {
    const synced = syncPageJsonSections(
      { ...nextPage, template_id: templateId },
      copy,
    );
    setPage(synced);
    persistPatch(copy, synced, templateId);
  };

  const handleSectionImageChange = (slotId: string, url: string | null) => {
    const prev = page.section_images ?? {};
    const nextImages = { ...prev };
    if (url) {
      nextImages[slotId] = url;
    } else {
      delete nextImages[slotId];
    }
    handlePageDesignChange({
      ...page,
      section_images: nextImages,
    });
  };

  const handlePublish = async () => {
    setPublishing(true);
    try {
      const res = await publishProject(experimentId, { cta_mode: "waitlist" });
      setPublishedSlug(res.slug);
      toast("Landing page is live", "success");
      onPublished?.();
    } catch {
      toast("Publish failed — try again", "error");
    } finally {
      setPublishing(false);
    }
  };

  const cancelPendingSave = () => {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    saveAbortRef.current?.abort();
    saveAbortRef.current = null;
  };

  const REGEN_POLL_INTERVAL_MS = 1000;
  const REGEN_POLL_MAX_ATTEMPTS = 360;
  const REGEN_IDLE_MAX_ATTEMPTS = 360;

  const wait = (ms: number) =>
    new Promise<void>((resolve) => {
      setTimeout(resolve, ms);
    });

  const wasGeneratedAfter = (
    generatedAt: string | undefined,
    pollStartedAt: number,
  ) => {
    if (!generatedAt) return false;
    const parsed = Date.parse(generatedAt);
    if (Number.isNaN(parsed)) return false;
    return parsed >= pollStartedAt - 2_000;
  };

  const waitForLandingGenerationIdle = async () => {
    for (let attempt = 0; attempt < REGEN_IDLE_MAX_ATTEMPTS; attempt += 1) {
      const experiment = await getExperiment(experimentId);
      if (experiment.status !== "LANDING_GENERATING") {
        return;
      }
      await wait(REGEN_POLL_INTERVAL_MS);
    }
    throw new Error(
      "Landing page generation is still running. Wait a moment and try again.",
    );
  };

  const fetchRegeneratedLandingPage = async (options: {
    expectedHint: string;
    pollStartedAt: number;
    section?: CopySectionId;
    previousSectionJson?: string;
    previousGenerationId?: string | null;
  }) => {
    const {
      expectedHint,
      pollStartedAt,
      section,
      previousSectionJson,
      previousGenerationId,
    } = options;

    for (let attempt = 0; attempt < REGEN_POLL_MAX_ATTEMPTS; attempt += 1) {
      const experiment = await getExperiment(experimentId);
      let lp: LandingPage | null = null;

      try {
        lp = await getLandingPage(experimentId);
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 404)) {
          throw err;
        }
      }

      if (lp) {
        const nextHint = lp.page_json?.meta?.regeneration_hint;
        const nextGenerationId = lp.page_json?.meta?.generation_id;
        const generatedAt = lp.page_json?.meta?.generated_at;
        const generatedAfterPoll = wasGeneratedAfter(generatedAt, pollStartedAt);

        if (nextHint === expectedHint) {
          return lp;
        }

        if (section && previousSectionJson != null && generatedAfterPoll) {
          const nextSection = resolveLandingPageEditorData(lp, displayName).copy[
            section
          ];
          if (JSON.stringify(nextSection ?? null) !== previousSectionJson) {
            return lp;
          }
        }

        if (
          generatedAfterPoll &&
          previousGenerationId &&
          nextGenerationId &&
          nextGenerationId !== previousGenerationId
        ) {
          return lp;
        }
      }

      if (
        experiment.status !== "LANDING_GENERATING" &&
        experiment.status !== "LANDING_DRAFT" &&
        experiment.status !== "LANDING_LIVE" &&
        attempt >= 5
      ) {
        throw new Error("Landing page regeneration failed. Please try again.");
      }

      await wait(REGEN_POLL_INTERVAL_MS);
    }

    throw new Error("Regeneration timed out. Please try again.");
  };

  const handleRegenerateAll = async () => {
    if (regeneratingAll || regeneratingSection) return;
    cancelPendingSave();
    setRegeneratingAll(true);
    setRegenMessage("Regenerating all sections. Please wait…");
    try {
      const hint = `all:${Date.now()}:${crypto.randomUUID()}`;
      const previousGenerationId = page?.meta?.generation_id ?? null;
      await waitForLandingGenerationIdle();
      const pollStartedAt = Date.now();
      await generateLandingPage(experimentId, {
        template_id: templateId,
        page_goal: "waitlist",
        regeneration_hint: hint,
      });
      const regeneratedLandingPage = await fetchRegeneratedLandingPage({
        expectedHint: hint,
        pollStartedAt,
        previousGenerationId,
      });
      const resolved = resolveLandingPageEditorData(
        regeneratedLandingPage,
        displayName,
      );
      setCopy(resolved.copy);
      setPage(resolved.page);
      setTemplateId(resolved.templateId);
      toast("All sections regenerated", "success");
      onRegenerateAll?.();
    } catch (err) {
      const detail =
        err instanceof ApiError &&
        err.body &&
        typeof err.body === "object" &&
        "detail" in err.body
          ? String((err.body as { detail?: unknown }).detail ?? "")
          : err instanceof Error
            ? err.message
            : "";
      toast(
        detail ? `Failed to regenerate all sections: ${detail}` : "Failed to regenerate all sections",
        "error",
      );
    } finally {
      setRegeneratingAll(false);
      setRegenMessage(null);
    }
  };

  const handleRegenerateSection = async (section: CopySectionId) => {
    if (regeneratingSection || regeneratingAll) return;

    cancelPendingSave();
    setRegeneratingSection(section);
    const label = `${section.charAt(0).toUpperCase()}${section.slice(1)}`;
    setRegenMessage(`Regenerating ${label}. Please wait…`);
    try {
      const regenerateOnce = async (hint: string) => {
        const previousSectionJson = JSON.stringify(copy[section] ?? null);
        const previousGenerationId = page?.meta?.generation_id ?? null;
        await waitForLandingGenerationIdle();
        const pollStartedAt = Date.now();
        await generateLandingPage(experimentId, {
          template_id: templateId,
          page_goal: "waitlist",
          regeneration_hint: hint,
        });
        return await fetchRegeneratedLandingPage({
          expectedHint: hint,
          pollStartedAt,
          section,
          previousSectionJson,
          previousGenerationId,
        });
      };

      let regeneratedLandingPage = await regenerateOnce(
        `${section}:${Date.now()}:${crypto.randomUUID()}`,
      );
      let resolvedRegen = resolveLandingPageEditorData(
        regeneratedLandingPage,
        displayName,
      );
      let regeneratedSection = resolvedRegen.copy[section];
      const currentSection = copy[section];

      // If output is identical (cache/provider determinism), force one more variant attempt.
      if (JSON.stringify(regeneratedSection) === JSON.stringify(currentSection)) {
        regeneratedLandingPage = await regenerateOnce(
          `${section}:${Date.now()}:${crypto.randomUUID()}:retry`,
        );
        resolvedRegen = resolveLandingPageEditorData(
          regeneratedLandingPage,
          displayName,
        );
        regeneratedSection = resolvedRegen.copy[section];
      }

      if (regeneratedSection == null) {
        throw new Error(`Missing regenerated section: ${section}`);
      }

      const nextCopy: CopyJson = {
        ...copy,
        [section]: resolvedRegen.copy[section],
      };
      const nextPage = syncPageJsonSections(
        {
          ...page,
          ...resolvedRegen.page,
          template_id: templateId,
          meta: resolvedRegen.page.meta ?? page.meta,
        },
        nextCopy,
      );
      setCopy(nextCopy);
      setPage(nextPage);
      persistPatch(nextCopy, nextPage, templateId);

      toast(
        `${section.charAt(0).toUpperCase()}${section.slice(1)} regenerated`,
        "success",
      );
    } catch (err) {
      const detail =
        err instanceof ApiError &&
        err.body &&
        typeof err.body === "object" &&
        "detail" in err.body
          ? String((err.body as { detail?: unknown }).detail ?? "")
          : err instanceof Error
            ? err.message
            : "";
      toast(
        detail ? `Could not regenerate ${section}: ${detail}` : `Could not regenerate ${section}`,
        "error",
      );
    } finally {
      setRegeneratingSection(null);
      setRegenMessage(null);
    }
  };

  const copyPublicUrl = () => {
    if (!publicUrl) return;
    void navigator.clipboard.writeText(publicUrl).then(() => {
      toast("Link copied", "success");
    });
  };

  const editorTabs: { id: EditorTab; label: string }[] = [
    { id: "content", label: "Copy" },
    { id: "design", label: "Design" },
    { id: "publish", label: isLive ? "Share" : "Publish" },
  ];

  return (
    <div
      className={`lp-editor-root flex min-h-0 flex-col overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] ${
        embedded ? "h-full" : "h-[calc(100dvh-4.5rem)]"
      }`}
    >
      {/* Toolbar */}
      <div className="lp-editor-toolbar shrink-0">
        {!embedded && (
          <>
            <Link
              href={`/experiment/${experimentId}`}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[13px] font-medium text-[var(--fv-text-muted)] no-underline transition-colors hover:bg-[var(--fv-hover-overlay)] hover:text-[var(--fv-text)]"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Back</span>
            </Link>

            <div className="min-w-0 flex-1">
              <EditableProjectName
                experimentId={experimentId}
                name={name}
                rawIdea={rawIdea}
                variant="inline"
                onRenamed={onExperimentRenamed}
              />
            </div>

            <StatusBadge status={experimentStatus} />
          </>
        )}

        <div
          className="lp-editor-tabs lp-editor-tabs--toolbar"
          role="tablist"
          aria-label="Editor sections"
        >
          {editorTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={editorTab === tab.id}
              onClick={() => setEditorTab(tab.id)}
              className={`lp-editor-tab ${
                editorTab === tab.id ? "lp-editor-tab-active" : ""
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="lp-editor-toolbar-actions">
          {publicHost && (
            <div className="lp-url-pill">
              <span>{publicHost}</span>
              <button
                type="button"
                onClick={copyPublicUrl}
                className="shrink-0 rounded p-0.5 text-[var(--fv-text-muted)] hover:text-[var(--fv-accent)]"
                aria-label="Copy public URL"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {isLive && publicUrl ? (
            <a
              href={publicUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="fv-btn-ghost inline-flex shrink-0 items-center gap-1.5 px-3 py-2 text-[13px] no-underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">View live</span>
            </a>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={regeneratingAll || publishing}
                onClick={() => void handleRegenerateAll()}
                className="fv-btn-ghost inline-flex shrink-0 items-center gap-1.5 px-3 py-2 text-[13px] disabled:opacity-60"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${regeneratingAll ? "animate-spin" : ""}`}
                />
                <span className="hidden sm:inline">
                  {regeneratingAll ? "Regenerating…" : "Regenerate all"}
                </span>
              </button>
              <button
                type="button"
                disabled={publishing || regeneratingAll}
                onClick={() => void handlePublish()}
                className="fv-btn-primary inline-flex shrink-0 items-center gap-1.5 px-4 py-2 text-[13px] disabled:opacity-60"
              >
                <Rocket className="h-3.5 w-3.5" />
                {publishing ? "Publishing…" : "Publish"}
              </button>
            </div>
          )}
        </div>
      </div>

      {!canEdit && editBlockedReason ? (
        <p className="shrink-0 border-b border-[var(--fv-border)] bg-[var(--fv-surface-2)] px-4 py-2.5 text-sm leading-relaxed text-[var(--fv-text-muted)]">
          {editBlockedReason}
        </p>
      ) : null}

      {/* Mobile panel toggle */}
      <div className="flex shrink-0 gap-2 border-b border-[var(--fv-border)] p-2 lg:hidden">
        <button
          type="button"
          onClick={() => setMobilePanel("edit")}
          className={`fv-tab-pill inline-flex min-h-[40px] flex-1 items-center justify-center gap-1.5 text-[13px] ${
            mobilePanel === "edit" ? "fv-tab-pill-active" : ""
          }`}
        >
          <Pencil className="h-4 w-4" />
          Edit
        </button>
        <button
          type="button"
          onClick={() => setMobilePanel("preview")}
          className={`fv-tab-pill inline-flex min-h-[40px] flex-1 items-center justify-center gap-1.5 text-[13px] ${
            mobilePanel === "preview" ? "fv-tab-pill-active" : ""
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>

      {/* Main split */}
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(360px,440px)_1fr] xl:grid-cols-[minmax(400px,480px)_1fr]">
        {/* Left panel */}
        <div
          className={`flex min-h-0 flex-col border-[var(--fv-border)] lg:border-r ${
            mobilePanel === "edit" ? "flex" : "hidden lg:flex"
          }`}
        >
          <div className="lp-editor-scroll p-4">
            {editorTab === "content" && (
              <CopyFieldsEditor
                copy={copy}
                onChange={handleCopyChange}
                onRegenerateSection={handleRegenerateSection}
                regeneratingSection={regeneratingSection}
                disabled={isRegenerating}
              />
            )}

            {editorTab === "design" && (
              <div className="lp-collapse-stack">
                <CollapsibleSection
                  title="Template"
                  summary={
                    PAGE_TEMPLATES.find((t) => t.id === templateId)?.name ??
                    "Choose layout"
                  }
                  defaultOpen
                >
                  <p className="mb-3 text-[12px] text-[var(--fv-text-muted)]">
                    Pick a template — your copy stays the same.
                  </p>
                  <div
                    className="grid grid-cols-2 gap-2"
                    role="radiogroup"
                    aria-label="Landing page template"
                  >
                    {PAGE_TEMPLATES.map((tpl) => {
                      const selected = templateId === tpl.id;
                      return (
                        <div
                          key={tpl.id}
                          role="radio"
                          tabIndex={0}
                          aria-checked={selected}
                          onClick={() => handleTemplateSelect(tpl.id)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              handleTemplateSelect(tpl.id);
                            }
                          }}
                          className={`lp-template-chip ${
                            selected ? "lp-template-chip-selected" : ""
                          }`}
                        >
                          <TemplatePreviewThumb
                            templateId={tpl.id}
                            copy={copy}
                            page={page}
                            projectName={projectName}
                          />
                          <span className="truncate text-[11px] font-semibold text-[var(--fv-text-soft)]">
                            {tpl.name}
                          </span>
                          {selected && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[var(--fv-accent)]">
                              <Check className="h-3 w-3" />
                              Active
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CollapsibleSection>

                <CollapsibleSection
                  title="Color theme"
                  summary={`${inferColorModeFromPalette(resolveColorPalette(page, templateId))} · ${
                    resolveColorPalette(page, templateId).preset
                  }`}
                >
                  <ColorThemePicker
                    templateId={templateId}
                    page={page}
                    copy={copy}
                    projectName={projectName}
                    disabled={isRegenerating}
                    showExport={false}
                    onChange={(_, nextPage) => handlePageDesignChange(nextPage)}
                    onPersist={() => {}}
                  />
                </CollapsibleSection>

                <CollapsibleSection
                  title="Brand icon"
                  summary={`${resolveBranding(page, projectName).icon_mode} · ${resolveBranding(page, projectName).logo_scale}%`}
                >
                  <BrandIconPicker
                    projectId={experimentId}
                    templateId={templateId}
                    projectName={projectName}
                    page={page}
                    disabled={isRegenerating}
                    onChange={(_, nextPage) => handlePageDesignChange(nextPage)}
                    onPersist={() => {}}
                  />
                </CollapsibleSection>

                <CollapsibleSection
                  title="Surface & atmosphere"
                  summary={formatSurfaceSummary(resolveSurface(page))}
                >
                  <SurfaceStylePicker
                    page={page}
                    disabled={isRegenerating}
                    onChange={handlePageDesignChange}
                  />
                </CollapsibleSection>
              </div>
            )}

            {editorTab === "publish" && (
              <div className="lp-collapse-stack">
                {publishedSlug && (
                  <CollapsibleSection
                    title="Startup URL"
                    summary={publicHost ?? undefined}
                    defaultOpen
                  >
                    <LandingPageSlugEditor
                      experimentId={experimentId}
                      currentSlug={publishedSlug}
                      projectName={projectName}
                      isLive={isLive}
                      embedded
                      onSlugSaved={(slug) => {
                        setPublishedSlug(slug);
                        toast("URL updated", "success");
                      }}
                    />
                    {isLive && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={copyPublicUrl}
                          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px]"
                        >
                          <Copy className="h-3.5 w-3.5" />
                          Copy link
                        </button>
                        {publicUrl && (
                          <a
                            href={publicUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] no-underline"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Open
                          </a>
                        )}
                      </div>
                    )}
                  </CollapsibleSection>
                )}

                {isLive && publishedSlug && (
                  <CollapsibleSection
                    title="Share with tracking"
                    summary={`${SHARE_CHANNELS.length} channel links`}
                  >
                    <ShareLinksPanel
                      slug={publishedSlug}
                      experimentName={displayName}
                      showDescription={false}
                    />
                  </CollapsibleSection>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Preview */}
        <div
          className={`min-h-0 overflow-hidden bg-[var(--fv-bg)] ${
            mobilePanel === "preview" ? "flex flex-col" : "hidden lg:flex lg:flex-col"
          }`}
        >
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <LandingPagePreview
              copy={copy}
              page={{ ...page, template_id: templateId }}
              projectName={projectName}
              templateId={templateId}
              mobileFluid={mobilePanel === "preview"}
              forEditor
              isPublished={isLive}
              publicationSlug={isLive ? publishedSlug : undefined}
              ctaConfig={isLive ? { mode: "waitlist" } : undefined}
              experimentId={experimentId}
              onSectionImageChange={handleSectionImageChange}
              onCopyChange={handleCopyChange}
              saveStatus={saveStatus}
              saveErrorDetail={saveErrorDetail}
            />
          </div>
        </div>
      </div>
      {isRegenerating && (
        <div className="fixed inset-0 z-[220] flex items-center justify-center bg-black/60 backdrop-blur-[1px]">
          <div className="w-[min(92vw,420px)] rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-5 shadow-2xl">
            <div className="flex items-start gap-3">
              <RefreshCw className="mt-0.5 h-5 w-5 animate-spin text-[var(--fv-accent)]" />
              <div>
                <p className="text-sm font-semibold text-[var(--fv-text)]">
                  Regenerating content
                </p>
                <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
                  {regenMessage ?? "Please wait while we regenerate your landing page copy."}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
