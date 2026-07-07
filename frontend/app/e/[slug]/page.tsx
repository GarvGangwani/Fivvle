import type { Metadata } from "next";
import Script from "next/script";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { PublishedLandingPage } from "@/components/published/PublishedLandingPage";
import { fetchPublishedPage } from "@/lib/published-page";

/** ISR fallback window (seconds). Must be a static literal — Next.js rejects conditionals here. */
export const revalidate = 60;

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface PageProps {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ utm_source?: string }>;
}

/**
 * Fires once on the client after hydration. Sends only slug, source_tag,
 * referrer, and user_agent — no cookies, auth tokens, or other PII (AGENTS.md).
 */
function PageViewBeacon({
  slug,
  sourceTag,
}: {
  slug: string;
  sourceTag: string | undefined;
}) {
  const beaconScript = `
(function () {
  var slug = ${JSON.stringify(slug)};
  var sourceTag = ${JSON.stringify(sourceTag ?? null)};
  var payload = JSON.stringify({
    slug: slug,
    source_tag: sourceTag,
    referrer: typeof document !== "undefined" ? document.referrer || null : null,
    user_agent: typeof navigator !== "undefined" ? navigator.userAgent || null : null
  });
  var url = ${JSON.stringify(`${API_BASE}/analytics/page-view`)};
  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    navigator.sendBeacon(url, new Blob([payload], { type: "application/json" }));
    return;
  }
  if (typeof fetch !== "undefined") {
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
      credentials: "omit"
    });
  }
})();
`;

  return (
    <Script id={`page-view-beacon-${slug}`} strategy="afterInteractive">
      {beaconScript}
    </Script>
  );
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const data = await fetchPublishedPage(slug);
  if (!data) return { title: "Page not found" };

  const hero = data.copy_json.hero;
  return {
    title: data.project_name,
    description:
      hero?.subheadline ?? `Landing page for ${data.project_name}`,
    openGraph: {
      title: hero?.headline ?? data.project_name,
      description: hero?.subheadline,
    },
  };
}

export default async function PublicLandingPageRoute({
  params,
  searchParams,
}: PageProps) {
  const { slug } = await params;
  const { utm_source: sourceTag } = await searchParams;
  const data = await fetchPublishedPage(slug);
  if (!data) notFound();

  return (
    <div data-fivvle-public-landing className="min-h-screen">
      <PageViewBeacon slug={slug} sourceTag={sourceTag} />
      <Suspense fallback={null}>
        <PublishedLandingPage data={data} />
      </Suspense>
    </div>
  );
}
