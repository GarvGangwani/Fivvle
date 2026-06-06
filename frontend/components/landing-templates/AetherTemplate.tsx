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
  truncateText,
} from "@/lib/copy-limits";
import styles from "./aether.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap";

const CARD_VARIANTS = ["cardDefault", "cardSubtle", "cardGreen", "cardDark"] as const;
const MARQUEE_FALLBACK = [
  "BRAND ONE",
  "BRAND TWO",
  "BRAND THREE",
  "BRAND FOUR",
  "BRAND FIVE",
  "BRAND SIX",
];

const DEFAULT_BENTO = [
  { metric: "120+", label: "Metric label", body: "A short description of the feature or metric." },
  { metric: "100%", label: "Metric label", body: "“A short, punchy testimonial quote from a customer.”" },
  { metric: "520k+", label: "Metric label", body: "A short description of the feature or metric." },
  { metric: "20+", label: "Metric label", body: "A short description of the feature or metric." },
];

const DEFAULT_BENEFITS = [
  {
    title: "Feature headline here.",
    description: "A short description of the feature and the outcome it delivers.",
  },
  {
    title: "Feature headline here.",
    description: "A short description of the feature and the outcome it delivers.",
  },
  {
    title: "Feature headline here.",
    description: "A short description of the feature and the outcome it delivers.",
  },
];

const DEFAULT_OUTCOMES = [
  { title: "Benefit headline here.", description: "A short description of the benefit and outcome." },
  { title: "Benefit headline here.", description: "A short description of the benefit and outcome." },
  { title: "Benefit headline here.", description: "A short description of the benefit and outcome." },
  { title: "Benefit headline here.", description: "A short description of the benefit and outcome." },
];

const DEFAULT_FLOAT = [
  { label: "Setup time", value: "60s" },
  { label: "Active users", value: "4,200+" },
  { label: "Uptime SLA", value: "99.9%" },
];

function floatStat(
  el: unknown,
  i: number,
): { label: string; value: string } | null {
  if (typeof el === "object" && el !== null) {
    const o = el as { stat?: string; description?: string };
    const value = truncateText(String(o.stat ?? ""), LIMITS.floatValue);
    if (!value) return null;
    return {
      label: truncateText(String(o.description ?? `Metric ${i + 1}`), LIMITS.floatLabel),
      value,
    };
  }
  const s = String(el);
  const stat = extractShortStat(s);
  if (!stat) return null;
  const label = truncateText(
    s.replace(stat, "").replace(/^[\s:—–\-]+/, "").trim() || `Metric ${i + 1}`,
    LIMITS.floatLabel,
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
}: TemplateProps) {
  const [navScrolled, setNavScrolled] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const hero = copy.hero;
  const headline = splitHeadline(hero?.headline ?? projectName);
  const features = copy.features ?? [];
  const problem = copy.problem;
  const proof = copy.proof;
  const cta = copy.cta;

  const bento = DEFAULT_BENTO.map((d, i) => {
    const f = features[i];
    return {
      metric: f?.title?.match(/\d[\d,k+%.]*/)?.[0] ?? d.metric,
      label: f?.title?.replace(/\d[\d,k+%.]*/g, "").trim() || d.label,
      body: truncateText(f?.description ?? d.body, LIMITS.cardBody),
    };
  });

  const benefits =
    features.length >= 3
      ? features.slice(0, 3)
      : features.length > 0
        ? [...features, ...DEFAULT_BENEFITS].slice(0, 3)
        : DEFAULT_BENEFITS;

  const outcomes =
    features.length >= 4
      ? features.slice(0, 4).map((f) => ({
          title: f.title,
          description: f.description,
        }))
      : DEFAULT_OUTCOMES;

  const proofEls = proof?.elements ?? [];
  const extractedFloat = proofEls
    .map(floatStat)
    .filter((x): x is { label: string; value: string } => x != null)
    .slice(0, 3);
  const floatCards =
    proofEls.length === 0
      ? DEFAULT_FLOAT
      : extractedFloat.length > 0
        ? extractedFloat
        : [];

  const marqueeItems =
    proofEls.length >= 3
      ? proofEls.map((el, i) =>
          truncateText(
            typeof el === "string" ? el : `Partner ${i + 1}`,
            LIMITS.marqueeItem,
          ).toUpperCase(),
        )
      : MARQUEE_FALLBACK;

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
        rootMargin: "0px 0px -8% 0px",
        root: scrollRoot === window ? null : (scrollRoot as HTMLElement),
      },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [copy]);

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
            <a href="#features">Features</a>
            <a href="#benefits">Benefits</a>
            <a href="#outcome">Outcome</a>
            <a href="#pricing">Pricing</a>
          </div>
          <CtaAction
            config={ctaConfig}
            scrollTarget={scrollTarget}
            className={styles.btnNav}
            as="link"
          >
            {ctaLabel}
          </CtaAction>
        </div>
      </nav>

      <header className={styles.hero}>
        <canvas ref={canvasRef} className={styles.heroCanvas} aria-hidden />
        <div className={styles.heroNebula} aria-hidden />
        <div className={`${styles.container} ${styles.heroContent}`}>
          <h1 className={`${styles.heroTitle} ${styles.reveal}`}>
            {headline.main}
            {headline.accent ? (
              <>
                <br />
                <span className={styles.opacity70}>{headline.accent}</span>
              </>
            ) : null}
          </h1>
          <div className={styles.spLg} />
          <p className={`${styles.heroSub} ${styles.reveal}`}>
            {hero?.subheadline ??
              "A short description of your product and why it matters. Lead with the outcome, then earn the click."}
          </p>
          <div className={styles.spXl} />
          <div className={`${styles.heroButtons} ${styles.reveal}`}>
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
              <span>{heroPrimary}</span>
              <svg viewBox="0 0 20 20" width={14} height={14} fill="none" aria-hidden>
                <path
                  d="M13.05 8.13L5.87 15.3 4.69 14.13 11.87 6.95H5.55V5.29h9.17v9.17h-1.67V8.13z"
                  fill="currentColor"
                />
              </svg>
            </CtaAction>
          </div>
        </div>

        {floatCards.map((card, i) => (
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
        ))}
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

      <section id="features" className={styles.sectionPad}>
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div className={styles.reveal}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Features
              </span>
            </div>
            <div className={styles.spLg} />
            <div className={`${styles.reveal} ${styles.maxMd}`}>
              <h2 className={styles.h2}>
                {problem?.heading ?? "A short description of the transformation"}{" "}
                <span className={styles.opacity40}>your product delivers.</span>
              </h2>
            </div>
          </div>
          <div className={styles.sp2xl} />
          <div className={styles.aboutGrid}>
            {bento.map((item, i) => (
              <div
                key={i}
                className={`${styles.card} ${styles[CARD_VARIANTS[i]]} ${styles.reveal}`}
              >
                <div>
                  <p className={styles.cardLabel}>{item.label}</p>
                  <div className={styles.spXs} />
                  <div className={styles.bigNum}>{item.metric}</div>
                </div>
                <div className={styles.spSm} />
                <p className={styles.cardBody}>{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        id="benefits"
        className={`${styles.sectionPad} ${styles.sectionWhite}`}
      >
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div className={styles.reveal}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Benefits
              </span>
            </div>
            <div className={styles.spSm} />
            <h2 className={`${styles.h2} ${styles.reveal} ${styles.maxMd}`}>
              Three reasons it just works.
            </h2>
            <div className={styles.spXs} />
            <p className={`${styles.reveal} ${styles.textSecondary} ${styles.maxSm}`}>
              {problem?.body ??
                "A short description of what makes your product different."}
            </p>
          </div>
          <div className={styles.spLg} />
          <div className={styles.servicesGrid}>
            {benefits.map((b, i) => (
              <div key={i} className={`${styles.serviceCard} ${styles.reveal}`}>
                <div>
                  <div className={styles.serviceIcon}>{i + 1}</div>
                  <div className={styles.spMd} />
                  <h3 className={styles.h3}>{b.title}</h3>
                  <div className={styles.spXs} />
                  <p className={styles.textSecondary} style={{ fontSize: "0.875rem" }}>
                    {truncateText(b.description, LIMITS.featureBody)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="outcome" className={styles.sectionPad}>
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div className={styles.reveal}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Outcome
              </span>
            </div>
            <div className={styles.spLg} />
            <h2 className={`${styles.h2} ${styles.reveal} ${styles.maxMd}`}>
              {proof?.headline ?? "Where your product delivers value"}
            </h2>
          </div>
          <div className={styles.sp2xl} />
          <div className={styles.aboutGrid}>
            {outcomes.map((o, i) => (
              <div
                key={i}
                className={`${styles.card} ${styles.cardDefault} ${styles.reveal}`}
              >
                <h3 className={styles.h3}>{o.title}</h3>
                <div className={styles.spXs} />
                <p className={styles.cardBody}>
                  {truncateText(o.description, LIMITS.cardBody)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        id="pricing"
        className={`${styles.sectionPad} ${styles.sectionWhite}`}
      >
        <div className={styles.container}>
          <div className={styles.textCenter}>
            <div className={styles.reveal}>
              <span className={styles.tag}>
                <span className={styles.tagDot} />
                Pricing
              </span>
            </div>
            <div className={styles.spLg} />
            <h2 className={`${styles.h2} ${styles.reveal} ${styles.maxMd}`}>
              Flexible tiers built for growth.
            </h2>
          </div>
          <div className={styles.sp2xl} />
          <div className={styles.servicesGrid}>
            {["Starter", "Professional", "Enterprise"].map((tier, i) => (
              <div key={tier} className={`${styles.serviceCard} ${styles.reveal}`}>
                <div>
                  <h3 className={styles.h3}>{tier}</h3>
                  <div className={styles.spSm} />
                  <div className={styles.bigNum}>
                    {i === 2 ? "Custom" : i === 1 ? "$99" : "$29"}
                  </div>
                  <div className={styles.spSm} />
                  <p className={styles.textSecondary} style={{ fontSize: "0.875rem" }}>
                    {i === 0
                      ? "For individuals getting started."
                      : i === 1
                        ? "For growing teams that need more."
                        : "For organizations at scale."}
                  </p>
                </div>
                <CtaAction
                  config={ctaConfig}
                  scrollTarget={scrollTarget}
                  className={i === 1 ? styles.btnNav : styles.btnOutline}
                  as="link"
                >
                  {i === 2 ? "Contact Us" : ctaLabel}
                </CtaAction>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="cta" className={`${styles.sectionPad} ${styles.ctaWrap}`}>
        <div className={`${styles.ctaSection} ${styles.reveal}`}>
          <h2>{cta?.heading ?? "Stop reading. Start building."}</h2>
          <p className={styles.ctaSub}>
            {cta?.subheading ??
              "Set expectations — no credit card, free forever, cancel anytime."}
          </p>
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
                {ctaLabel}
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
