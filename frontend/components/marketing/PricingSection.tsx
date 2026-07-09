import Link from "next/link";
import {
  marketingButtonClass,
  marketingCardClass,
  sectionEyebrowClass,
  sectionShellClass,
} from "./marketing-styles";

const TIERS = [
  {
    id: "spark",
    name: "SPARK",
    price: "$0",
    period: "/mo",
    access: "Acts 01–02 only",
    features: [
      "Idea capture",
      "Hypothesis refinement",
      "Community support",
      "No research runs",
    ],
    cta: "START FREE",
    highlighted: false,
  },
  {
    id: "founder",
    name: "FOUNDER",
    price: "$49",
    period: "/mo",
    access: "Acts 01–04",
    features: [
      "Everything in Spark",
      "Full research runs",
      "Landing page generation",
      "Share-link analytics",
      "20 validations / mo",
    ],
    cta: "DEPLOY PLAN",
    highlighted: true,
  },
  {
    id: "unicorn",
    name: "UNICORN",
    price: "$199",
    period: "/mo",
    access: "Full pipeline + priority",
    features: [
      "Everything in Founder",
      "Signal act (live metrics + verdict)",
      "Priority queue",
      "Unlimited validations",
      "Insight reports",
    ],
    cta: "GO INFINITE",
    highlighted: false,
  },
] as const;

function CheckIcon({ inverse }: { inverse?: boolean }) {
  return (
    <span
      className={`material-symbols-outlined shrink-0 ${inverse ? "text-ink-inverse" : "text-brand-primary"}`}
      aria-hidden="true"
    >
      check
    </span>
  );
}

export function PricingSection() {
  return (
    <section id="pricing" className={`${sectionShellClass} bg-canvas-bg`}>
      <div className="mx-auto max-w-7xl">
        <p className={sectionEyebrowClass}>SUBSCRIPTION TIERS</p>
        <h2 className="mt-3 max-w-3xl font-headline text-headline-lg uppercase text-ink-primary">
          Pick a tier. Stop guessing about your idea.
        </h2>

        {/* TODO: subscription monetization backend not yet implemented — CTAs must not go to checkout. Route to waitlist page or open "Coming soon" modal. Tracked-work item #3. */}
        <div className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {TIERS.map((tier) => {
            const inverse = tier.highlighted;

            return (
              <article
                key={tier.id}
                className={`${marketingCardClass} relative flex flex-col overflow-visible p-card-padding ${
                  inverse
                    ? "bg-brand-primary pt-12 text-ink-inverse"
                    : "bg-surface-card text-ink-primary"
                }`}
              >
                {tier.highlighted ? (
                  <span className="absolute right-4 top-4 rotate-12 border-2 border-border-master bg-brutalist-yellow px-2 py-1 font-label-md text-label-md uppercase text-ink-primary shadow-brutal-sm">
                    MOST POPULAR
                  </span>
                ) : null}

                <p className="font-label-md text-label-md uppercase opacity-80">
                  {tier.name}
                </p>
                <p className="mt-2 font-display text-display-lg leading-none">
                  {tier.price}
                  <span className="font-body-md text-body-md">{tier.period}</span>
                </p>
                <p
                  className={`mt-2 font-body-sm text-body-sm ${inverse ? "text-ink-inverse/85" : "text-ink-tertiary"}`}
                >
                  {tier.access}
                </p>

                <ul className="mt-6 flex flex-1 flex-col gap-2">
                  {tier.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 font-body-md text-body-md"
                    >
                      <CheckIcon inverse={inverse} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  href={`/waitlist?tier=${tier.id}`}
                  className={`${marketingButtonClass} mt-8 w-full px-4 py-3 text-center font-label-md text-label-md uppercase no-underline ${
                    inverse
                      ? "bg-ink-inverse text-brand-primary"
                      : "bg-surface-card text-ink-primary"
                  }`}
                >
                  {tier.cta}
                </Link>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
