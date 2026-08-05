"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { MarketingFooter } from "./MarketingFooter";
import { MarketingNav } from "./MarketingNav";
import { marketingButtonClass } from "./marketing-styles";

type ComingSoonPageProps = {
  eyebrow: string;
  headline: string;
  body: string;
  ctaLabel: string;
  ctaHref?: string;
  showEmailCapture?: boolean;
  /** Passed to waitlist stub when `showEmailCapture` is true. */
  intent?: string;
};

function resolveIntent(ctaHref: string, intent?: string): string {
  if (intent) return intent;
  try {
    const url = new URL(ctaHref, "http://localhost");
    return url.searchParams.get("intent") ?? "unknown";
  } catch {
    return "unknown";
  }
}

export function ComingSoonPage({
  eyebrow,
  headline,
  body,
  ctaLabel,
  ctaHref = "/waitlist?intent=demo",
  showEmailCapture = false,
  intent,
}: ComingSoonPageProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const waitlistIntent = resolveIntent(ctaHref, intent);

  async function handleEmailSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("loading");

    try {
      const response = await fetch("/api/waitlist/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, intent: waitlistIntent }),
      });
      const data = (await response.json()) as { ok?: boolean };

      if (!response.ok || !data.ok) {
        throw new Error("subscribe_failed");
      }

      setStatus("done");
      setEmail("");
    } catch {
      setStatus("error");
    }
  }

  const isMailto = ctaHref.startsWith("mailto:");

  return (
    <div className="flex min-h-screen flex-col bg-canvas-bg text-ink-primary">
      <MarketingNav />
      <main className="canvas-grid-bg relative flex flex-1 flex-col border-b-2 border-border-master pt-16">
        <div className="flex flex-1 items-center justify-center px-gutter py-24">
          <article className="mx-auto w-full max-w-2xl rounded-md border-2 border-border-master bg-surface-card p-12 shadow-brutal-md">
            <p className="font-label-md text-label-md uppercase text-accent">
              {eyebrow}
            </p>
            <h1 className="mt-4 font-display text-display-lg uppercase leading-none text-ink-primary">
              {headline}
            </h1>
            <p className="mt-6 max-w-lg font-body-lg text-body-lg text-ink-secondary">
              {body}
            </p>

            {showEmailCapture ? (
              <form onSubmit={handleEmailSubmit} className="mt-10 space-y-4">
                <label className="block">
                  <span className="sr-only">Email address</span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    disabled={status === "done"}
                    placeholder="you@company.com"
                    autoComplete="email"
                    className="w-full rounded-md border-2 border-border-master bg-canvas-bg px-4 py-3 font-body-md text-body-md shadow-brutal-sm focus:border-accent focus:outline-none disabled:opacity-60"
                  />
                </label>
                <button
                  type="submit"
                  disabled={status === "loading" || status === "done"}
                  className={`${marketingButtonClass} bg-accent px-8 py-4 font-bold uppercase tracking-wider text-ink-inverse disabled:opacity-60`}
                >
                  {status === "loading" ? "SUBMITTING…" : ctaLabel}
                </button>
                {status === "done" ? (
                  <p
                    role="status"
                    className="font-body-md text-body-md text-status-success"
                  >
                    You&apos;re on the list — we&apos;ll email you when it
                    ships.
                  </p>
                ) : null}
                {status === "error" ? (
                  <p
                    role="alert"
                    className="font-body-md text-body-md text-status-critical"
                  >
                    Something went wrong. Try again in a moment.
                  </p>
                ) : null}
              </form>
            ) : isMailto ? (
              <a
                href={ctaHref}
                className={`${marketingButtonClass} mt-10 inline-flex bg-accent px-8 py-4 font-bold uppercase tracking-wider text-ink-inverse no-underline`}
              >
                {ctaLabel}
              </a>
            ) : (
              <Link
                href={ctaHref}
                className={`${marketingButtonClass} mt-10 inline-flex bg-accent px-8 py-4 font-bold uppercase tracking-wider text-ink-inverse no-underline`}
              >
                {ctaLabel}
              </Link>
            )}
          </article>
        </div>
      </main>
      <MarketingFooter />
    </div>
  );
}
