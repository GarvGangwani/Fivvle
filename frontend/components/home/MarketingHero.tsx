import Link from "next/link";
import { ArrowRight, CheckCircle2, Sparkles, Zap } from "lucide-react";

const FEATURES = [
  {
    icon: Sparkles,
    title: "AI refinement",
    description: "Shape your raw idea into a testable hypothesis through conversation.",
  },
  {
    icon: Zap,
    title: "Market research",
    description: "Multi-source evidence with citations — competitors, risks, and demand signals.",
  },
  {
    icon: CheckCircle2,
    title: "Real validation",
    description: "Launch a landing page, track signups, and get an insight report to decide.",
  },
] as const;

export function MarketingHero() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="fv-hero-glow" />

      <div className="relative mx-auto flex max-w-5xl flex-col items-center px-4 pb-24 pt-20 sm:pt-28">
        <div
          className="fv-f-logo mb-8"
          style={{ width: 56, height: 56, fontSize: 28 }}
          aria-hidden
        >
          F
        </div>

        <h1 className="fv-fade-up max-w-3xl text-center text-4xl font-bold tracking-[-0.04em] text-[var(--fv-text)] sm:text-5xl lg:text-6xl">
          Validate ideas with{" "}
          <span className="bg-gradient-to-r from-[var(--fv-accent)] to-[var(--fv-accent-gradient-end)] bg-clip-text text-transparent">
            real signal
          </span>
        </h1>

        <p className="fv-fade-up-delay mt-5 max-w-xl text-center text-lg leading-relaxed text-[var(--fv-text-soft)]">
          Fivvle researches your market, generates a landing page, and measures
          interest — so you know whether to proceed, iterate, or pivot.
        </p>

        <div className="fv-fade-up-delay mt-10 flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="/signup"
            className="fv-btn-primary w-full justify-center px-8 py-3.5 text-sm no-underline sm:w-auto"
          >
            Get started free
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login"
            className="fv-btn-ghost w-full px-8 py-3.5 text-center text-sm font-semibold no-underline sm:w-auto"
          >
            Log in
          </Link>
        </div>

        <div className="fv-fade-up-delay mt-20 grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="fv-section-card !p-5 text-center sm:text-left"
            >
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--fv-accent-muted)] sm:mx-0">
                <Icon className="h-5 w-5 text-[var(--fv-accent)]" />
              </div>
              <h3 className="font-semibold text-[var(--fv-text)]">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-[var(--fv-text-muted)]">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
