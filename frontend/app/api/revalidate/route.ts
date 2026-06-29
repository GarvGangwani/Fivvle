import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

const SLUG_RE = /^[a-z0-9-]{6,40}$/;

interface RevalidateBody {
  slug?: string;
}

/**
 * On-demand ISR invalidation for public landing pages.
 * Called server-to-server from FastAPI after live landing page edits.
 */
export async function POST(request: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "Revalidation is not configured" },
      { status: 503 },
    );
  }

  const provided =
    request.headers.get("x-revalidate-secret") ??
    request.headers.get("X-Revalidate-Secret");
  if (!provided || provided !== secret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: RevalidateBody;
  try {
    body = (await request.json()) as RevalidateBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const slug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  if (!SLUG_RE.test(slug)) {
    return NextResponse.json({ error: "Invalid slug" }, { status: 400 });
  }

  revalidatePath(`/e/${slug}`);

  return NextResponse.json({ revalidated: true, slug });
}
