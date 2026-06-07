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
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-green-200 bg-green-50 px-4 py-3">
          <div>
            <p className="text-sm font-semibold text-green-900">Published</p>
            <p className="text-xs text-green-700">
              Your landing page is live and collecting traffic.
            </p>
          </div>
          <Link
            href={`/e/${publishedSlug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-green-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-900"
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
              ? "bg-gray-900 text-white"
              : "bg-gray-100 text-gray-600"
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
              ? "bg-gray-900 text-white"
              : "bg-gray-100 text-gray-600"
          }`}
        >
          <Eye className="h-4 w-4" />
          Preview
        </button>
      </div>

      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(280px,360px)_1fr]">
        <div
          className={`lp-editor-panel space-y-6 overflow-y-auto rounded-xl border border-gray-800 bg-gray-950 p-4 sm:p-5 ${
            mobilePanel === "edit" ? "block" : "hidden lg:block"
          }`}
        >
          <ThemePicker
            selected={templateId}
            onSelect={handleTemplateSelect}
          />

          <CopyFieldsEditor copy={copy} onChange={handleCopyChange} />

          <div className="border-t border-white/10 pt-6">
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
          className={`min-h-[480px] overflow-hidden rounded-xl border border-gray-200 bg-gray-100 lg:min-h-[calc(100vh-12rem)] ${
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
