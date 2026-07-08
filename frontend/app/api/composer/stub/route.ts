import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const message = typeof body?.message === "string" ? body.message : "";
  return NextResponse.json({
    ok: true,
    stub: true,
    echo: message,
    note: "AI Composer real implementation pending — see redesign tracked-work item.",
  });
}
