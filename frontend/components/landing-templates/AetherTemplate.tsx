"use client";

import { useEffect, useRef, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import {
  extractShortStat,
  LIMITS,
} from "@/lib/copy-limits";
import {
  hasPricingSection,
  resolvePricingPlans,
} from "@/lib/landing-page-sections";
import {
  updateCta,
  updateFeature,
  updateHero,
  updateProblem,
  updateProofHeadline,
} from "@/lib/copy-mutations";
import { CopyText } from "./CopyText";
import { useScrollReveal } from "./useScrollReveal";
import styles from "./aether.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap";

const MARQUEE_FALLBACK = [
  "Early access",
  "Founding members",
  "Waitlist open",
];

const CARD_VARIANTS = ["cardDefault", "cardSubtle", "cardGreen", "cardDark"] as const;

function floatStat(
  el: unknown,
  i: number,
): { label: string; value: string } | null {
  const cap = (text: string) => text.trim();
  if (typeof el === "object" && el !== null) {
    const o = el as { stat?: string; description?: string };
    const value = cap(String(o.stat ?? ""));
    if (!value) return null;
    return {
      label: cap(String(o.description ?? `Metric ${i + 1}`)),
      value,
    };
  }
  const s = String(el);
  const stat = extractShortStat(s);
  if (!stat) return null;
  const label = cap(
    s.replace(stat, "").replace(/^[\s:—–\-]+/, "").trim() || `Metric ${i + 1}`,
  );
  return { label, value: stat };
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

export function AetherTemplate({
  copy,
  projectName,
  cssVarStyle,
  isPublished,
  ctaConfig,
  publicationSlug,
  scrollTarget = "#cta",
  branding,
  forEditor = false,
}: TemplateProps) {
  const cap = (text: string) => text.trim();
  const [navScrolled, setNavScrolled] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const hero = copy.hero;
  const headline = splitHeadline(hero?.headline ?? projectName);
  const features = copy.features ?? [];
  const problem = copy.problem;
  const proof = copy.proof;
  const cta = copy.cta;

  const pricingPlans = resolvePricingPlans(copy);
  const showPricing = hasPricingSection(copy);

  const bento = features.slice(0, 4).map((f) => {
    const metricMatch = f.title.match(/\d[\d,k+%.]*\+?/);
    const label = (
      metricMatch ? f.title.replace(metricMatch[0], "") : f.title
    ).trim();
    return {
      metric: metricMatch?.[0] ?? "",
      label: label || f.title,
      body: f.description,
    };
  });

  const benefits = features.slice(0, 3);
  const outcomes = features.slice(0, 4).map((f) => ({
    title: f.title,
    description: f.description,
  }));

  const proofEls = proof?.elements ?? [];
  const extractedFloat = proofEls
    .map((el, i) => floatStat(el, i))
    .filter((x): x is { label: string; value: string } => x != null)
    .slice(0, 3);
  const floatCards = extractedFloat;

  const marqueeItems =
    proofEls.length >= 3
      ? proofEls.map((el, i) =>
          cap(typeof el === "string" ? el : `Signal ${i + 1}`).toUpperCase(),
        )
      : MARQUEE_FALLBACK;

  const navItems = [
    { href: "#features", label: "Features", show: features.length > 0 },
    { href: "#benefits", label: "Benefits", show: benefits.length > 0 },
    { href: "#outcome", label: "Outcome", show: outcomes.length > 0 },
    { href: "#pricing", label: "Pricing", show: showPricing },
  ].filter((item) => item.show);

  useEffect(() => {
    const id = "fivvle-aether-fonts";
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
      setNavScrolled(y > 50);
    };
    scrollTargetEl.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => scrollTargetEl.removeEventListener("scroll", onScroll);
  }, []);

  const { revealProps, revealClass } = useScrollReveal(rootRef, [copy]);
  const rv = (id: string) => revealClass(id, styles.reveal, styles.revealVisible);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let frame = 0;

    class Particle {
      x = 0;
      y = 0;
      size = 1;
      speedX = 0;
      speedY = 0;
      alpha = 0.3;
      twinkleSpeed = 0.008;
      twinkleDirection = 1;

      constructor(w: number, h: number) {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.size = Math.random() * 1.5 + 0.5;
        this.speedX = Math.random() * 0.1 - 0.05;
        this.speedY = Math.random() * 0.1 - 0.05;
        this.alpha = Math.random() * 0.5 + 0.2;
        this.twinkleSpeed = Math.random() * 0.01 + 0.005;
      }

      update(w: number, h: number) {
        this.x += this.speedX;
        this.y += this.speedY;
        this.alpha += this.twinkleSpeed * this.twinkleDirection;
        if (this.alpha > 0.8 || this.alpha < 0.2) this.twinkleDirection *= -1;
        if (this.x < 0) this.x = w;
        if (this.x > w) this.x = 0;
        if (this.y < 0) this.y = h;
        if (this.y > h) this.y = 0;
      }

      draw(c: CanvasRenderingContext2D) {
        c.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
        c.beginPath();
        c.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        c.fill();
      }
    }

    const particles: Particle[] = [];
    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      width = canvas.width = rect?.width ?? window.innerWidth;
      height = canvas.height = rect?.height ?? window.innerHeight;
      if (particles.length === 0) {
        for (let i = 0; i < 50; i++) particles.push(new Particle(width, height));
      }
    };

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
      ctx.lineWidth = 0.5;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dist = Math.hypot(
            particles[i].x - particles[j].x,
            particles[i].y - particles[j].y,
          );
          if (dist < 130) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }
      particles.forEach((p) => {
        p.update(width, height);
        p.draw(ctx);
      });
      frame = requestAnimationFrame(animate);
    };

    resize();
    animate();
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  const ctaLabel = cta?.button ?? hero?.cta ?? "Get Started";
  const heroPrimary = hero?.cta ?? "Start free";
  const heroSecondary = "See how it works";

  return (
    <div
      ref={rootRef}
      id="top"
      className={`${styles.root} ${base.root}`}
      style={cssVarStyle}
    >
      <header className={styles.hero}>
        <canvas ref={canvasRef} className={styles.heroCanvas} aria-hidden />
        <div className={styles.heroNebula} aria-hidden />
        <nav
          className={`${styles.navbar} ${navScrolled ? styles.navbarScrolled : ""}`}
        >
          <div className={styles.navbarInner}>
            <BrandMark
              branding={branding}
              projectName={projectName}
              variant="aether"
              className={styles.navBrand}
              href="#top"
            />
          <div className={styles.navLinks}>
            {navItems.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </div>
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.btnNav}
              as="link"
            >
              <CopyText
                copy={copy}
                inline
                value={ctaLabel}
                mutate={(c, v) => updateCta(c, "button", v)}
              />
            </CtaAction>
          </div>
        </nav>

        <div className={styles.heroStage}>
          <div className={`${styles.container} ${styles.heroContent}`}>
          <div {...revealProps("hero-title")} className={rv("hero-title")}>
            <CopyText
              copy={copy}
              as="h1"
              className={styles.heroTitle}
              value={hero?.headline ?? projectName}
              mutate={(c, v) => updateHero(c, "headline", v)}
              maxLength={LIMITS.headline}
              multiline
            />
          </div>
          <div className={styles.spLg} />
          <div {...revealProps("hero-sub")} className={rv("hero-sub")}>
            <CopyText
              copy={copy}
              as="p"
              className={styles.heroSub}
              value={
                hero?.subheadline ??
                "A short description of your product and why it matters. Lead with the outcome, then earn the click."
              }
              mutate={(c, v) => updateHero(c, "subheadline", v)}
              maxLength={LIMITS.subheadline}
              multiline
            />
          </div>
          <div className={styles.spXl} />
          <div
            {...revealProps("hero-buttons")}
            className={`${styles.heroButtons} ${rv("hero-buttons")}`}
          >
            <CtaAction
              config={ctaConfig}
              scrollTarget="#features"
              className={styles.btnSecondaryDark}
              as="link"
            >
              {heroSecondary}
            </CtaAction>
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.btnArrowLight}
              as="link"
            >
              <CopyText
                copy={copy}
                inline
                value={heroPrimary}
                mutate={(c, v) => updateHero(c, "cta", v)}
              />
              <svg viewBox="0 0 20 20" width={14} height={14} fill="none" aria-hidden>
                <path
                  d="M13.05 8.13L5.87 15.3 4.69 14.13 11.87 6.95H5.55V5.29h9.17v9.17h-1.67V8.13z"
                  fill="currentColor"
                />
              </svg>
            </CtaAction>
          </div>
        </div>

        {floatCards.length > 0
          ? floatCards.map((card, i) => (
          <div
            key={i}
            className={`${styles.floatingCard} ${
              i === 0
                ? styles.floatingCard1
                : i === 1
                  ? styles.floatingCard2
                  : styles.floatingCard3
            }`}
          >
            <div className={styles.floatingTitle}>{card.label}</div>
            <div className={styles.floatingValue}>{card.value}</div>
          </div>
        ))
          : null}
        </div>
      </header>

      <section className={styles.logoStrip} aria-label="Trusted by">
        <div className={styles.logoTrack}>
          {[...marqueeItems, ...marqueeItems].map((item, i) => (
            <span key={i} className={styles.logoItem}>
              {item}
            </span>
          ))}
        </div>
      </section>

      {features.length > 0 ? (
      <section id="features" className={styles.sectionPad}>
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div {...revealProps("features-tag")} className={rv("features-tag")}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Features
              </span>
            </div>
            <div className={styles.spLg} />
            <div
              {...revealProps("features-heading")}
              className={`${styles.maxMd} ${rv("features-heading")}`}
            >
              <h2 className={styles.h2}>
                <CopyText
                  copy={copy}
                  inline
                  value={
                    problem?.heading ?? "A short description of the transformation"
                  }
                  mutate={(c, v) => updateProblem(c, "heading", v)}
                  maxLength={LIMITS.proofHeadline}
                />{" "}
                <span className={styles.opacity40}>your product delivers.</span>
              </h2>
            </div>
          </div>
          <div className={styles.sp2xl} />
          <div className={styles.aboutGrid}>
            {bento.map((item, i) => (
              <div
                key={i}
                {...revealProps(`bento-${i}`)}
                className={`${styles.card} ${styles[CARD_VARIANTS[i]]} ${rv(`bento-${i}`)}`}
              >
                <div>
                  <CopyText
                    copy={copy}
                    as="p"
                    className={styles.cardLabel}
                    value={features[i]?.title ?? item.label}
                    mutate={(c, v) => updateFeature(c, i, "title", v)}
                    maxLength={LIMITS.featureTitle}
                  />
                  <div className={styles.spXs} />
                  {item.metric ? (
                    <div className={styles.bigNum}>{item.metric}</div>
                  ) : null}
                </div>
                <div className={styles.spSm} />
                <CopyText
                  copy={copy}
                  as="p"
                  className={styles.cardBody}
                  value={features[i]?.description ?? item.body}
                  mutate={(c, v) => updateFeature(c, i, "description", v)}
                  maxLength={LIMITS.cardBody}
                  multiline
                />
              </div>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      {benefits.length > 0 ? (
      <section
        id="benefits"
        className={`${styles.sectionPad} ${styles.sectionWhite}`}
      >
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div {...revealProps("benefits-tag")} className={rv("benefits-tag")}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Benefits
              </span>
            </div>
            <div className={styles.spSm} />
            <h2
              {...revealProps("benefits-heading")}
              className={`${styles.h2} ${styles.maxMd} ${rv("benefits-heading")}`}
            >
              Three reasons it just works.
            </h2>
            <div className={styles.spXs} />
            <p
              {...revealProps("benefits-sub")}
              className={`${styles.textSecondary} ${styles.maxSm} ${rv("benefits-sub")}`}
            >
              <CopyText
                copy={copy}
                inline
                value={
                  problem?.body ??
                  "A short description of what makes your product different."
                }
                mutate={(c, v) => updateProblem(c, "body", v)}
                multiline
              />
            </p>
          </div>
          <div className={styles.spLg} />
          <div className={styles.servicesGrid}>
            {benefits.map((b, i) => (
              <div
                key={i}
                {...revealProps(`benefit-${i}`)}
                className={`${styles.serviceCard} ${rv(`benefit-${i}`)}`}
              >
                <div>
                  <div className={styles.serviceIcon}>{i + 1}</div>
                  <div className={styles.spMd} />
                  <CopyText
                    copy={copy}
                    as="h3"
                    className={styles.h3}
                    value={b.title}
                    mutate={(c, v) => updateFeature(c, i, "title", v)}
                    maxLength={LIMITS.featureTitle}
                  />
                  <div className={styles.spXs} />
                  <CopyText
                    copy={copy}
                    as="p"
                    className={styles.textSecondary}
                    style={{ fontSize: "0.875rem" }}
                    value={b.description}
                    mutate={(c, v) => updateFeature(c, i, "description", v)}
                    maxLength={LIMITS.featureBody}
                    multiline
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      {outcomes.length > 0 ? (
      <section id="outcome" className={styles.sectionPad}>
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div {...revealProps("outcome-tag")} className={rv("outcome-tag")}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Outcome
              </span>
            </div>
            <div className={styles.spLg} />
            <div
              {...revealProps("outcome-heading")}
              className={`${styles.maxMd} ${rv("outcome-heading")}`}
            >
              <CopyText
                copy={copy}
                as="h2"
                className={styles.h2}
                value={proof?.headline ?? "Where your product delivers value"}
                mutate={updateProofHeadline}
                maxLength={LIMITS.proofHeadline}
              />
            </div>
          </div>
          <div className={styles.sp2xl} />
          <div className={styles.aboutGrid}>
            {outcomes.map((o, i) => (
              <div
                key={i}
                {...revealProps(`outcome-${i}`)}
                className={`${styles.card} ${styles.cardDefault} ${rv(`outcome-${i}`)}`}
              >
                <CopyText
                  copy={copy}
                  as="h3"
                  className={styles.h3}
                  value={o.title}
                  mutate={(c, v) => updateFeature(c, i, "title", v)}
                  maxLength={LIMITS.featureTitle}
                />
                <div className={styles.spXs} />
                <CopyText
                  copy={copy}
                  as="p"
                  className={styles.cardBody}
                  value={o.description}
                  mutate={(c, v) => updateFeature(c, i, "description", v)}
                  maxLength={LIMITS.cardBody}
                  multiline
                />
              </div>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      {showPricing ? (
      <section
        id="pricing"
        className={`${styles.sectionPad} ${styles.sectionWhite}`}
      >
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div {...revealProps("pricing-tag")} className={rv("pricing-tag")}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Pricing
              </span>
            </div>
            <div className={styles.spLg} />
            <h2
              {...revealProps("pricing-heading")}
              className={`${styles.h2} ${styles.maxMd} ${rv("pricing-heading")}`}
            >
              Plans that fit how you work.
            </h2>
          </div>
          <div className={styles.sp2xl} />
          <div className={styles.servicesGrid}>
            {pricingPlans.map((plan, i) => (
              <div
                key={plan.name}
                {...revealProps(`pricing-${plan.name}`)}
                className={`${styles.serviceCard} ${rv(`pricing-${plan.name}`)}`}
              >
                <div>
                  <h3 className={styles.h3}>{plan.name}</h3>
                  <div className={styles.spSm} />
                  <div className={styles.bigNum}>
                    {plan.price}
                    {plan.period ? (
                      <span className={styles.textSecondary} style={{ fontSize: "0.875rem" }}>
                        {` /${plan.period}`}
                      </span>
                    ) : null}
                  </div>
                  <div className={styles.spSm} />
                  {plan.description ? (
                    <p className={styles.textSecondary} style={{ fontSize: "0.875rem" }}>
                      {plan.description}
                    </p>
                  ) : null}
                </div>
                <CtaAction
                  config={ctaConfig}
                  scrollTarget={scrollTarget}
                  className={plan.featured || i === 1 ? styles.btnNav : styles.btnOutline}
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

      <section id="cta" className={`${styles.sectionPad} ${styles.ctaWrap}`}>
        <div
          {...revealProps("cta")}
          className={`${styles.ctaSection} ${rv("cta")}`}
        >
          <CopyText
            copy={copy}
            as="h2"
            value={cta?.heading ?? "Stop reading. Start building."}
            mutate={(c, v) => updateCta(c, "heading", v)}
            maxLength={LIMITS.ctaHeading}
          />
          <CopyText
            copy={copy}
            as="p"
            className={styles.ctaSub}
            value={
              cta?.subheading ??
              "Join the waitlist for early access when we open the next cohort."
            }
            mutate={(c, v) => updateCta(c, "subheading", v)}
            maxLength={LIMITS.ctaSubheading}
            multiline
          />
          {isPublished && publicationSlug ? (
            <WaitlistForm
              slug={publicationSlug}
              buttonLabel={ctaLabel}
              className={styles.ctaForm}
              inputClassName={styles.ctaInput}
              buttonClassName={styles.ctaSubmit}
            />
          ) : (
            <form className={styles.ctaForm} onSubmit={(e) => e.preventDefault()}>
              <input
                type="email"
                className={styles.ctaInput}
                placeholder="Enter your email"
                required
              />
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles.ctaSubmit}
                as="link"
              >
                <CopyText
                  copy={copy}
                  inline
                  value={ctaLabel}
                  mutate={(c, v) => updateCta(c, "button", v)}
                />
              </CtaAction>
            </form>
          )}
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={`${styles.container} ${styles.footerInner}`}>
          <span>
            &copy; {new Date().getFullYear()} {projectName}. All rights reserved.
          </span>
          <a
            href="https://fivvle.io"
            className={styles.footerBadge}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>Engineered via</span>
            <strong>Fivvle</strong>
          </a>
        </div>
      </footer>
    </div>
  );
}
