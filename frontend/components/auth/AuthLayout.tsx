import Link from "next/link";

interface AuthLayoutProps {
  children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="canvas-grid-bg relative flex min-h-screen flex-col overflow-hidden bg-canvas-bg text-ink-primary">
      <div
        className="pointer-events-none absolute -left-16 top-24 hidden h-48 w-48 rotate-12 border-2 border-dashed border-brand-primary opacity-20 lg:block"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -right-12 bottom-32 hidden h-32 w-32 -rotate-6 border-2 border-dashed border-ink-tertiary opacity-20 md:block"
        aria-hidden="true"
      />

      <header className="relative z-10 flex h-16 shrink-0 items-center justify-between border-b-2 border-border-master px-gutter">
        <Link
          href="/"
          className="font-headline text-headline-md font-black uppercase tracking-tight text-ink-primary no-underline"
        >
          FIVVLE
        </Link>
        <nav aria-label="Auth utility links">
          <Link
            href="/docs"
            className="font-label-md text-label-md uppercase text-ink-secondary no-underline hover:text-ink-primary"
          >
            DOCUMENTATION
          </Link>
        </nav>
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-gutter py-12">
        {children}
      </main>

      <div
        className="pointer-events-none fixed bottom-6 left-6 z-10 space-y-1"
        aria-hidden="true"
      >
        <div className="h-1 w-24 bg-ink-primary" />
        <div className="h-1 w-16 bg-brand-primary" />
        <div className="h-1 w-32 bg-ink-tertiary" />
      </div>
      <p className="pointer-events-none fixed bottom-6 right-6 z-10 font-mono text-mono-sm uppercase tracking-wider text-ink-primary">
        ENCRYPTED END-TO-END
      </p>
    </div>
  );
}
