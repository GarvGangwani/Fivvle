"use client";

import type { CSSProperties } from "react";
import type { CopyJson, PageJson } from "@/lib/types";
import {
  defaultColorModeForTemplate,
  resolveTemplateId,
  type TemplateId,
} from "@/lib/templates";
import {
  paletteToCssVars,
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

interface TemplateRendererProps {
  copy: CopyJson;
  page: PageJson;
  projectName: string;
  templateId?: TemplateId;
  isPublished?: boolean;
  ctaConfig?: CtaConfig;
  publicationSlug?: string;
}

export function TemplateRenderer({
  copy,
  page,
  projectName,
  templateId,
  isPublished,
  ctaConfig,
  publicationSlug,
}: TemplateRendererProps) {
  const safeCopy = normalizeCopyJson(copy);
  const branding = resolveBranding(page, projectName);
  const tid = templateId ?? resolveTemplateId(page.template_id);
  const colorMode =
    (page.color_mode as ColorMode | undefined) ??
    defaultColorModeForTemplate(tid);
  const palette = resolveColorPalette(page, tid);
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
  };

  if (tid === "bold-v1") {
    return (
      <BoldV1Template
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />
    );
  }

  if (tid === "minimal-v3") {
    return (
      <MinimalV3Template
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />
    );
  }

  if (tid === "editorial-saas") {
    return (
      <EditorialSaasTemplate
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />
    );
  }

  if (tid === "aether") {
    return (
      <AetherTemplate
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />
    );
  }

  if (tid === "abstract") {
    return (
      <AbstractTemplate
        copy={safeCopy}
        projectName={projectName}
        colorMode={colorMode}
        cssVarStyle={cssVarStyle}
        {...shared}
      />
    );
  }

  return (
    <DarkPremiumTemplate
      copy={safeCopy}
      projectName={projectName}
      colorMode={colorMode}
      cssVarStyle={cssVarStyle}
      {...shared}
    />
  );
}
