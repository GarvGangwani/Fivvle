"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ExternalLink, Eye, Pencil } from "lucide-react";
import type { CopyJson, LandingPage, PageJson } from "@/lib/types";
import {
  defaultColorModeForTemplate,
  resolveTemplateId,
  type TemplateId,
} from "@/lib/templates";
import { defaultPaletteForTemplate } from "@/lib/color-palettes";
import { patchLandingPage } from "@/lib/api";
import { ThemePicker } from "@/components/landing-page-generator/ThemePicker";
import { PublishPanel } from "@/components/landing-page-generator/PublishPanel";
import { LandingPagePreview } from "@/components/landing-page-generator/LandingPagePreview";
import { CopyFieldsEditor } from "./CopyFieldsEditor";
import "./editor-panel.css";

type MobilePanel = "edit" | "preview";

interface EditorLayoutProps {
  experimentId: string;
  experimentStatus: string;
  landingPage: LandingPage;
  onPublished?: () => void;
}

export function EditorLayout({
  experimentId,
  experimentStatus,
  landingPage,
  onPublished,
}: EditorLayoutProps) {
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("edit");
  const [copy, setCopy] = useState<CopyJson>(landingPage.copy_json ?? {});
  const [page, setPage] = useState<PageJson>(landingPage.page_json ?? {});
  const [templateId, setTemplateId] = useState<TemplateId>(() =>
    resolveTemplateId(landingPage.page_json?.template_id ?? landingPage.template_id),
  );
  const [publishedSlug, setPublishedSlug] = useState(landingPage.slug);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const projectName =
    landingPage.headline ||
    copy.hero?.headline ||
    "My Startup";

  const isLive = experimentStatus === "LANDING_LIVE";

  const persistPatch = useCallback(
    (nextCopy: CopyJson, nextPage: PageJson, nextTemplateId: TemplateId) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        void patchLandingPage(experimentId, {
          copy_json: nextCopy,
          page_json: nextPage,
          template_id: nextTemplateId,
        }).catch(() => {
          /* PATCH may not be available yet — local preview still works */
        });
      }, 500);
    },
    [experimentId],
  );

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  const handleTemplateSelect = (id: TemplateId) => {
    setTemplateId(id);
    const nextPage: PageJson = {
      ...page,
      template_id: id,
      color_mode: defaultColorModeForTemplate(id),
      color_palette: defaultPaletteForTemplate(id),
    };
    setPage(nextPage);
    persistPatch(copy, nextPage, id);
  };

  const handleCopyChange = (nextCopy: CopyJson) => {
    setCopy(nextCopy);
    persistPatch(nextCopy, page, templateId);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {isLive && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[rgba(16,185,129,0.3)] bg-[rgba(16,185,129,0.1)] px-4 py-3">
          <div>
            <p className="text-sm font-semibold text-[var(--fv-success)]">Published</p>
            <p className="text-xs text-[var(--fv-text-soft)]">
              Your landing page is live and collecting traffic.
            </p>
          </div>
          <Link
            href={`/e/${publishedSlug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="fv-btn-primary px-3 py-1.5 text-sm no-underline"
          >
            View live page
            <ExternalLink className="h-4 w-4" />
          </Link>
        </div>
      )}

      <div className="mb-4 flex gap-2 lg:hidden">
        <button
          type="button"
          onClick={() => setMobilePanel("edit")}
          className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium ${
            mobilePanel === "edit"
              ? "bg-[var(--fv-accent)] text-[#080c14]"
              : "bg-white/5 text-[var(--fv-text-muted)]"
          }`}
        >
          <Pencil className="h-4 w-4" />
          Edit
        </button>
        <button
          type="button"
          onClick={() => setMobilePanel("preview")}
          className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium ${
            mobilePanel === "preview"
              ? "bg-[var(--fv-accent)] text-[#080c14]"
              : "bg-white/5 text-[var(--fv-text-muted)]"
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>

      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(280px,360px)_1fr]">
        <div
          className={`lp-editor-panel space-y-6 overflow-y-auto rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-4 sm:p-5 ${
            mobilePanel === "edit" ? "block" : "hidden lg:block"
          }`}
        >
          <ThemePicker
            selected={templateId}
            onSelect={handleTemplateSelect}
          />

          <CopyFieldsEditor copy={copy} onChange={handleCopyChange} />

          <div className="border-t border-[var(--fv-border)] pt-6">
            <PublishPanel
              projectId={experimentId}
              projectName={projectName}
              outputVersion={landingPage.output_version ?? 1}
              disabled={isLive}
              onPublished={(res) => {
                setPublishedSlug(res.slug);
                onPublished?.();
              }}
            />
          </div>
        </div>

        <div
          className={`min-h-[480px] overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-bg)] lg:min-h-[calc(100vh-12rem)] ${
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
