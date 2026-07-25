/**
 * Keep page_json.sections aligned with copy_json for PATCH payloads.
 * Copy-tab edits only — never touch branding / surface / color_palette.
 */

import type { CopyJson, PageJson } from "@/lib/types";
import { syncPageJsonSections } from "@/lib/landing-page-data";

export type SyncedLandingCopyPatch = {
  copy_json: CopyJson;
  page_json: PageJson;
};

/** Build a single-request PATCH body: full copy blob + sections-synced page_json. */
export function buildSyncedCopyPatch(
  copy: CopyJson,
  page: PageJson,
  templateId?: string,
): SyncedLandingCopyPatch {
  const basePage =
    templateId != null ? { ...page, template_id: templateId } : page;
  return {
    copy_json: copy,
    page_json: syncPageJsonSections(basePage, copy),
  };
}
