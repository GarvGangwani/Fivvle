"use client";

import { useEffect, useRef, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import {
  extractShortStat,
  LIMITS,
} from "@/lib/copy-limits";
import {
  hasPricingSection,
  resolvePricingPlans,
} from "@/lib/landing-page-sections";
import { ABSTRACT_IMAGE_SLOTS, getSectionImageUrl } from "@/lib/section-images";
import {
  updateCta,
  updateFeature,
  updateHero,
  updateProblem,
  updateProofHeadline,
} from "@/lib/copy-mutations";
import { SectionImageSlot } from "./SectionImageSlot";
import { CopyText } from "./CopyText";
import { useCopyEdit } from "./CopyEditContext";
import { useScrollReveal } from "./useScrollReveal";
import styles from "./abstract.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap";

const MARQUEE_FALLBACK = [
  "Early access",
  "Founding members",
  "Waitlist open",
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

function metricFromProof(
  el: unknown,
  i: number,
): { value: string; label: string } | null {
  const cap = (text: string) => text.trim();
  if (typeof el === "object" && el !== null) {
    const o = el as { stat?: string; description?: string };
    const value = cap(String(o.stat ?? ""));
    if (value) {
      return {
        value,
        label: cap(
          String(o.description ?? `Metric ${i + 1}`),
        ),
      };
    }
  }
  const s = String(el);
  const stat = extractShortStat(s);
  if (stat) {
    return {
      value: stat,
      label: cap(
        s.replace(stat, "").replace(/^[\s:—–\-]+/, "").trim() || `Metric ${i + 1}`,
      ),
    };
  }
  return null;
}

export function AbstractTemplate({
  copy,
  projectName,
  cssVarStyle,
  isPublished,
  ctaConfig,
  publicationSlug,
  scrollTarget = "#cta-section",
  forEditor = false,
  sectionImages,
  experimentId,
  onSectionImageChange,
}: TemplateProps) {
  const cap = (text: string) => text.trim();
  const imageEditable =
    forEditor && Boolean(onSectionImageChange) && Boolean(experimentId);
  const imageSlotProps = {
    editable: imageEditable,
    experimentId,
    onImageChange: onSectionImageChange,
  };
  const inlineEditable = useCopyEdit()?.editable ?? false;
  const [navScrolled, setNavScrolled] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const hero = copy.hero;
  const headline = splitHeadline(hero?.headline ?? projectName);
  const problem = copy.problem;
  const pricingPlans = resolvePricingPlans(copy);
  const showPricing = hasPricingSection(copy);

  const features =
    (copy.features ?? []).length > 0
      ? (copy.features ?? []).slice(0, 5)
      : [];
  const proof = copy.proof;
  const proofEls = proof?.elements ?? [];
  const cta = copy.cta;
  const ctaLabel = cta?.button ?? "Get Started";

  const marqueeItems =
    proofEls.length >= 3
      ? proofEls.map((el, i) =>
          cap(
            typeof el === "string" ? el : `Partner ${i + 1}`,
          ),
        )
      : MARQUEE_FALLBACK;

  const metrics =
    proofEls.length > 0
      ? proofEls
          .slice(0, 4)
          .map((el, i) => metricFromProof(el, i))
          .filter((m): m is { value: string; label: string } => m != null)
      : [];

  const navItems = [
    { href: "#about", label: "About", show: Boolean(problem?.heading || problem?.body) },
    { href: "#features", label: "Features", show: features.length > 0 },
    { href: "#pricing", label: "Pricing", show: showPricing },
  ].filter((item) => item.show);

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

  const { revealProps, revealClass } = useScrollReveal(rootRef, [copy]);
  const rv = (id: string) => revealClass(id, styles.reveal, styles.revealVisible);

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
          {navItems.map((item) => (
            <a key={item.href} href={item.href}>
              {item.label}
            </a>
          ))}
        </div>
        <CtaAction
          config={ctaConfig}
          scrollTarget={scrollTarget}
          className={styles["nav-menu-btn"]}
          as="link"
        >
          <CopyText
            copy={copy}
            inline
            value={ctaLabel}
            mutate={(c, v) => updateCta(c, "button", v)}
          />
        </CtaAction>
      </nav>

      <section className={styles.hero}>
        <div className={styles["hero-bg"]}>
          <div className={styles.heroVisual} aria-hidden />
          <div className={styles["hero-bg-fade"]} />
          <div className={styles["hero-bg-fade-bottom"]} />
        </div>
        <div className={styles["hero-left"]}>
          <div {...revealProps("hero-title")} className={rv("hero-title")}>
            <CopyText
              copy={copy}
              as="h1"
              className={styles["hero-title"]}
              value={hero?.headline ?? projectName}
              mutate={(c, v) => updateHero(c, "headline", v)}
              maxLength={LIMITS.headline}
              multiline
            />
          </div>
          <div {...revealProps("hero-sub")} className={rv("hero-sub")}>
            <CopyText
              copy={copy}
              as="p"
              className={styles["hero-sub"]}
              value={
                hero?.subheadline ??
                "A short description of your product and why it matters. Lead with the outcome, not the feature list."
              }
              mutate={(c, v) => updateHero(c, "subheadline", v)}
              maxLength={LIMITS.subheadline}
              multiline
            />
          </div>
          <div {...revealProps("hero-cta")} className={rv("hero-cta")}>
            <CtaAction
              config={ctaConfig}
              scrollTarget="#features"
              className={styles["btn-arrow"]}
              as="link"
            >
            <CopyText
              copy={copy}
              inline
              value={hero?.cta ?? "See how it works"}
              mutate={(c, v) => updateHero(c, "cta", v)}
            />
            <ArrowIcon />
          </CtaAction>
          </div>
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
          <div
            {...revealProps("about")}
            className={`${styles["about-inner"]} ${rv("about")}`}
          >
            <CopyText
              copy={copy}
              as="h2"
              value={
                problem?.heading ??
                "A longer description of what your product does and the value it creates."
              }
              mutate={(c, v) => updateProblem(c, "heading", v)}
              maxLength={LIMITS.proofHeadline}
            />
            <CopyText
              copy={copy}
              as="p"
              value={
                problem?.body ??
                "Explain the core problem your product solves and the transformation it delivers. Write about outcomes, not features."
              }
              mutate={(c, v) => updateProblem(c, "body", v)}
              maxLength={LIMITS.subheadline + 80}
              multiline
            />
            <a href="#features" className={styles["btn-arrow"]}>
              <span>Learn more</span>
              <ArrowIcon />
            </a>
          </div>
        </div>
      </section>

      {features.length > 0 ? (
      <section className={styles.features} id="features">
        <div className={styles.container}>
          <div
            {...revealProps("features-header")}
            className={`${styles["features-header"]} ${rv("features-header")}`}
          >
            <h2>What makes it different.</h2>
            <p>
              <CopyText
                copy={copy}
                inline
                value={
                  proof?.headline ??
                  "A summary of your core differentiators, explained clearly."
                }
                mutate={updateProofHeadline}
                maxLength={LIMITS.proofHeadline}
              />
            </p>
          </div>
          <div className={styles["feature-accordion"]}>
            {features.map((f, i) => (
              <div
                key={i}
                {...revealProps(`feature-${i}`)}
                className={`${styles["feature-row"]} ${rv(`feature-${i}`)}`}
              >
                <span className={styles["feature-num"]}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <CopyText
                  copy={copy}
                  as="h3"
                  value={f.title}
                  mutate={(c, v) => updateFeature(c, i, "title", v)}
                  maxLength={LIMITS.featureTitle}
                />
                <CopyText
                  copy={copy}
                  as="p"
                  value={f.description}
                  mutate={(c, v) => updateFeature(c, i, "description", v)}
                  maxLength={LIMITS.featureBody}
                  multiline
                />
              </div>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      <section className={styles.showcase}>
        <div className={styles.container}>
          <div className={styles["showcase-grid"]}>
            <div
              {...revealProps("showcase-image")}
              className={`${styles["showcase-image"]} ${rv("showcase-image")}`}
            >
              <SectionImageSlot
                slotId={ABSTRACT_IMAGE_SLOTS.showcase}
                imageUrl={getSectionImageUrl(sectionImages, ABSTRACT_IMAGE_SLOTS.showcase)}
                fill
                className={styles.showcasePlaceholder}
                placeholderClassName={styles.showcasePlaceholder}
                alt=""
                {...imageSlotProps}
              />
            </div>
            <div
              {...revealProps("showcase-content")}
              className={`${styles["showcase-content"]} ${rv("showcase-content")}`}
            >
              <CopyText
                copy={copy}
                as="h2"
                value={showcaseTitle}
                mutate={(c, v) => updateProblem(c, "heading", v)}
                maxLength={LIMITS.proofHeadline}
              />
              <CopyText
                copy={copy}
                as="p"
                value={showcaseP1}
                mutate={(c, v) => updateProblem(c, "body", v)}
                maxLength={LIMITS.featureBody + 40}
                multiline
              />
              {!inlineEditable && showcaseP2 ? (
                <p>{showcaseP2.trim()}</p>
              ) : null}
              {showPricing ? (
              <a href="#pricing" className={styles["btn-arrow"]} style={{ marginTop: "1rem" }}>
                <span>View plans</span>
                <ArrowIcon />
              </a>
              ) : (
              <a href="#cta-section" className={styles["btn-arrow"]} style={{ marginTop: "1rem" }}>
                <span>{ctaLabel}</span>
                <ArrowIcon />
              </a>
              )}
            </div>
          </div>
        </div>
      </section>

      {metrics.length > 0 ? (
      <section className={styles.metrics}>
        <div className={styles.container}>
          <div className={styles["metrics-row"]}>
            {metrics.map((m, i) => (
              <div
                key={i}
                {...revealProps(`metric-${i}`)}
                className={`${styles.metric} ${rv(`metric-${i}`)}`}
              >
                <div className={styles["metric-val"]}>{m.value}</div>
                <p className={styles["metric-label"]}>{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      {showPricing ? (
      <section className={styles.pricing} id="pricing">
        <div className={styles.container}>
          <div
            {...revealProps("pricing-intro")}
            className={`${styles["pricing-intro"]} ${rv("pricing-intro")}`}
          >
            <h2>Choose your plan.</h2>
            <p>Pick the option that matches where you are today.</p>
          </div>
          <div
            {...revealProps("pricing-duo")}
            className={`${styles["pricing-duo"]} ${rv("pricing-duo")}`}
          >
            {pricingPlans.map((plan, i) => (
              <div
                key={plan.name}
                className={`${styles["price-tier"]}${
                  plan.featured || i === 1 ? ` ${styles.featured}` : ""
                }`}
              >
                <div>
                  <div className={styles["price-name"]}>{plan.name}</div>
                  <div>
                    <span className={styles["price-amount"]}>{plan.price}</span>
                    {plan.period ? (
                      <span
                        className={styles["price-period"]}
                        style={
                          plan.featured || i === 1
                            ? { color: "rgba(255,255,255,0.5)" }
                            : undefined
                        }
                      >
                        /{plan.period}
                      </span>
                    ) : null}
                  </div>
                  {plan.description ? (
                    <p className={styles["price-desc"]}>{plan.description}</p>
                  ) : null}
                  {plan.features.length > 0 ? (
                    <ul className={styles["price-feat"]}>
                      {plan.features.map((feat, j) => (
                        <li key={j}>
                          <CheckIcon />
                          {feat}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
                <CtaAction
                  config={ctaConfig}
                  scrollTarget={scrollTarget}
                  className={
                    plan.featured || i === 1
                      ? styles["btn-tier-light"]
                      : styles["btn-tier"]
                  }
                  as="link"
                >
                  {ctaLabel}
                </CtaAction>
              </div>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      <section className={styles.cta} id="cta-section">
        <div className={styles.container}>
          <div className={styles["cta-layout"]}>
            <div
              {...revealProps("cta-text")}
              className={`${styles["cta-text"]} ${rv("cta-text")}`}
            >
              <CopyText
                copy={copy}
                as="h2"
                value={cta?.heading ?? "Ready to get started?"}
                mutate={(c, v) => updateCta(c, "heading", v)}
                maxLength={LIMITS.ctaHeading}
              />
              <CopyText
                copy={copy}
                as="p"
                value={
                  cta?.subheading ??
                  "Join the waitlist for early access when the next cohort opens."
                }
                mutate={(c, v) => updateCta(c, "subheading", v)}
                maxLength={LIMITS.ctaSubheading}
                multiline
              />
              {isPublished && publicationSlug ? (
                <WaitlistForm
                  slug={publicationSlug}
                  buttonLabel={ctaLabel}
                  className={styles["cta-form"]}
                  metaClassName={styles.ctaFormMeta}
                />
              ) : (
                <>
                  <form className={styles["cta-form"]} onSubmit={(e) => e.preventDefault()}>
                    <input type="email" placeholder="Enter your email" required readOnly />
                    <button type="submit">
                      <CopyText
                        copy={copy}
                        inline
                        value={ctaLabel}
                        mutate={(c, v) => updateCta(c, "button", v)}
                      />
                    </button>
                  </form>
                  <p className={styles.ctaFormMeta}>No spam · Unsubscribe anytime</p>
                </>
              )}
            </div>
            <div
              {...revealProps("cta-visual")}
              className={`${styles["cta-visual"]} ${rv("cta-visual")}`}
            >
              <SectionImageSlot
                slotId={ABSTRACT_IMAGE_SLOTS.cta}
                imageUrl={getSectionImageUrl(sectionImages, ABSTRACT_IMAGE_SLOTS.cta)}
                fill
                className={styles.ctaVisualShape}
                placeholderClassName={styles.ctaVisualShape}
                alt=""
                {...imageSlotProps}
              />
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
