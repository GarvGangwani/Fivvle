"use client";

/**
 * ORPHANED by feat/floating-nav — replaced by FloatingAppNav.
 * Do not remount. Delete in a cleanup PR.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";

export function AppTopNav() {
  const pathname = usePathname();
  const homeActive = pathname === "/";
  const experimentsActive =
    pathname === "/experiments" ||
    pathname.startsWith("/experiments/") ||
    pathname.startsWith("/experiment/");

  const linkClass = (active: boolean) =>
    `border-b-2 pb-0.5 font-label-md text-label-md uppercase no-underline ${
      active
        ? "border-brand-primary text-brand-primary"
        : "border-transparent text-ink-secondary hover:text-ink-primary"
    }`;

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b-2 border-border-master bg-canvas-bg">
      <div className="relative flex h-full items-center px-gutter md:pl-[calc(7rem+24px)]">
        <Link
          href="/"
          className="font-headline text-headline-md font-black uppercase tracking-tight text-ink-primary no-underline"
        >
          FIVVLE
        </Link>

        <nav
          className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-8 md:flex"
          aria-label="App sections"
        >
          <Link href="/" className={linkClass(homeActive)}>
            HOME
          </Link>
          <Link href="/experiments" className={linkClass(experimentsActive)}>
            EXPERIMENTS
          </Link>
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <Link
            href="/settings"
            className="flex items-center justify-center p-2 text-ink-primary transition-colors hover:bg-surface-muted no-underline"
            aria-label="Open settings"
          >
            <span className="material-symbols-outlined" aria-hidden>
              account_circle
            </span>
          </Link>
        </div>
      </div>
    </header>
  );
}
