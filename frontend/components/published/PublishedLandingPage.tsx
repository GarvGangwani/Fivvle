"use client";

import type { PublishedPagePayload } from "@/lib/published-page";
import { resolveLandingPageCopy } from "@/lib/landing-page-data";
import { resolveTemplateId } from "@/lib/templates";
import type { CtaConfig } from "@/lib/cta-config";
import { TemplateRenderer } from "@/components/landing-templates/TemplateRenderer";
import { PreviewErrorBoundary } from "@/components/landing-templates/PreviewErrorBoundary";

interface PublishedLandingPageProps {
  data: PublishedPagePayload;
}

export function PublishedLandingPage({ data }: PublishedLandingPageProps) {
  const page = {
    ...(data.page_json ?? {}),
    template_id: data.template_id ?? data.page_json?.template_id,
  };
  const copy = resolveLandingPageCopy(data.copy_json, page);
  const templateId = resolveTemplateId(page.template_id);
  const ctaConfig: CtaConfig = {
    mode: data.cta_mode,
    url: data.cta_url,
  };

  return (
    <PreviewErrorBoundary variant="published">
      <div data-theme="light">
        <TemplateRenderer
          copy={copy}
          page={page}
          projectName={data.project_name}
          templateId={templateId}
          isPublished
          ctaConfig={ctaConfig}
          publicationSlug={data.slug}
        />
      </div>
    </PreviewErrorBoundary>
  );
}
