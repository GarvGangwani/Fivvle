"use client";

import type { CSSProperties, ReactNode } from "react";
import type { CopyJson, PageJson } from "@/lib/types";
import { resolveTemplateId, type TemplateId } from "@/lib/templates";
import {
  paletteToCssVars,
  inferColorModeFromPalette,
  resolveColorPalette,
  type ColorMode,
} from "@/lib/color-palettes";
import type { CtaConfig } from "@/lib/cta-config";
import { normalizeCopyJson } from "@/lib/normalize-copy";
import { resolveBranding } from "@/lib/branding";
import { BoldV1Template } from "./BoldV1Template";
import { DarkPremiumTemplate } from "./DarkPremiumTemplate";
import { MinimalV3Template } from "./MinimalV3Template";
import { EditorialSaasTemplate } from "./EditorialSaasTemplate";
import { AetherTemplate } from "./AetherTemplate";
import { AbstractTemplate } from "./AbstractTemplate";
import { SurfaceShell } from "./SurfaceShell";
import { CopyEditProvider } from "./CopyEditContext";

interface TemplateRendererProps {
  copy: CopyJson;
  page: PageJson;
  projectName: string;
  templateId?: TemplateId;
  isPublished?: boolean;
  ctaConfig?: CtaConfig;
  publicationSlug?: string;
  /** When true, show full copy in editor preview without layout truncation. */
  forEditor?: boolean;
  experimentId?: string;
  onSectionImageChange?: (slotId: string, url: string | null) => void;
  onCopyChange?: (copy: CopyJson) => void;
}

export function TemplateRenderer({
  copy,
  page,
  projectName,
  templateId,
  isPublished,
  ctaConfig,
  publicationSlug,
  forEditor = false,
  experimentId,
  onSectionImageChange,
  onCopyChange,
}: TemplateRendererProps) {
  const safeCopy = normalizeCopyJson(copy, { forEditor });
  const branding = resolveBranding(page, projectName);
  const tid = templateId ?? resolveTemplateId(page.template_id);
  const palette = resolveColorPalette(page, tid);
  const colorMode = inferColorModeFromPalette(palette);
  const cssVarStyle = paletteToCssVars(tid, palette, colorMode) as CSSProperties;
  const scrollTarget =
    tid === "minimal-v3"
      ? "#try"
      : tid === "editorial-saas"
        ? "#join"
        : tid === "abstract"
          ? "#cta-section"
          : "#cta";
  const shared = {
    isPublished,
    ctaConfig,
    publicationSlug,
    scrollTarget,
    branding,
    forEditor,
    sectionImages: page.section_images,
    experimentId,
    onSectionImageChange,
  };

  const withSurface = (node: ReactNode) => (
    <CopyEditProvider
      editable={forEditor && Boolean(onCopyChange)}
      onCopyChange={onCopyChange}
    >
      <SurfaceShell
        page={page}
        accentColor={palette.accent}
        colorMode={colorMode}
      >
        {node}
      </SurfaceShell>
    </CopyEditProvider>
  );

  if (tid === "bold-v1") {
    return withSurface(
      <BoldV1Template
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />,
    );
  }

  if (tid === "minimal-v3") {
    return withSurface(
      <MinimalV3Template
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />,
    );
  }

  if (tid === "editorial-saas") {
    return withSurface(
      <EditorialSaasTemplate
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />,
    );
  }

  if (tid === "aether") {
    return withSurface(
      <AetherTemplate
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />,
    );
  }

  if (tid === "abstract") {
    return withSurface(
      <AbstractTemplate
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />,
    );
  }

  return withSurface(
    <DarkPremiumTemplate
      copy={safeCopy}
      projectName={projectName}
      colorMode={colorMode}
      cssVarStyle={cssVarStyle}
      {...shared}
    />,
  );
}
