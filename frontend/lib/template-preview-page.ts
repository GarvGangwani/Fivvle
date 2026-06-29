import type { CopyJson, PageJson } from "@/lib/types";
import { syncPageJsonSections } from "@/lib/landing-page-data";
import {
  defaultColorModeForTemplate,
  PAGE_TEMPLATES,
  type TemplateId,
} from "@/lib/templates";
import { defaultPaletteForTemplate } from "@/lib/color-palettes";
import { defaultSurfaceForTemplate } from "@/lib/surface";

/** Apply each template's default theme while keeping the founder's copy. */
export function buildPageForTemplatePreview(
  page: PageJson,
  copy: CopyJson,
  templateId: TemplateId,
): PageJson {
  return syncPageJsonSections(
    {
      ...page,
      template_id: templateId,
      template_name: PAGE_TEMPLATES.find((t) => t.id === templateId)?.name,
      color_mode: defaultColorModeForTemplate(templateId),
      color_palette: defaultPaletteForTemplate(templateId),
      surface: defaultSurfaceForTemplate(templateId),
    },
    copy,
  );
}

/** Generic copy for template pickers before a landing page exists. */
export const TEMPLATE_PICKER_DUMMY_COPY: CopyJson = {
  hero: {
    headline: "Validate your idea faster",
    subheadline: "Launch a polished landing page and learn what resonates.",
    cta: "Join waitlist",
  },
  problem: {
    heading: "Founders guess too early",
    body: "Without real signal, teams burn months building the wrong thing.",
  },
  features: [
    {
      title: "Research-backed insights",
      description: "AI summarizes market, competitors, and demand in minutes.",
    },
    {
      title: "Live landing pages",
      description: "Publish a tracked page and measure real interest.",
    },
    {
      title: "Clear next steps",
      description: "Decide whether to iterate, proceed, or pivot with confidence.",
    },
  ],
  cta: {
    heading: "Start validating today",
    subheading: "Get your first page live in under an hour.",
    button: "Get early access",
  },
};

export const TEMPLATE_PICKER_DUMMY_PAGE: PageJson = buildPageForTemplatePreview(
  { template_id: "dark-premium" },
  TEMPLATE_PICKER_DUMMY_COPY,
  "dark-premium",
);
