"use client";

import Link from "next/link";

export function MarketingNav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b-2 border-border-master bg-canvas-bg">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-gutter">
        <Link
          href="/"
          className="font-headline text-headline-md font-black uppercase tracking-tight text-ink-primary no-underline"
        >
          FIVVLE
        </Link>

        <nav
          className="hidden items-center gap-8 md:flex"
          aria-label="Marketing sections"
        >
          <a
            href="#five-acts"
            className="font-label-md text-label-md uppercase text-ink-secondary no-underline hover:text-ink-primary"
          >
            HOW IT WORKS
          </a>
          <a
            href="#pricing"
            className="font-label-md text-label-md uppercase text-ink-secondary no-underline hover:text-ink-primary"
          >
            PRICING
          </a>
        </nav>

        <div className="flex items-center gap-1">
          <Link
            href="/login?intent=start"
            className="flex items-center justify-center p-2 text-ink-primary transition-colors hover:bg-surface-muted no-underline"
            aria-label="Start validation"
          >
            <span className="material-symbols-outlined" aria-hidden="true">
              bolt
            </span>
          </Link>
          <Link
            href="/login"
            className="flex items-center justify-center p-2 text-ink-primary transition-colors hover:bg-surface-muted no-underline"
            aria-label="Log in"
          >
            <span className="material-symbols-outlined" aria-hidden="true">
              account_circle
            </span>
          </Link>
        </div>
      </div>
    </header>
  );
}
