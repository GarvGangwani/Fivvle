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
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--fv-border)] bg-white/[0.02] px-4 py-3">
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
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[color-mix(in_srgb,var(--fv-success)_30%,transparent)] bg-[color-mix(in_srgb,var(--fv-success)_10%,transparent)] px-4 py-3">
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
            className="fv-btn-ghost inline-flex shrink-0 items-center gap-1.5 px-3 py-2 text-sm no-underline transition-all duration-200"
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
                  <code className="min-w-0 flex-1 truncate rounded-lg bg-white/[0.03] px-3 py-2 font-mono text-[12px] text-[var(--fv-text-muted)]">
                    {url}
                  </code>
                  <button
                    type="button"
                    onClick={() => void navigator.clipboard.writeText(url)}
                    className="fv-btn-ghost shrink-0 px-3 py-1.5 text-[12px] transition-all duration-200"
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
          className={`fv-tab-pill inline-flex flex-1 items-center justify-center gap-1.5 transition-all duration-200 ${
            mobilePanel === "edit" ? "fv-tab-pill-active" : ""
          }`}
        >
          <Pencil className="h-4 w-4" />
          Edit
        </button>
        <button
          type="button"
          onClick={() => setMobilePanel("preview")}
          className={`fv-tab-pill inline-flex flex-1 items-center justify-center gap-1.5 transition-all duration-200 ${
            mobilePanel === "preview" ? "fv-tab-pill-active" : ""
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>

      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(300px,380px)_1fr]">
        <div
          className={`lp-editor-panel flex min-h-0 flex-col overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] ${
            mobilePanel === "edit" ? "flex" : "hidden lg:flex"
          }`}
        >
          <div className="shrink-0 border-b border-[var(--fv-border)] p-6 pb-4">
            <h2 className="text-lg font-semibold text-[var(--fv-text)]">
              Edit Landing Page
            </h2>
            <p className="mt-0.5 text-[13px] text-[var(--fv-text-muted)]">
              {templateMeta?.name ?? templateId}
            </p>

            <div className="mt-4">
              <p className="mb-2 text-[12px] font-medium text-[var(--fv-text-soft)]">
                Template
              </p>
              <div className="flex flex-wrap gap-3">
                {PAGE_TEMPLATES.map((tpl) => {
                  const selected = templateId === tpl.id;
                  return (
                    <button
                      key={tpl.id}
                      type="button"
                      onClick={() => handleTemplateSelect(tpl.id)}
                      className={`flex flex-col items-center gap-1.5 rounded-lg p-1 transition-all duration-200 ${
                        selected
                          ? "ring-2 ring-[var(--fv-accent)]"
                          : "hover:opacity-80"
                      }`}
                      aria-pressed={selected}
                      aria-label={`Select ${tpl.name} template`}
                    >
                      <div
                        className="h-12 w-16 rounded-lg"
                        style={{
                          background: `linear-gradient(135deg, ${tpl.preview.accent}, ${tpl.preview.bg})`,
                        }}
                      />
                      <span className="max-w-[4.5rem] truncate text-center text-[11px] text-[var(--fv-text-muted)]">
                        {tpl.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-6 pt-4">
            <CopyFieldsEditor copy={copy} onChange={handleCopyChange} />
          </div>

          <div className="shrink-0 border-t border-[var(--fv-border)] bg-[var(--fv-surface)] p-6">
            {isLive ? (
              <div className="space-y-2 text-center">
                <span className="badge-proceed">Published</span>
                {publishedSlug && (
                  <Link
                    href={`/e/${publishedSlug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="fv-btn-ghost flex w-full items-center justify-center gap-2 py-2.5 text-sm no-underline transition-all duration-200"
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
