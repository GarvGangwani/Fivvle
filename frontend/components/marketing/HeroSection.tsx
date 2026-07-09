"use client";

import Link from "next/link";
import { LiveActivityBadge } from "./LiveActivityBadge";
import { marketingButtonClass } from "./marketing-styles";

interface HeroSectionProps {
  onDemoClick: () => void;
}

export function HeroSection({ onDemoClick }: HeroSectionProps) {
  return (
    <section className="relative overflow-hidden border-b-2 border-border-master pt-16">
      <div className="canvas-grid-bg relative min-h-[calc(100vh-4rem)] px-gutter pb-24 pt-20 md:pb-32 md:pt-28">
        <div className="relative z-10 mx-auto max-w-5xl">
          <p className="inline-block bg-ink-primary px-3 py-1.5 font-mono text-mono-md uppercase tracking-wider text-ink-inverse">
            PHASE 01 — VALIDATE BEFORE YOU BUILD
          </p>

          <h1 className="mt-8 max-w-4xl font-display text-display-lg uppercase leading-[1.05] tracking-tight text-ink-primary">
            Turn &quot;I have an idea&quot; into a defensible{" "}
            <span className="text-brand-primary-deep underline decoration-brand-primary decoration-[6px] underline-offset-8">
              proceed / kill
            </span>{" "}
            decision.
          </h1>

          <p className="mt-6 max-w-2xl font-headline text-headline-md font-normal text-ink-secondary">
            Fivvle researches your startup idea against real market signal, tests
            it against real people via a hosted landing page, and hands you a
            verdict backed by cited evidence — in days, not months.
          </p>

          <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:items-center">
            <Link
              href="/signup"
              className={`${marketingButtonClass} bg-brand-primary px-8 py-4 text-base font-bold uppercase tracking-wider text-ink-inverse shadow-brutal-md hover:shadow-brutal-lg no-underline`}
            >
              START A VALIDATION →
            </Link>
            {/* TODO: replace with real demo route */}
            <button
              type="button"
              onClick={onDemoClick}
              className={`${marketingButtonClass} bg-surface-card px-8 py-4 text-base font-bold uppercase tracking-wider text-ink-primary shadow-brutal-md hover:shadow-brutal-lg`}
            >
              VIEW DEMO
            </button>
          </div>
        </div>

        <LiveActivityBadge />
      </div>
    </section>
  );
}
