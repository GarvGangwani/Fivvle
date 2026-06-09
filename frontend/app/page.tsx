import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-4 py-16">
      <div className="flex flex-col items-center text-center">
        <div
          className="fv-f-logo mb-6"
          style={{ width: 48, height: 48, fontSize: 24 }}
          aria-hidden
        >
          F
        </div>
        <h1 className="text-5xl font-bold tracking-tight text-[var(--fv-text)]">
          Fivvle
        </h1>
        <p className="mt-3 text-xl text-[var(--fv-text-muted)]">
          Validate your startup idea with real signal.
        </p>
        <p className="mt-3 max-w-md text-sm leading-relaxed text-[var(--fv-text-soft)]">
          Research demand, publish a landing page, and measure real interest —
          before you invest months building.
        </p>
      </div>

      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <Link
          href="/signup"
          className="fv-btn-primary w-full justify-center px-8 py-3 text-sm no-underline sm:w-auto"
        >
          Get started
        </Link>
        <Link
          href="/login"
          className="fv-btn-ghost w-full px-8 py-3 text-center text-sm font-semibold no-underline sm:w-auto"
        >
          Log in
        </Link>
      </div>
    </main>
  );
}
