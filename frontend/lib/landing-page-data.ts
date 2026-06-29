import type { CopyJson, LandingPage, PageJson } from "./types";
import { normalizeCopyJson } from "./normalize-copy";
import { resolveTemplateId, type TemplateId } from "./templates";

/** Sections stored as `{ items: [...] }` in page_json but arrays in copy_json. */
function unwrapSectionItems(value: unknown): unknown {
  if (value == null) return value;
  if (Array.isArray(value)) return value;
  if (typeof value === "object") {
    const o = value as Record<string, unknown>;
    if (Array.isArray(o.items)) return o.items;
  }
  return value;
}

/** Coerce copy_json shapes that differ from template expectations. */
export function coerceRawCopyJson(copy: CopyJson): CopyJson {
  const next: CopyJson = { ...copy };

  if (copy.features != null) {
    next.features = unwrapSectionItems(copy.features) as CopyJson["features"];
  }
  if (copy.faq != null) {
    next.faq = unwrapSectionItems(copy.faq) as CopyJson["faq"];
  }

  return next;
}

/** Rebuild copy_json from page_json.sections (inverse of theme_to_page_json). */
export function extractCopyFromPageSections(page: PageJson): CopyJson {
  const copy: CopyJson = {};

  for (const section of page.sections ?? []) {
    const { type, content } = section;
    if (content == null) continue;

    if (type === "features" || type === "faq") {
      (copy as Record<string, unknown>)[type] = unwrapSectionItems(content);
      continue;
    }

    if (
      type === "hero" ||
      type === "problem" ||
      type === "proof" ||
      type === "cta" ||
      type === "objections" ||
      type === "comparison" ||
      type === "pricing"
    ) {
      (copy as Record<string, unknown>)[type] = content;
    }
  }

  return copy;
}

function isSectionEmpty(value: unknown): boolean {
  if (value == null) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value !== "object") return false;

  const o = value as Record<string, unknown>;
  if (Array.isArray(o.items)) return o.items.length === 0;

  const strings = Object.values(o).filter((v) => typeof v === "string") as string[];
  if (strings.length > 0) {
    return strings.every((s) => s.trim().length === 0);
  }

  const arrays = Object.values(o).filter(Array.isArray) as unknown[][];
  if (arrays.length > 0) {
    return arrays.every((a) => a.length === 0);
  }

  return Object.keys(o).length === 0;
}

/** Prefer primary copy_json; fill missing sections from page_json.sections. */
export function mergeCopySources(
  primary: CopyJson,
  fromSections: CopyJson,
): CopyJson {
  const merged = coerceRawCopyJson({ ...fromSections, ...primary });
  const keys: (keyof CopyJson)[] = [
    "hero",
    "problem",
    "features",
    "proof",
    "faq",
    "cta",
    "objections",
    "comparison",
  ];

  for (const key of keys) {
    if (isSectionEmpty(merged[key]) && !isSectionEmpty(fromSections[key])) {
      (merged as Record<string, unknown>)[key] = fromSections[key];
    }
  }

  return merged;
}

export function resolvePageJson(landingPage: LandingPage): PageJson {
  const page: PageJson = { ...(landingPage.page_json ?? {}) };
  if (!page.template_id) {
    page.template_id = landingPage.template_id;
  }
  return page;
}

/** Full copy resolution pipeline for template preview. */
export function resolveLandingPageCopy(
  copyJson: CopyJson | null | undefined,
  pageJson: PageJson,
  options?: { forEditor?: boolean },
): CopyJson {
  const primary = copyJson ?? {};
  const fromSections = extractCopyFromPageSections(pageJson);
  const merged = mergeCopySources(primary, fromSections);
  return normalizeCopyJson(merged, options);
}

/** Keep page_json.sections in sync when the founder edits copy. */
export function syncPageJsonSections(
  page: PageJson,
  copy: CopyJson,
): PageJson {
  const existingOrder = page.sections?.map((s) => s.type) ?? [];
  const defaultOrder = [
    "hero",
    "problem",
    "features",
    "objections",
    "proof",
    "faq",
    "cta",
  ];
  const order =
    existingOrder.length > 0
      ? existingOrder
      : defaultOrder.filter(
          (type) => !isSectionEmpty((copy as Record<string, unknown>)[type]),
        );

  const typesToInclude =
    order.length > 0
      ? order
      : defaultOrder.filter(
          (type) => !isSectionEmpty((copy as Record<string, unknown>)[type]),
        );

  const sections: NonNullable<PageJson["sections"]> = [];

  for (const type of typesToInclude) {
    const content = (copy as Record<string, unknown>)[type];
    if (isSectionEmpty(content)) continue;

    if (type === "features" || type === "faq") {
      const items = unwrapSectionItems(content);
      if (Array.isArray(items) && items.length > 0) {
        sections.push({ type, content: { items } });
      }
      continue;
    }

    sections.push({ type, content });
  }

  return { ...page, sections };
}

export interface ResolvedLandingPageEditorData {
  copy: CopyJson;
  page: PageJson;
  templateId: TemplateId;
  projectName: string;
}

export function resolveLandingPageEditorData(
  landingPage: LandingPage,
  experimentName?: string | null,
): ResolvedLandingPageEditorData {
  const page = resolvePageJson(landingPage);
  const copy = resolveLandingPageCopy(landingPage.copy_json, page, {
    forEditor: true,
  });
  const templateId = resolveTemplateId(page.template_id ?? landingPage.template_id);
  const syncedPage = syncPageJsonSections(
    { ...page, template_id: templateId },
    copy,
  );

  const projectName =
    experimentName?.trim() ||
    landingPage.headline?.trim() ||
    copy.hero?.headline?.trim() ||
    "Untitled project";

  return {
    copy,
    page: syncedPage,
    templateId,
    projectName,
  };
}
