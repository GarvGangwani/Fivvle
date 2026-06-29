/**
 * Public landing page host resolution — subdomain routing for published pages.
 *
 * Dev:  http://{slug}.localhost:3000
 * Prod: https://{slug}.fivvle.io
 *
 * Internal Next.js route remains /e/[slug]; middleware rewrites subdomain requests.
 */

/** Query param used on public landing page URLs for source-tag analytics. */
export const LANDING_PAGE_SOURCE_PARAM = "utm_source";

/** Matches backend validate_landing_slug / AGENTS.md public slug rules. */
export const LANDING_SLUG_PATTERN = /^[a-z0-9-]{6,40}$/;

/** Subdomains reserved for the app shell — never treated as project slugs. */
export const RESERVED_LANDING_SUBDOMAINS = new Set([
  "www",
  "app",
  "api",
  "admin",
  "staging",
  "mail",
]);

const DEFAULT_ROOT_DOMAIN = "fivvle.io";
const DEFAULT_DEV_PORT = 3000;

export function getLandingRootDomain(): string {
  return (
    process.env.NEXT_PUBLIC_LANDING_ROOT_DOMAIN?.trim().toLowerCase() ||
    DEFAULT_ROOT_DOMAIN
  );
}

export function getLandingDevPort(): number {
  const raw = process.env.NEXT_PUBLIC_LANDING_DEV_PORT?.trim();
  if (!raw) return DEFAULT_DEV_PORT;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_DEV_PORT;
}

function isValidLandingSlug(value: string): boolean {
  return LANDING_SLUG_PATTERN.test(value);
}

/**
 * Extract a project landing slug from the request Host header.
 * Returns null for the app shell (localhost, app.fivvle.io, www, etc.).
 */
export function resolveProjectSlugFromHost(host: string): string | null {
  const hostname = host.split(":")[0]?.trim().toLowerCase();
  if (!hostname) return null;

  const rootDomain = getLandingRootDomain();

  let subdomain: string | null = null;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return null;
  }

  if (hostname.endsWith(".localhost")) {
    subdomain = hostname.slice(0, -".localhost".length);
  } else if (hostname === rootDomain || hostname.endsWith(`.${rootDomain}`)) {
    if (hostname === rootDomain) {
      return null;
    }
    subdomain = hostname.slice(0, -(rootDomain.length + 1));
  } else {
    return null;
  }

  if (!subdomain || subdomain.includes(".")) {
    return null;
  }

  if (RESERVED_LANDING_SUBDOMAINS.has(subdomain)) {
    return null;
  }

  return isValidLandingSlug(subdomain) ? subdomain : null;
}

/** Suffix after the slug in the URL editor, e.g. .fivvle.io or .localhost:3000 */
export function getLandingSubdomainSuffix(): string {
  const isDev = process.env.NODE_ENV === "development";
  const root = getLandingRootDomain();
  const port = getLandingDevPort();
  return isDev ? `.localhost:${port}` : `.${root}`;
}

/** Hostname shown in UI (no protocol), e.g. mewwly.fivvle.io */
export function formatPublicLandingHost(slug: string): string {
  const isDev = process.env.NODE_ENV === "development";
  const root = getLandingRootDomain();
  const port = getLandingDevPort();
  return isDev ? `${slug}.localhost:${port}` : `${slug}.${root}`;
}

/** Origin for a published landing page, e.g. http://mewwly.localhost:3000 */
export function buildPublicLandingPageOrigin(slug: string): string {
  const isDev = process.env.NODE_ENV === "development";
  const host = formatPublicLandingHost(slug);
  return `${isDev ? "http" : "https"}://${host}`;
}

/** Full public URL for sharing (optional utm_source). */
export function buildPublicLandingPageUrl(
  slug: string,
  sourceTag?: string,
): string {
  const url = new URL(`${buildPublicLandingPageOrigin(slug)}/`);
  if (sourceTag) {
    url.searchParams.set(LANDING_PAGE_SOURCE_PARAM, sourceTag);
  }
  return url.toString();
}

/** True when the host is a project landing subdomain. */
export function isProjectLandingHost(host: string): boolean {
  return resolveProjectSlugFromHost(host) !== null;
}
