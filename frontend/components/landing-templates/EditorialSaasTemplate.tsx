"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { mergeFaq, splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import styles from "./editorial-saas.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap";

const GRAD_PAIRS = [
  ["var(--grad-mint-1)", "var(--grad-mint-2)"],
  ["var(--grad-gold-1)", "var(--grad-gold-2)"],
  ["var(--grad-rose-1)", "var(--grad-rose-2)"],
] as const;

const EYEBROWS = ["CAPABILITY ONE", "CAPABILITY TWO", "CAPABILITY THREE"];

function initialsFrom(text: string): string {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "FL";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export function EditorialSaasTemplate({
  copy,
  projectName,
  colorMode = "light",
  cssVarStyle,
  isPublished,
  ctaConfig,
  publicationSlug,
  scrollTarget = "#join",
  branding,
}: TemplateProps) {
  const [mode, setMode] = useState(colorMode);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [quoteIndex, setQuoteIndex] = useState(0);
  const [activeSlide, setActiveSlide] = useState(0);
  const featuresRef = useRef<HTMLElement>(null);

  const hero = copy.hero;
  const features = (copy.features ?? []).slice(0, 3);
  const featureSlides =
    features.length > 0
      ? features
      : [
          {
            title: "Feature headline here.",
            description:
              "A short description of the feature and the outcome it delivers.",
          },
        ];
  const proof = copy.proof;
  const proofElements = (proof?.elements ?? []).map((el) =>
    typeof el === "string" ? el : String(el),
  );
  const quotes =
    proofElements.length > 0
      ? proofElements.map((q, i) => ({
          quote: q.startsWith("“") ? q : `“${q}”`,
          name: proof?.headline?.split(/[—–-]/)[0]?.trim() || "Customer",
          role: proof?.headline || "Verified user",
          av: initialsFrom(proof?.headline ?? `User ${i + 1}`),
        }))
      : [
          {
            quote:
              "“A short, punchy quote from a happy customer that reads like a tweet.”",
            name: "First Last",
            role: "Title, Company",
            av: "FL",
          },
        ];
  const workflowSteps = featureSlides.slice(0, 3).map((f, i) => ({
    num: i + 1,
    title: f.title,
    body: f.description,
  }));
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const headline = splitHeadline(hero?.headline ?? projectName);

  useEffect(() => {
    setMode(colorMode);
  }, [colorMode]);

  useEffect(() => {
    const id = "fivvle-editorial-saas-fonts";
    if (!document.getElementById(id)) {
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = FONTS;
      document.head.appendChild(link);
    }
  }, []);

  const handleFeaturesScroll = useCallback(() => {
    const section = featuresRef.current;
    if (!section || window.innerWidth <= 960) return;

    const rect = section.getBoundingClientRect();
    const scrollableDist = rect.height - window.innerHeight;
    if (scrollableDist <= 0) return;

    const percent = Math.min(Math.max(-rect.top / scrollableDist, 0), 1);
    let index = 0;
    if (percent >= 0.66) index = 2;
    else if (percent >= 0.33) index = 1;
    setActiveSlide(index);
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", handleFeaturesScroll, { passive: true });
    window.addEventListener("resize", handleFeaturesScroll);
    handleFeaturesScroll();
    return () => {
      window.removeEventListener("scroll", handleFeaturesScroll);
      window.removeEventListener("resize", handleFeaturesScroll);
    };
  }, [handleFeaturesScroll, featureSlides.length]);

  useEffect(() => {
    const els = document.querySelectorAll(`.${styles.reveal}`);
    if (!els.length || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add(styles.revealIn);
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [faq.length, featureSlides.length]);

  const currentQuote = quotes[quoteIndex % quotes.length];

  return (
    <div
      className={`${styles.root} ${base.root}`}
      data-theme={mode}
      style={cssVarStyle}
    >
      <header className={styles.nav}>
        <div className={`${styles.wrap} ${styles.navInner}`}>
          <BrandMark
            branding={branding}
            projectName={projectName}
            variant="editorial-saas"
            showSplitName={false}
            className={styles.brand}
            href="#top"
          />
          <nav className={styles.navLinks} aria-label="Primary">
            <a href="#features">Features</a>
            <a href="#workflow">Mechanism</a>
            <a href="#testimonials">Testimonials</a>
            <a href="#faq">FAQ</a>
          </nav>
          <div className={styles.navCta}>
            {!isPublished && (
              <button
                type="button"
                className={styles.themeToggle}
                aria-label="Toggle theme"
                onClick={() => setMode((m) => (m === "dark" ? "light" : "dark"))}
              >
                <span className={styles.themeThumb}>
                  {mode === "dark" ? "☾" : "☀"}
                </span>
              </button>
            )}
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={`${styles.btn} ${styles.btnSecondary}`}
              as="link"
            >
              {hero?.cta ?? "Get started"}
            </CtaAction>
          </div>
        </div>
      </header>

      <main id="top">
        {hero && (
          <section className={styles.hero}>
            <div className={`${styles.wrap} ${styles.heroInner}`}>
              <h1 className={`${styles.display} ${styles.reveal}`}>
                {headline.main}{" "}
                {headline.accent && (
                  <span className={styles.italic}>{headline.accent}</span>
                )}
              </h1>
              <p className={`${styles.heroSub} ${styles.reveal}`}>{hero.subheadline}</p>
              <div className={`${styles.heroActions} ${styles.reveal}`}>
                <CtaAction
                  config={ctaConfig}
                  scrollTarget={scrollTarget}
                  className={`${styles.btn} ${styles.btnPrimary}`}
                >
                  {hero.cta}
                </CtaAction>
                <a className={`${styles.btn} ${styles.btnSecondary}`} href="#features">
                  See how it works
                </a>
              </div>
            </div>
            <div className={styles.heroWaves} aria-hidden>
              <svg className={`${styles.heroWave} ${styles.wave1}`} viewBox="0 0 2880 200" preserveAspectRatio="none">
                <path d="M 0 60 C 240 10, 480 110, 720 60 C 960 10, 1200 110, 1440 60 C 1680 10, 1920 110, 2160 60 C 2400 10, 2640 110, 2880 60 L 2880 200 L 0 200 Z" fill="url(#es-wave-1)" />
              </svg>
              <svg className={`${styles.heroWave} ${styles.wave2}`} viewBox="0 0 2880 200" preserveAspectRatio="none">
                <path d="M 0 80 C 300 130, 600 30, 900 80 C 1200 130, 1350 30, 1440 80 C 1740 130, 2040 30, 2340 80 C 2640 130, 2790 30, 2880 80 L 2880 200 L 0 200 Z" fill="url(#es-wave-2)" />
              </svg>
              <svg className={`${styles.heroWave} ${styles.wave3}`} viewBox="0 0 2880 200" preserveAspectRatio="none">
                <path d="M 0 100 C 360 50, 720 150, 1080 100 C 1260 70, 1380 130, 1440 100 C 1800 50, 2160 150, 2520 100 C 2700 70, 2820 130, 2880 100 L 2880 200 L 0 200 Z" fill="url(#es-wave-3)" />
              </svg>
              <svg width="0" height="0" aria-hidden>
                <defs>
                  <linearGradient id="es-wave-1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--wave-color-1)" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="var(--bg)" stopOpacity="1" />
                  </linearGradient>
                  <linearGradient id="es-wave-2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--wave-color-2)" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="var(--bg)" stopOpacity="1" />
                  </linearGradient>
                  <linearGradient id="es-wave-3" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--wave-color-3)" stopOpacity="0.15" />
                    <stop offset="100%" stopColor="var(--bg)" stopOpacity="1" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </section>
        )}

        <section className={styles.featuresSticky} id="features" ref={featuresRef}>
          <div className={styles.featuresTrack}>
            <div className={`${styles.wrap} ${styles.featuresInner}`}>
              <div className={styles.featuresLeft}>
                {featureSlides.map((feat, idx) => {
                  const [g1, g2] = GRAD_PAIRS[idx % GRAD_PAIRS.length];
                  const textClass =
                    idx === activeSlide
                      ? styles.featureTextActive
                      : idx < activeSlide
                        ? styles.featureTextPast
                        : "";
                  return (
                    <div
                      key={idx}
                      className={`${styles.featureText} ${textClass}`}
                    >
                      <div className={styles.mobileVisual}>
                        <div className={styles.gradCard} style={{ ["--g1" as string]: g1, ["--g2" as string]: g2 }}>
                          <div className={styles.gradOverlay} />
                        </div>
                      </div>
                      <span className={styles.eyebrow}>{EYEBROWS[idx] ?? `CAPABILITY ${idx + 1}`}</span>
                      <h2 className={styles.h2}>{feat.title}</h2>
                      <p className={styles.lede}>{feat.description}</p>
                      <div className={styles.featureList}>
                        <div className={`${styles.featureItem} ${styles.featureItemVisible}`}>
                          <h4 className={styles.featureItemTitle}>{feat.title}</h4>
                          <p className={styles.featureItemBody}>{feat.description}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className={styles.featuresRight}>
                <div className={styles.visualWrapper}>
                  {featureSlides.map((_, idx) => {
                    const [g1, g2] = GRAD_PAIRS[idx % GRAD_PAIRS.length];
                    const visClass =
                      idx === activeSlide
                        ? styles.featureVisualActive
                        : idx < activeSlide
                          ? styles.featureVisualPast
                          : "";
                    return (
                      <div
                        key={idx}
                        className={`${styles.featureVisual} ${visClass}`}
                      >
                        <div
                          className={styles.gradCard}
                          style={{ ["--g1" as string]: g1, ["--g2" as string]: g2 }}
                        >
                          <div className={styles.gradOverlay} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.workflow} id="workflow">
          <div className={`${styles.wrap} ${styles.workflowGrid}`}>
            <div className={styles.reveal}>
              <h2 className={styles.h2}>How the process works</h2>
              <p className={styles.lede} style={{ marginTop: 14 }}>
                {copy.problem?.body ??
                  "A simple overview of the steps involved in our workflow."}
              </p>
              <div className={styles.workflowSteps}>
                {workflowSteps.map((step) => (
                  <div
                    key={step.num}
                    className={`${styles.stepRow} ${styles.stepHighlighted}`}
                  >
                    <div className={styles.stepNum}>{step.num}</div>
                    <div>
                      <h4 className={styles.stepTitle}>{step.title}</h4>
                      <p className={styles.stepBody}>{step.body}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 40 }}>
                <CtaAction
                  config={ctaConfig}
                  scrollTarget={scrollTarget}
                  className={`${styles.btn} ${styles.btnPrimary}`}
                >
                  {hero?.cta ?? "Get started"}
                </CtaAction>
              </div>
            </div>
            <div className={styles.reveal}>
              <div className={styles.mechanismVisual}>
                <div
                  className={styles.gradCard}
                  style={{
                    ["--g1" as string]: GRAD_PAIRS[0][0],
                    ["--g2" as string]: GRAD_PAIRS[0][1],
                  }}
                >
                  <div className={styles.gradOverlay} />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.testimonial} id="testimonials">
          <div className={`${styles.wrap} ${styles.testimonialInner} ${styles.reveal}`}>
            <blockquote className={styles.testimonialQuote}>
              {currentQuote.quote}
            </blockquote>
            <div className={styles.testimonialFooter}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div className={styles.testimonialAv}>{currentQuote.av}</div>
                <div>
                  <div className={styles.testimonialName}>{currentQuote.name}</div>
                  <span className={styles.testimonialRole}>{currentQuote.role}</span>
                </div>
              </div>
              {quotes.length > 1 && (
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    className={styles.arrowBtn}
                    aria-label="Previous quote"
                    onClick={() =>
                      setQuoteIndex((i) => (i - 1 + quotes.length) % quotes.length)
                    }
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    className={styles.arrowBtn}
                    aria-label="Next quote"
                    onClick={() => setQuoteIndex((i) => (i + 1) % quotes.length)}
                  >
                    →
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>

        {faq.length > 0 && (
          <section className={styles.faqSection} id="faq">
            <div className={styles.wrap}>
              <div className={`${styles.faqHead} ${styles.reveal}`}>
                <span className={styles.eyebrow}>FAQ</span>
                <h2 className={styles.h2} style={{ marginTop: 16 }}>
                  Questions, answered.
                </h2>
              </div>
              <div className={styles.faqList}>
                {faq.map((item, i) => (
                  <div
                    key={i}
                    className={`${styles.faqItem} ${openFaq === i ? styles.faqOpen : ""} ${styles.reveal}`}
                  >
                    <button
                      type="button"
                      className={styles.faqQ}
                      aria-expanded={openFaq === i}
                      onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    >
                      <span>{item.question}</span>
                      <span className={styles.faqBtn} aria-hidden>
                        +
                      </span>
                    </button>
                    {openFaq === i && (
                      <div className={styles.faqPanel}>{item.answer}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {cta && (
          <section className={styles.cta} id="join">
            <div className={`${styles.wrap} ${styles.ctaInner} ${styles.reveal}`}>
              <h2 className={styles.ctaTitle}>{cta.heading}</h2>
              <p className={styles.lede}>{cta.subheading}</p>
              {isPublished &&
              ctaConfig?.mode === "waitlist" &&
              publicationSlug ? (
                <WaitlistForm
                  slug={publicationSlug}
                  buttonLabel={cta.button}
                  className={styles.ctaForm}
                  inputClassName={styles.ctaInput}
                  buttonClassName={`${styles.btn} ${styles.btnPrimary}`}
                />
              ) : (
                <form
                  className={styles.ctaForm}
                  onSubmit={(e) => e.preventDefault()}
                >
                  <input
                    className={styles.ctaInput}
                    type="email"
                    placeholder="founder@startup.com"
                    readOnly
                    aria-label="Email"
                  />
                  <button type="submit" className={`${styles.btn} ${styles.btnPrimary}`}>
                    {cta.button}
                  </button>
                </form>
              )}
              <p className={styles.ctaFine}>
                NO CREDIT CARD · FREE FOREVER · CANCEL ANYTIME
              </p>
            </div>
          </section>
        )}
      </main>

      <footer className={styles.foot}>
        <div className={`${styles.wrap} ${styles.footInner}`}>
          <BrandMark
            branding={branding}
            projectName={projectName}
            variant="editorial-saas"
            showSplitName={false}
            className={styles.brand}
            href="#top"
          />
          <nav className={styles.footCols} aria-label="Footer">
            <a href="#features">Features</a>
            <a href="#workflow">Mechanism</a>
            <a href="#testimonials">Testimonials</a>
            <a href="#faq">FAQ</a>
          </nav>
          <a
            className={styles.footMade}
            href="https://fivvle.io"
            target="_blank"
            rel="noopener noreferrer"
          >
            Engineered via <b>Fivvle</b>
          </a>
          <div className={styles.footCopy}>
            © {new Date().getFullYear()} {projectName}. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
