import type { CopyJson, PageJson } from "./types";
import type { CtaMode } from "./cta-config";

import {
  buildPublicLandingPageUrl,
  formatPublicLandingHost,
  LANDING_PAGE_SOURCE_PARAM,
} from "@/lib/landing-host";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export { LANDING_PAGE_SOURCE_PARAM };

export function buildTrackedLandingPageUrl(
  slug: string,
  sourceTag: string,
  _origin?: string,
): string {
  return buildPublicLandingPageUrl(slug, sourceTag);
}

export { buildPublicLandingPageUrl, formatPublicLandingHost };

export interface PublishedPagePayload {
  slug: string;
  project_name: string;
  copy_json: CopyJson;
  page_json: PageJson;
  cta_mode: CtaMode;
  cta_url: string | null;
  experiment_slug: string | null;
  published_at: string;
  page_goal?: string;
  template_id?: string;
  output_version?: number;
}

export async function fetchPublishedPage(
  slug: string,
): Promise<PublishedPagePayload | null> {
  const isDev = process.env.NODE_ENV === "development";
  const res = await fetch(`${API_BASE}/e/${encodeURIComponent(slug)}`, {
    next: isDev ? { revalidate: 0 } : { revalidate: 60 },
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to load published page (${res.status})`);
  }
  const raw = (await res.json()) as PublishedPagePayload;
  return {
    ...raw,
    copy_json: raw.copy_json ?? {},
    page_json: raw.page_json ?? {},
  };
}

export async function submitWaitlistLead(
  slug: string,
  email: string,
  sourceTag?: string | null,
): Promise<{ message: string; already_registered?: boolean }> {
  const res = await fetch(
    `${API_BASE}/e/${encodeURIComponent(slug)}/waitlist`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, ...(sourceTag ? { source_tag: sourceTag } : {}) }),
    },
  );
  if (!res.ok) {
    const body = await res.text();
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      detail = parsed.detail ?? body;
    } catch {
      /* raw */
    }
    throw new Error(detail || "Signup failed");
  }
  return res.json() as Promise<{ message: string }>;
}

export function slugifyProjectName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 28) || "page";
}
