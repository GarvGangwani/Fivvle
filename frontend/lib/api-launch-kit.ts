/**
 * Typed wrappers for the LaunchKit endpoints (Launch phase, PR 1 backend).
 *
 * Mirrors the editable-doc conventions in `lib/api.ts`
 * (`getEditedDoc` / `patchEditedDoc` / `EditedDocVersionConflict`): the artifact
 * is enveloped with an optimistic-concurrency `version`, and a CAS conflict on
 * PATCH surfaces as a dedicated error class.
 *
 * Types here intentionally live beside the wrappers (same pattern as
 * `EditedDocResponse` in `api.ts`) rather than in `lib/types.ts`.
 */

import { ApiError, apiFetch } from "./api";

export type LaunchChannel =
  | "reddit"
  | "twitter"
  | "linkedin"
  | "hackernews"
  | "product_hunt"
  | "dm_chain"
  | "newsletter"
  | "community_slack"
  | "other";

export type ShareSurface =
  | "tweet"
  | "reddit_post"
  | "dm_opener"
  | "linkedin_post"
  | "hackernews_show";

export interface ShareCopyVariant {
  surface: ShareSurface;
  text: string;
  regenerated_count: number;
}

export interface ReadinessItem {
  id: string;
  label: string;
  /** ISO timestamp when ticked, or null while unchecked. */
  checked_at: string | null;
}

/** The schema-pure LaunchKit artifact (GET/PATCH payload, minus the envelope). */
export interface LaunchKit {
  schema_version: 1;
  landing_page_id: string;
  first_channel: LaunchChannel;
  first_channel_rationale: string;
  first_cohort_hint: string;
  share_copy_variants: ShareCopyVariant[];
  readiness_checklist: ReadinessItem[];
  generated_at: string;
  founder_edited: boolean;
  raw_report: Record<string, unknown>;
}

/** GET/PATCH /launch-kit response: artifact + optimistic-concurrency version. */
export interface LaunchKitEnvelope {
  launch_kit: LaunchKit;
  version: number;
}

/** 202 response for POST /generate-launch-kit. */
export interface LaunchKitGenerateResponse {
  experiment_id: string;
  generation_started: boolean;
}

export interface ShareCopyVariantPatch {
  index: number;
  text: string;
}

export interface ReadinessItemPatch {
  id: string;
  checked_at: string | null;
}

/** Founder-editable fields; only provided keys are applied server-side. */
export interface LaunchKitPatch {
  first_channel?: LaunchChannel;
  first_channel_rationale?: string;
  first_cohort_hint?: string;
  share_copy_variants?: ShareCopyVariantPatch[];
  readiness_checklist?: ReadinessItemPatch[];
}

/** Raised when a PATCH to /launch-kit loses the CAS race (409). */
export class LaunchKitVersionConflict extends ApiError {
  public current_version: number;

  constructor(current_version: number, body: unknown, requestId: string | null) {
    super(409, body, requestId);
    this.name = "LaunchKitVersionConflict";
    this.current_version = current_version;
  }
}

/** POST /experiments/{id}/generate-launch-kit — dispatch async (re)generation. */
export async function generateLaunchKit(
  experimentId: string,
): Promise<LaunchKitGenerateResponse> {
  return apiFetch<LaunchKitGenerateResponse>(
    `/experiments/${experimentId}/generate-launch-kit`,
    { method: "POST", body: {} },
  );
}

/** GET /experiments/{id}/launch-kit — 404 (ApiError) when not yet generated. */
export async function getLaunchKit(
  experimentId: string,
): Promise<LaunchKitEnvelope> {
  return apiFetch<LaunchKitEnvelope>(
    `/experiments/${experimentId}/launch-kit`,
  );
}

/** PATCH /experiments/{id}/launch-kit — CAS edit; throws LaunchKitVersionConflict on 409. */
export async function patchLaunchKit(
  experimentId: string,
  body: { version: number; patch: LaunchKitPatch },
): Promise<LaunchKitEnvelope> {
  try {
    return await apiFetch<LaunchKitEnvelope>(
      `/experiments/${experimentId}/launch-kit`,
      { method: "PATCH", body },
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) {
      const detail = (err.body as { detail?: { current_version?: number } })
        ?.detail;
      const current =
        typeof detail?.current_version === "number"
          ? detail.current_version
          : 0;
      throw new LaunchKitVersionConflict(current, err.body, err.requestId);
    }
    throw err;
  }
}
