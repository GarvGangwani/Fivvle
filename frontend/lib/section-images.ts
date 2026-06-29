/** Stable slot IDs for template image placeholders (stored in page_json.section_images). */

export const ABSTRACT_IMAGE_SLOTS = {
  showcase: "abstract:showcase",
  cta: "abstract:cta",
} as const;

export function editorialFeatureImageSlot(index: number): string {
  return `editorial-saas:feature-${index}`;
}

export const EDITORIAL_WORKFLOW_IMAGE_SLOT = "editorial-saas:workflow";

export function getSectionImageUrl(
  sectionImages: Record<string, string> | undefined,
  slotId: string,
): string | undefined {
  const url = sectionImages?.[slotId]?.trim();
  return url || undefined;
}
