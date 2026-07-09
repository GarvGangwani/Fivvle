import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const email = typeof body?.email === "string" ? body.email.trim() : "";
  const intent = typeof body?.intent === "string" ? body.intent : "unknown";
  const tier = typeof body?.tier === "string" ? body.tier : undefined;

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json(
      { ok: false, error: "invalid_email" },
      { status: 400 },
    );
  }

  return NextResponse.json({
    ok: true,
    stub: true,
    email,
    intent,
    ...(tier ? { tier } : {}),
    note: "Waitlist subscription stub — real backend pending tracked-work item #3.",
  });
}
