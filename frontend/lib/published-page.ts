import type { CopyJson, PageJson } from "./types";
import type { CtaMode } from "./cta-config";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export interface PublishedPagePayload {
  slug: string;
  project_name: string;
  page_goal: string;
  template_id: string;
  copy_json: CopyJson;
  page_json: PageJson;
  cta_mode: CtaMode;
  cta_url: string | null;
  output_version: number;
  published_at: string;
}

export async function fetchPublishedPage(
  slug: string,
): Promise<PublishedPagePayload | null> {
  const res = await fetch(`${API_BASE}/public/pages/${encodeURIComponent(slug)}`, {
    next: { revalidate: 60 },
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to load published page (${res.status})`);
  }
  return res.json() as Promise<PublishedPagePayload>;
}

export async function submitWaitlistLead(
  slug: string,
  email: string,
): Promise<{ message: string; already_registered?: boolean }> {
  const res = await fetch(
    `${API_BASE}/public/pages/${encodeURIComponent(slug)}/leads`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
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
    .slice(0, 48) || "page";
}
