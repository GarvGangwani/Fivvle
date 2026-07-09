import Link from "next/link";

interface MarketingFooterProps {
  onDemoClick?: () => void;
}

export function MarketingFooter({ onDemoClick }: MarketingFooterProps) {
  return (
    <footer className="bg-ink-primary px-gutter py-16 text-ink-inverse">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-3">
          <div>
            <p className="font-display text-headline-lg font-black uppercase tracking-tight">
              FIVVLE
            </p>
            <p className="mt-3 max-w-xs font-body-md text-body-md text-ink-inverse/80">
              Evidence-backed validation for founders who ship.
            </p>
          </div>

          <div>
            <p className="font-label-md text-label-md uppercase text-ink-inverse/60">
              PRODUCT
            </p>
            <ul className="mt-4 space-y-2 font-body-md text-body-md">
              <li>
                <a
                  href="#five-acts"
                  className="text-ink-inverse no-underline hover:underline"
                >
                  How it works
                </a>
              </li>
              <li>
                <a
                  href="#pricing"
                  className="text-ink-inverse no-underline hover:underline"
                >
                  Pricing
                </a>
              </li>
              <li>
                {onDemoClick ? (
                  <button
                    type="button"
                    onClick={onDemoClick}
                    className="bg-transparent p-0 font-inherit text-ink-inverse hover:underline"
                  >
                    Demo
                  </button>
                ) : (
                  /* TODO: replace with real demo route */
                  <Link
                    href="/demo"
                    className="text-ink-inverse no-underline hover:underline"
                  >
                    Demo
                  </Link>
                )}
              </li>
              <li>
                {/* TODO: changelog stub */}
                <Link
                  href="/changelog"
                  className="text-ink-inverse no-underline hover:underline"
                >
                  Changelog
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="font-label-md text-label-md uppercase text-ink-inverse/60">
              COMPANY
            </p>
            <ul className="mt-4 space-y-2 font-body-md text-body-md">
              <li>
                {/* TODO: privacy policy page */}
                <Link
                  href="/privacy"
                  className="text-ink-inverse no-underline hover:underline"
                >
                  Privacy Policy
                </Link>
              </li>
              <li>
                {/* TODO: terms page */}
                <Link
                  href="/terms"
                  className="text-ink-inverse no-underline hover:underline"
                >
                  Terms of Service
                </Link>
              </li>
              <li>
                <a
                  href="mailto:hello@fivvle.io"
                  className="text-ink-inverse no-underline hover:underline"
                >
                  Contact
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="dashed-underline mt-12 h-px w-full opacity-40" aria-hidden="true" />

        <p className="mt-8 font-mono text-mono-sm uppercase tracking-widest text-ink-inverse/70">
          © 2026 FIVVLE. VALIDATION AS A SERVICE.
        </p>
      </div>
    </footer>
  );
}
