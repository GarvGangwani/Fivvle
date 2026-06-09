"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ExternalLink, Eye, Pencil } from "lucide-react";
import type { CopyJson, LandingPage, PageJson } from "@/lib/types";
import {
  defaultColorModeForTemplate,
  PAGE_TEMPLATES,
  type TemplateId,
} from "@/lib/templates";
import { defaultPaletteForTemplate } from "@/lib/color-palettes";
import { patchLandingPage } from "@/lib/api";
import {
  resolveLandingPageEditorData,
  syncPageJsonSections,
} from "@/lib/landing-page-data";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { LandingPagePreview } from "@/components/landing-page-generator/LandingPagePreview";
import { PublishPanel } from "@/components/landing-page-generator/PublishPanel";
import { useToast } from "@/components/ui/ToastProvider";
import { CopyFieldsEditor } from "./CopyFieldsEditor";
import "./editor-panel.css";

type MobilePanel = "edit" | "preview";

interface EditorLayoutProps {
  experimentId: string;
  experimentName: string;
  experimentStatus: string;
  landingPage: LandingPage;
  onPublished?: () => void;
}

export function EditorLayout({
  experimentId,
  experimentName,
  experimentStatus,
  landingPage,
  onPublished,
}: EditorLayoutProps) {
  const resolved = resolveLandingPageEditorData(landingPage);

  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("edit");
  const [copy, setCopy] = useState<CopyJson>(resolved.copy);
  const [page, setPage] = useState<PageJson>(resolved.page);
  const [templateId, setTemplateId] = useState<TemplateId>(resolved.templateId);
  const [publishedSlug, setPublishedSlug] = useState(landingPage.slug);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { toast } = useToast();

  const projectName = resolved.projectName;
  const templateMeta = PAGE_TEMPLATES.find((t) => t.id === templateId);
  const isLive = experimentStatus === "LANDING_LIVE";

  useEffect(() => {
    const next = resolveLandingPageEditorData(landingPage);
    setCopy(next.copy);
    setPage(next.page);
    setTemplateId(next.templateId);
    setPublishedSlug(landingPage.slug);
  }, [landingPage]);

  const persistPatch = useCallback(
    (nextCopy: CopyJson, nextPage: PageJson, nextTemplateId: TemplateId) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        void patchLandingPage(experimentId, {
          copy_json: nextCopy,
          page_json: nextPage,
          template_id: nextTemplateId,
        })
          .then(() => {
            toast("Changes saved", "success");
          })
          .catch(() => {
            toast("Could not save changes", "error");
          });
      }, 500);
    },
    [experimentId, toast],
  );

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  const handleTemplateSelect = (id: TemplateId) => {
    setTemplateId(id);
    setShowTemplatePicker(false);
    const nextPage: PageJson = syncPageJsonSections(
      {
        ...page,
        template_id: id,
        template_name: PAGE_TEMPLATES.find((t) => t.id === id)?.name,
        color_mode: defaultColorModeForTemplate(id),
        color_palette: defaultPaletteForTemplate(id),
      },
      copy,
    );
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

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3"
        style={{
          borderColor: "rgba(255,255,255,0.07)",
          background: "rgba(255,255,255,0.02)",
        }}
      >
        <div className="min-w-0">
          <p className="truncate text-[15px] font-semibold text-[var(--fv-text)]">
            {experimentName}
          </p>
          <p className="mt-0.5 text-[13px] text-[var(--fv-text-muted)]">
            {templateMeta?.name ?? templateId}
          </p>
        </div>
        <StatusBadge status={experimentStatus} />
      </div>

      {isLive && publishedSlug && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[rgba(16,185,129,0.3)] bg-[rgba(16,185,129,0.1)] px-4 py-3">
          <div className="min-w-0">
            <span className="badge-proceed">Published</span>
            <p className="mt-2 truncate text-[13px] text-[var(--fv-text-soft)]">
              Your page is live at{" "}
              <span className="font-medium text-[var(--fv-success)]">
                fivvle.io/e/{publishedSlug}
              </span>
            </p>
          </div>
          <Link
            href={`/e/${publishedSlug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="fv-btn-ghost inline-flex shrink-0 items-center gap-1.5 px-3 py-2 text-sm no-underline"
          >
            View live
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>
      )}

      {isLive && publishedSlug && (
        <div className="mb-4 rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-4">
          <p className="fv-panel-label mb-3">Share with tracking</p>
          <p className="mb-3 text-[12px] text-[var(--fv-text-muted)]">
            Each link tracks which channel drives traffic. Use these when sharing.
          </p>
          <div className="space-y-2">
            {[
              { label: "Twitter / X", tag: "twitter" },
              { label: "LinkedIn", tag: "linkedin" },
              { label: "Reddit", tag: "reddit" },
              { label: "Email", tag: "email" },
              { label: "Friends & family", tag: "warm" },
            ].map(({ label, tag }) => {
              const url = `${window.location.origin}/e/${publishedSlug}?ref=${tag}`;
              return (
                <div key={tag} className="flex items-center gap-2">
                  <span className="w-28 shrink-0 text-[13px] text-[var(--fv-text-soft)]">
                    {label}
                  </span>
                  <code className="min-w-0 flex-1 truncate rounded bg-white/[0.03] px-3 py-2 font-mono text-[12px] text-[var(--fv-text-muted)]">
                    {url}
                  </code>
                  <button
                    type="button"
                    onClick={() => void navigator.clipboard.writeText(url)}
                    className="fv-btn-ghost shrink-0 px-3 py-1.5 text-[12px]"
                  >
                    Copy
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mb-4 flex gap-2 transition-opacity duration-200 lg:hidden">
        <button
          type="button"
          onClick={() => setMobilePanel("edit")}
          className={`fv-tab-pill inline-flex flex-1 items-center justify-center gap-1.5 ${
            mobilePanel === "edit" ? "fv-tab-pill-active" : ""
          }`}
        >
          <Pencil className="h-4 w-4" />
          Edit
        </button>
        <button
          type="button"
          onClick={() => setMobilePanel("preview")}
          className={`fv-tab-pill inline-flex flex-1 items-center justify-center gap-1.5 ${
            mobilePanel === "preview" ? "fv-tab-pill-active" : ""
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>

      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(300px,380px)_1fr]">
        <div
          className={`lp-editor-panel flex flex-col overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] ${
            mobilePanel === "edit" ? "flex" : "hidden lg:flex"
          }`}
        >
          <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-5">
            <div>
              <h2 className="text-[16px] font-semibold text-[var(--fv-text)]">
                Edit Your Landing Page
              </h2>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[13px]">
                <span className="text-[var(--fv-text-soft)]">
                  {templateMeta?.name ?? templateId}
                </span>
                <button
                  type="button"
                  onClick={() => setShowTemplatePicker((v) => !v)}
                  className="text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)]"
                >
                  Change template
                </button>
              </div>
            </div>

            {showTemplatePicker && (
              <div className="grid gap-2">
                {PAGE_TEMPLATES.map((tpl) => (
                  <button
                    key={tpl.id}
                    type="button"
                    onClick={() => handleTemplateSelect(tpl.id)}
                    className={`host-card text-left ${
                      templateId === tpl.id ? "host-card selected" : ""
                    }`}
                  >
                    <div
                      className="h-1 w-full"
                      style={{ background: tpl.preview.accent }}
                    />
                    <div className="p-3">
                      <p className="text-[13px] font-semibold text-fv-text">
                        {tpl.name}
                      </p>
                      <p className="mt-0.5 text-[11px] text-[var(--fv-text-muted)]">
                        {tpl.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}

            <CopyFieldsEditor copy={copy} onChange={handleCopyChange} />
          </div>

          <div className="shrink-0 border-t border-[var(--fv-border)] p-4 sm:p-5">
            {isLive ? (
              <div className="space-y-2 text-center">
                <span className="badge-proceed">Published</span>
                {publishedSlug && (
                  <Link
                    href={`/e/${publishedSlug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="fv-btn-ghost flex w-full items-center justify-center gap-2 py-2.5 text-sm no-underline"
                  >
                    View at /e/{publishedSlug}
                    <ExternalLink className="h-4 w-4" />
                  </Link>
                )}
              </div>
            ) : (
              <PublishPanel
                projectId={experimentId}
                projectName={projectName}
                outputVersion={landingPage.output_version ?? 1}
                fullWidth
                disabled={false}
                onPublished={(res) => {
                  setPublishedSlug(res.slug);
                  onPublished?.();
                }}
              />
            )}
          </div>
        </div>

        <div
          className={`min-h-[480px] overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-bg)] transition-opacity duration-200 lg:min-h-[calc(100vh-14rem)] ${
            mobilePanel === "preview" ? "block" : "hidden lg:block"
          }`}
        >
          <LandingPagePreview
            copy={copy}
            page={{ ...page, template_id: templateId }}
            projectName={projectName}
            templateId={templateId}
          />
        </div>
      </div>
    </div>
  );
}
