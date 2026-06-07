"use client";

import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import { TemplateRenderer } from "@/components/landing-templates/TemplateRenderer";
import { DevicePreview } from "./DevicePreview";
import { PreviewErrorBoundary } from "@/components/landing-templates/PreviewErrorBoundary";

interface LandingPagePreviewProps {
  copy: CopyJson;
  page: PageJson;
  projectName: string;
  templateId: TemplateId;
}

export function LandingPagePreview({
  copy,
  page,
  projectName,
  templateId,
}: LandingPagePreviewProps) {
  return (
    <PreviewErrorBoundary variant="preview">
      <DevicePreview variant="editor">
        <TemplateRenderer
          copy={copy}
          page={page}
          projectName={projectName}
          templateId={templateId}
        />
      </DevicePreview>
    </PreviewErrorBoundary>
  );
}
