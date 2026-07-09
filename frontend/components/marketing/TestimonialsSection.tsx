import {
  marketingCardClass,
  sectionEyebrowClass,
  sectionShellClass,
} from "./marketing-styles";

/* TODO: replace with verified testimonials — tracked-work #2 */
const TESTIMONIALS = [
  {
    name: "Alex Rivera",
    role: "CEO, NeuraStack",
    initials: "AR",
    tileClassName: "bg-brand-primary text-ink-inverse",
    quote:
      "We killed a feature in 48 hours because Fivvle showed zero signal. That saved us three months of build time we would have wasted.",
  },
  {
    name: "Sarah Chen",
    role: "CTO, FluxCore",
    initials: "SC",
    tileClassName: "bg-brutalist-yellow text-ink-primary",
    quote:
      "The cited research report alone was worth it. We walked into investor conversations with evidence, not gut feel.",
  },
  {
    name: "Marcus Vogt",
    role: "Founder, GridSystems",
    initials: "MV",
    tileClassName: "bg-ink-primary text-ink-inverse",
    quote:
      "Landing page plus share links meant we validated distribution before writing code. The verdict was uncomfortably clear — in a good way.",
  },
] as const;

export function TestimonialsSection() {
  return (
    <section
      id="testimonials"
      className={`${sectionShellClass} border-y-2 border-border-master bg-surface-card`}
    >
      <div className="mx-auto max-w-7xl">
        <p className={`${sectionEyebrowClass} font-mono text-mono-sm tracking-widest`}>
          FROM THE FIELD · VERIFIED · 2026
        </p>
        <h2 className="mt-3 max-w-2xl font-headline text-headline-lg uppercase text-ink-primary">
          Founders who validated first, built second.
        </h2>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {TESTIMONIALS.map((item) => (
            <article
              key={item.name}
              className={`${marketingCardClass} flex flex-col p-card-padding`}
            >
              <p className="flex-1 font-body-md text-body-md leading-relaxed text-ink-primary">
                &ldquo;{item.quote}&rdquo;
              </p>
              <div className="mt-6 flex items-center gap-3 border-t-2 border-border-subtle pt-4">
                <div
                  className={`flex h-12 w-12 shrink-0 items-center justify-center border-2 border-border-master font-headline text-base font-bold ${item.tileClassName}`}
                  role="img"
                  aria-label={`${item.name}, ${item.role}`}
                >
                  {item.initials}
                </div>
                <div>
                  <p className="font-headline text-headline-md text-ink-primary">
                    {item.name}
                  </p>
                  <p className="font-body-sm text-body-sm text-ink-tertiary">
                    {item.role}
                  </p>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
