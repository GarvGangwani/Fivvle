"use client";

import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import type { CtaConfig } from "@/lib/cta-config";
import { TemplateRenderer } from "@/components/landing-templates/TemplateRenderer";
import { DevicePreview } from "./DevicePreview";
import { PreviewErrorBoundary } from "@/components/landing-templates/PreviewErrorBoundary";
import type { PreviewSaveStatus } from "./PreviewSaveStatus";

interface LandingPagePreviewProps {
  copy: CopyJson;
  page: PageJson;
  projectName: string;
  templateId: TemplateId;
  /** On mobile editor, fill container width without device chrome scaling. */
  mobileFluid?: boolean;
  forEditor?: boolean;
  isPublished?: boolean;
  publicationSlug?: string;
  ctaConfig?: CtaConfig;
  experimentId?: string;
  onSectionImageChange?: (slotId: string, url: string | null) => void;
  onCopyChange?: (copy: CopyJson) => void;
  saveStatus?: PreviewSaveStatus;
  saveErrorDetail?: string | null;
}

export function LandingPagePreview({
  copy,
  page,
  projectName,
  templateId,
  mobileFluid = false,
  forEditor = false,
  isPublished = false,
  publicationSlug,
  ctaConfig,
  experimentId,
  onSectionImageChange,
  onCopyChange,
  saveStatus = "idle",
  saveErrorDetail = null,
}: LandingPagePreviewProps) {
  const previewPayload = {
    copy,
    page,
    projectName,
    templateId,
    forEditor,
    isPublished,
    publicationSlug,
    ctaConfig,
  };

  return (
    <PreviewErrorBoundary variant="preview">
      <div className="flex h-full min-h-0 flex-col">
        <DevicePreview
          variant="editor"
          mobileFluid={mobileFluid}
          showInlineEditDisclaimer={Boolean(forEditor && onCopyChange)}
          previewPayload={previewPayload}
          saveStatus={saveStatus}
          saveErrorDetail={saveErrorDetail}
        >
          <TemplateRenderer
            copy={copy}
            page={page}
            projectName={projectName}
            templateId={templateId}
            forEditor={forEditor}
            isPublished={isPublished}
            publicationSlug={publicationSlug}
            ctaConfig={ctaConfig}
            experimentId={experimentId}
            onSectionImageChange={onSectionImageChange}
            onCopyChange={onCopyChange}
          />
        </DevicePreview>
      </div>
    </PreviewErrorBoundary>
  );
}
