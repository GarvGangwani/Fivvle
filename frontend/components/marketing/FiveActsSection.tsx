import {
  marketingCardClass,
  sectionEyebrowClass,
  sectionShellClass,
} from "./marketing-styles";

const ACTS = [
  {
    number: "01",
    title: "SPARK",
    subtitle: "Capture the raw idea. No form, just a conversation start.",
    icon: "bolt",
    className: "bg-surface-card text-ink-primary",
    iconClassName: "text-ink-primary",
  },
  {
    number: "02",
    title: "REFINE",
    subtitle: "Pressure-test the hypothesis through a targeted chat.",
    icon: "chat",
    className: "bg-accent text-ink-inverse",
    iconClassName: "text-ink-inverse",
  },
  {
    number: "03",
    title: "EVIDENCE",
    subtitle: "Research runs against real web sources with cited signal.",
    icon: "search",
    className: "bg-surface-card text-ink-primary",
    iconClassName: "text-ink-primary",
  },
  {
    number: "04",
    title: "LAUNCH",
    subtitle: "Auto-generated landing page + tracked share links.",
    icon: "rocket_launch",
    className: "bg-brutalist-yellow text-ink-primary",
    iconClassName: "text-ink-primary",
  },
  {
    number: "05",
    title: "SIGNAL",
    subtitle: "Live metrics + a founder-facing verdict from real behavior.",
    icon: "insights",
    className: "bg-surface-card text-ink-primary",
    iconClassName: "text-ink-primary",
  },
] as const;

export function FiveActsSection() {
  return (
    <section id="five-acts" className={`${sectionShellClass} bg-canvas-bg`}>
      <div className="mx-auto max-w-7xl">
        <p className={sectionEyebrowClass}>THE FIVE ACTS</p>
        <h2 className="mt-3 max-w-3xl font-headline text-headline-lg uppercase text-ink-primary">
          From raw idea to real-world signal, in five acts.
        </h2>
        <p className="mt-4 max-w-2xl font-body-lg text-body-lg text-ink-secondary">
          Every experiment moves through the same structured pipeline. No manual
          configuration, no dashboards to wire up — just the work.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
          {ACTS.map((act) => {
            const isInverse = act.className.includes("text-ink-inverse");
            const mutedClass = isInverse
              ? "text-ink-inverse/80"
              : "text-ink-tertiary";

            return (
              <article
                key={act.number}
                className={`${marketingCardClass} flex min-h-[220px] flex-col p-card-padding ${act.className}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-mono-sm uppercase">
                    {act.number}
                  </span>
                  <span
                    className={`material-symbols-outlined icon-lg shrink-0 leading-none ${act.iconClassName}`}
                    aria-hidden="true"
                  >
                    {act.icon}
                  </span>
                </div>
                <h3 className="mt-6 font-headline text-headline-md uppercase">
                  {act.title}
                </h3>
                <p className={`mt-2 font-body-sm text-body-sm ${mutedClass}`}>
                  {act.subtitle}
                </p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
