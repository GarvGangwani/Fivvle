"use client";

import { useEffect, useRef, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import {
  extractShortStat,
  LIMITS,
  truncateText,
} from "@/lib/copy-limits";
import styles from "./abstract.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap";

const MARQUEE_FALLBACK = [
  "Brand One",
  "Brand Two",
  "Brand Three",
  "Brand Four",
  "Brand Five",
  "Brand Six",
  "Brand Seven",
  "Brand Eight",
];

const DEFAULT_FEATURES = [
  {
    title: "Feature headline here",
    description:
      "A short description of the feature and the outcome it delivers for your customer.",
  },
  {
    title: "Feature headline here",
    description:
      "A short description of the feature and the outcome it delivers for your customer.",
  },
  {
    title: "Feature headline here",
    description:
      "A short description of the feature and the outcome it delivers for your customer.",
  },
  {
    title: "Feature headline here",
    description:
      "A short description of the feature and the outcome it delivers for your customer.",
  },
  {
    title: "Feature headline here",
    description:
      "A short description of the feature and the outcome it delivers for your customer.",
  },
];

const DEFAULT_METRICS = [
  { value: "98%", label: "Metric label here" },
  { value: "4.2x", label: "Metric label here" },
  { value: "<60s", label: "Metric label here" },
  { value: "12k+", label: "Metric label here" },
];

const PRICE_FEATURES = [
  "Feature check one",
  "Feature check two",
  "Feature check three",
  "Feature check four",
];

function ArrowIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M3.33 8h9.34M8.67 4l4 4-4 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className={styles["check-icon"]} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function getScrollParent(node: HTMLElement | null): HTMLElement | Window {
  let el = node?.parentElement;
  while (el) {
    const { overflowY } = getComputedStyle(el);
    if (overflowY === "auto" || overflowY === "scroll") return el;
    el = el.parentElement;
  }
  return window;
}

function metricFromProof(el: unknown, i: number): { value: string; label: string } {
  if (typeof el === "object" && el !== null) {
    const o = el as { stat?: string; description?: string };
    const value = truncateText(String(o.stat ?? ""), LIMITS.floatValue);
    if (value) {
      return {
        value,
        label: truncateText(String(o.description ?? `Metric ${i + 1}`), LIMITS.floatLabel),
      };
    }
  }
  const s = String(el);
  const stat = extractShortStat(s);
  if (stat) {
    return {
      value: stat,
      label: truncateText(
        s.replace(stat, "").replace(/^[\s:—–\-]+/, "").trim() || `Metric ${i + 1}`,
        LIMITS.floatLabel,
      ),
    };
  }
  return DEFAULT_METRICS[i] ?? { value: "—", label: `Metric ${i + 1}` };
}

export function AbstractTemplate({
  copy,
  projectName,
  cssVarStyle,
  isPublished,
  ctaConfig,
  publicationSlug,
  scrollTarget = "#cta-section",
}: TemplateProps) {
  const [navScrolled, setNavScrolled] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const hero = copy.hero;
  const headline = splitHeadline(hero?.headline ?? projectName);
  const problem = copy.problem;
  const features =
    (copy.features ?? []).length > 0
      ? (copy.features ?? []).slice(0, 5)
      : DEFAULT_FEATURES;
  const proof = copy.proof;
  const proofEls = proof?.elements ?? [];
  const cta = copy.cta;
  const ctaLabel = cta?.button ?? "Get Started";

  const marqueeItems =
    proofEls.length >= 3
      ? proofEls.map((el, i) =>
          truncateText(
            typeof el === "string" ? el : `Partner ${i + 1}`,
            LIMITS.marqueeItem,
          ),
        )
      : MARQUEE_FALLBACK;

  const metrics = DEFAULT_METRICS.map((d, i) => {
    const el = proofEls[i];
    return el != null ? metricFromProof(el, i) : d;
  });

  const showcaseTitle =
    problem?.heading ??
    "Built for teams that value clarity.";
  const showcaseBody = problem?.body?.split(/\n\n|\.\s+(?=[A-Z])/) ?? [];
  const showcaseP1 =
    showcaseBody[0] ??
    "A description of how your product integrates into existing workflows. Focus on the experience, not the technical specifications.";
  const showcaseP2 =
    showcaseBody[1] ??
    "Explain the second key benefit here. Keep it concrete and avoid generic marketing language.";

  const priceFeats =
    features.length >= 4
      ? features.slice(0, 4).map((f) => truncateText(f.title, LIMITS.featureTitle))
      : PRICE_FEATURES;

  const displayName = projectName;

  useEffect(() => {
    const id = "fivvle-abstract-fonts";
    if (!document.getElementById(id)) {
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = FONTS;
      document.head.appendChild(link);
    }
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const scrollTargetEl = getScrollParent(root);
    const onScroll = () => {
      const y =
        scrollTargetEl === window
          ? window.scrollY
          : (scrollTargetEl as HTMLElement).scrollTop;
      setNavScrolled(y > 40);
    };
    scrollTargetEl.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => scrollTargetEl.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const els = root.querySelectorAll(`.${styles.reveal}`);
    const scrollRoot = getScrollParent(root);
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) e.target.classList.add(styles.revealVisible);
        }
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -10% 0px",
        root: scrollRoot === window ? null : (scrollRoot as HTMLElement),
      },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [copy]);

  return (
    <div
      ref={rootRef}
      id="top"
      className={`${styles.root} ${base.root}`}
      style={{
        ...cssVarStyle,
        ["--max-w" as string]: "1200px",
        ["--font" as string]: '"Outfit", system-ui, sans-serif',
      }}
    >
      <nav
        className={`${styles.navbar} ${navScrolled ? styles.navbarScrolled : ""}`}
        id="navbar"
      >
        <a href="#top" className={styles["nav-logo"]}>
          {displayName}
        </a>
        <div className={styles["nav-links"]}>
          <a href="#about">About</a>
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
        </div>
        <CtaAction
          config={ctaConfig}
          scrollTarget={scrollTarget}
          className={styles["nav-menu-btn"]}
          as="link"
        >
          {ctaLabel}
        </CtaAction>
      </nav>

      <section className={styles.hero}>
        <div className={styles["hero-bg"]}>
          <div className={styles.heroVisual} aria-hidden />
          <div className={styles["hero-bg-fade"]} />
          <div className={styles["hero-bg-fade-bottom"]} />
        </div>
        <div className={styles["hero-left"]}>
          <h1 className={`${styles["hero-title"]} ${styles.reveal}`}>
            {headline.main}
            {headline.accent ? (
              <>
                <br />
                <span className={styles.light}>{headline.accent}</span>
              </>
            ) : null}
          </h1>
          <p className={`${styles["hero-sub"]} ${styles.reveal}`}>
            {truncateText(
              hero?.subheadline ??
                "A short description of your product and why it matters. Lead with the outcome, not the feature list.",
              LIMITS.subheadline,
            )}
          </p>
          <CtaAction
            config={ctaConfig}
            scrollTarget="#features"
            className={`${styles["btn-arrow"]} ${styles.reveal}`}
            as="link"
          >
            <span>{hero?.cta ?? "See how it works"}</span>
            <ArrowIcon />
          </CtaAction>
        </div>
        <div className={styles["hero-right"]} />
      </section>

      <div className={styles["scroll-strip"]}>
        <div className={styles["scroll-track"]}>
          {[...marqueeItems, ...marqueeItems].map((item, i) => (
            <span key={i} className={styles["scroll-item"]}>
              {item}
            </span>
          ))}
        </div>
      </div>

      <section className={styles.about} id="about">
        <div className={styles.container}>
          <div className={`${styles["about-inner"]} ${styles.reveal}`}>
            <h2>
              {truncateText(
                problem?.heading ??
                  "A longer description of what your product does and the value it creates.",
                LIMITS.proofHeadline,
              )}
            </h2>
            <p>
              {truncateText(
                problem?.body ??
                  "Explain the core problem your product solves and the transformation it delivers. Write about outcomes, not features.",
                LIMITS.subheadline + 80,
              )}
            </p>
            <a href="#features" className={styles["btn-arrow"]}>
              <span>Learn more</span>
              <ArrowIcon />
            </a>
          </div>
        </div>
      </section>

      <section className={styles.features} id="features">
        <div className={styles.container}>
          <div className={`${styles["features-header"]} ${styles.reveal}`}>
            <h2>What makes it different.</h2>
            <p>
              {truncateText(
                proof?.headline ?? "A summary of your core differentiators, explained clearly.",
                LIMITS.proofHeadline,
              )}
            </p>
          </div>
          <div className={styles["feature-accordion"]}>
            {features.map((f, i) => (
              <div key={i} className={`${styles["feature-row"]} ${styles.reveal}`}>
                <span className={styles["feature-num"]}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3>{truncateText(f.title, LIMITS.featureTitle)}</h3>
                <p>{truncateText(f.description, LIMITS.featureBody)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.showcase}>
        <div className={styles.container}>
          <div className={styles["showcase-grid"]}>
            <div className={`${styles["showcase-image"]} ${styles.reveal}`}>
              <div className={styles.showcasePlaceholder} aria-hidden />
            </div>
            <div className={`${styles["showcase-content"]} ${styles.reveal}`}>
              <h2>{truncateText(showcaseTitle, LIMITS.proofHeadline)}</h2>
              <p>{truncateText(showcaseP1, LIMITS.featureBody + 40)}</p>
              <p>{truncateText(showcaseP2, LIMITS.featureBody + 40)}</p>
              <a href="#pricing" className={styles["btn-arrow"]} style={{ marginTop: "1rem" }}>
                <span>View plans</span>
                <ArrowIcon />
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.metrics}>
        <div className={styles.container}>
          <div className={styles["metrics-row"]}>
            {metrics.map((m, i) => (
              <div key={i} className={`${styles.metric} ${styles.reveal}`}>
                <div className={styles["metric-val"]}>{m.value}</div>
                <p className={styles["metric-label"]}>{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.pricing} id="pricing">
        <div className={styles.container}>
          <div className={`${styles["pricing-intro"]} ${styles.reveal}`}>
            <h2>Flexible pricing, no surprises.</h2>
            <p>
              Choose the plan that fits your needs. Both plans include core features and
              standard support.
            </p>
          </div>
          <div className={`${styles["pricing-duo"]} ${styles.reveal}`}>
            <div className={styles["price-tier"]}>
              <div>
                <div className={styles["price-name"]}>Standard</div>
                <div>
                  <span className={styles["price-amount"]}>$29</span>
                  <span className={styles["price-period"]}>/once</span>
                </div>
                <p className={styles["price-desc"]}>
                  For individuals getting started with the essentials.
                </p>
                <ul className={styles["price-feat"]}>
                  {priceFeats.map((feat, i) => (
                    <li key={i}>
                      <CheckIcon />
                      {feat}
                    </li>
                  ))}
                </ul>
              </div>
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles["btn-tier"]}
                as="link"
              >
                {ctaLabel}
              </CtaAction>
            </div>
            <div className={`${styles["price-tier"]} ${styles.featured}`}>
              <div>
                <div className={styles["price-name"]}>Professional</div>
                <div>
                  <span className={styles["price-amount"]}>$99</span>
                  <span className={styles["price-period"]} style={{ color: "rgba(255,255,255,0.5)" }}>
                    /once
                  </span>
                </div>
                <p className={styles["price-desc"]}>
                  For growing teams that need more power and support.
                </p>
                <ul className={styles["price-feat"]}>
                  {[...priceFeats, "Feature check five"].map((feat, i) => (
                    <li key={i}>
                      <CheckIcon />
                      {feat}
                    </li>
                  ))}
                </ul>
              </div>
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles["btn-tier-light"]}
                as="link"
              >
                {ctaLabel}
              </CtaAction>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.cta} id="cta-section">
        <div className={styles.container}>
          <div className={styles["cta-layout"]}>
            <div className={`${styles["cta-text"]} ${styles.reveal}`}>
              <h2>{truncateText(cta?.heading ?? "Ready to get started?", LIMITS.ctaHeading)}</h2>
              <p>
                {truncateText(
                  cta?.subheading ??
                    "A short description of what happens when they sign up. No credit card required, free to start.",
                  LIMITS.ctaSubheading,
                )}
              </p>
              {isPublished && publicationSlug ? (
                <WaitlistForm
                  slug={publicationSlug}
                  buttonLabel={ctaLabel}
                  className={styles["cta-form"]}
                  inputClassName=""
                  buttonClassName=""
                />
              ) : (
                <form className={styles["cta-form"]} onSubmit={(e) => e.preventDefault()}>
                  <input type="email" placeholder="Enter your email" required readOnly />
                  <button type="submit">{ctaLabel}</button>
                </form>
              )}
            </div>
            <div className={`${styles["cta-visual"]} ${styles.reveal}`}>
              <div className={styles.ctaVisualShape} aria-hidden />
            </div>
          </div>
        </div>
      </section>

      <footer>
        <div className={`${styles.container} ${styles.footerInner}`}>
          <span>&copy; {new Date().getFullYear()} {displayName}. All rights reserved.</span>
          <div className={styles.footerBadge}>
            <span>Engineered via</span>
            <a href="https://fivvle.io">
              <strong>Fivvle</strong>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
