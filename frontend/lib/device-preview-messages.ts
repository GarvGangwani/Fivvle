import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import type { CtaConfig } from "@/lib/cta-config";

export const DEVICE_PREVIEW_MESSAGE = {
  UPDATE: "fivvle:device-preview-update",
  READY: "fivvle:device-preview-ready",
  LOADED: "fivvle:device-preview-loaded",
} as const;

export interface DevicePreviewPayload {
  copy: CopyJson;
  page: PageJson;
  projectName: string;
  templateId: TemplateId;
  forEditor?: boolean;
  isPublished?: boolean;
  publicationSlug?: string;
  ctaConfig?: CtaConfig;
}

export function isDevicePreviewPayload(value: unknown): value is DevicePreviewPayload {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.projectName === "string" &&
    typeof v.templateId === "string" &&
    v.copy !== null &&
    typeof v.copy === "object" &&
    v.page !== null &&
    typeof v.page === "object"
  );
}
