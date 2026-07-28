import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  LANDING_SLUG_PATTERN,
  resolveProjectSlugFromHost,
} from "@/lib/landing-host";

/** App routes that must not be served on project subdomains. */
const APP_ROUTE_PREFIXES = [
  "/dashboard",
  "/experiment",
  "/login",
  "/signup",
  "/admin",
  "/archived",
  "/new",
  "/api",
  "/preview",
] as const;

function isAppRoute(pathname: string): boolean {
  return APP_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function internalLandingPath(slug: string): string {
  return `/e/${slug}`;
}

export function middleware(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  const slug = resolveProjectSlugFromHost(host);

  if (!slug) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Already rewritten to the internal landing route — avoid loops.
  const internalPrefix = internalLandingPath(slug);
  if (pathname === internalPrefix || pathname.startsWith(`${internalPrefix}/`)) {
    const pathSlugMatch = pathname.match(/^\/e\/([a-z0-9-]{6,40})(?:\/|$)/);
    if (pathSlugMatch && pathSlugMatch[1] !== slug) {
      return new NextResponse(null, { status: 404 });
    }
    return NextResponse.next();
  }

  if (isAppRoute(pathname)) {
    return new NextResponse(null, { status: 404 });
  }

  // Only the landing page root is public on project subdomains.
  if (pathname !== "/" && pathname !== "") {
    return new NextResponse(null, { status: 404 });
  }

  const rewriteUrl = request.nextUrl.clone();
  rewriteUrl.pathname = internalPrefix;
  return NextResponse.rewrite(rewriteUrl);
}

export const config = {
  matcher: [
    /*
     * Run on all paths except Next static assets and common static files.
     */
    "/((?!_next/static|_next/image|favicon.ico|icon.png|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};

// Re-export for tests / tooling that import slug validation from middleware.
export { LANDING_SLUG_PATTERN };
