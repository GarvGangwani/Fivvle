"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { MarketingNav } from "@/components/marketing/MarketingNav";

export function WaitlistForm() {
  const searchParams = useSearchParams();
  const tier = searchParams.get("tier") ?? "founder";
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("loading");
    setMessage(null);

    try {
      const response = await fetch("/api/waitlist/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, tier }),
      });
      const data = (await response.json()) as { ok?: boolean; stub?: boolean };

      if (!response.ok || !data.ok) {
        throw new Error("subscribe_failed");
      }

      setStatus("done");
      setMessage(
        "You're on the list. We'll email you when Founder tier goes live.",
      );
      setEmail("");
    } catch {
      setStatus("error");
      setMessage("Something went wrong. Try again in a moment.");
    }
  }

  return (
    <div className="min-h-screen bg-canvas-bg text-ink-primary">
      <MarketingNav />
      <main className="mx-auto max-w-xl px-gutter pb-24 pt-28">
        <p className="font-label-md text-label-md uppercase text-brand-primary">
          WAITLIST
        </p>
        <h1 className="mt-3 font-headline text-headline-lg uppercase">
          Subscription tiers launching soon.
        </h1>
        <p className="mt-4 font-body-lg text-body-lg text-ink-secondary">
          Drop your email and we&apos;ll notify you when Founder tier goes live.
          {tier !== "founder" ? (
            <span className="mt-2 block font-mono text-mono-sm uppercase text-ink-tertiary">
              Selected tier: {tier}
            </span>
          ) : null}
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <label className="block">
            <span className="font-label-md text-label-md uppercase text-ink-secondary">
              Email
            </span>
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-md border-2 border-border-master bg-surface-card px-4 py-3 font-body-md text-body-md shadow-brutal-sm focus:border-brand-primary focus:outline-none"
              placeholder="you@company.com"
              autoComplete="email"
            />
          </label>
          <button
            type="submit"
            disabled={status === "loading"}
            className={`${marketingButtonClass} w-full bg-brand-primary px-4 py-3 font-label-md text-label-md uppercase text-ink-inverse disabled:opacity-60`}
          >
            {status === "loading" ? "SUBMITTING…" : "NOTIFY ME"}
          </button>
        </form>

        {message ? (
          <p
            role="status"
            className={`mt-4 font-body-md text-body-md ${status === "error" ? "text-status-critical" : "text-status-success"}`}
          >
            {message}
          </p>
        ) : null}

        <Link
          href="/"
          className="mt-8 inline-block font-body-md text-body-md text-brand-primary no-underline hover:underline"
        >
          ← Back to home
        </Link>
      </main>
    </div>
  );
}
