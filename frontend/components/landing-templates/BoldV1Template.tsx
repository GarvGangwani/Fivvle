"use client";

import { useEffect, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { mergeFaq, splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import styles from "./bold-v1.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap";

export function BoldV1Template({
  copy,
  projectName,
  colorMode = "light",
  cssVarStyle,
  isPublished,
  ctaConfig,
  publicationSlug,
  scrollTarget = "#cta",
  branding,
}: TemplateProps) {
  const [mode, setMode] = useState(colorMode);
  const hero = copy.hero;
  const problem = copy.problem;
  const features = copy.features ?? [];
  const comparison = copy.comparison;
  const proof = copy.proof;
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const headline = splitHeadline(hero?.headline ?? projectName);
  const words = (hero?.headline ?? projectName).trim().split(/\s+/);

  useEffect(() => {
    setMode(colorMode);
  }, [colorMode]);

  useEffect(() => {
    const id = "fivvle-bold-fonts";
    if (!document.getElementById(id)) {
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = FONTS;
      document.head.appendChild(link);
    }
  }, []);

  return (
    <div
      className={`${styles.root} ${base.root}`}
      data-theme={mode}
      style={cssVarStyle}
    >
      <nav className={styles.nav}>
        <div className={styles.wrap}>
          <div className={styles.navRow}>
            <BrandMark
              branding={branding}
              projectName={projectName}
              variant="bold-v1"
              showSplitName={false}
              className={styles.logo}
            />
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              {!isPublished && (
                <button
                  type="button"
                  className={styles.navCta}
                  onClick={() => setMode((m) => (m === "dark" ? "light" : "dark"))}
                >
                  {mode === "dark" ? "Light" : "Dark"}
                </button>
              )}
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles.navCta}
              >
                {hero?.cta ?? "Get started"}
              </CtaAction>
            </div>
          </div>
        </div>
      </nav>

      {hero && (
        <header className={styles.hero}>
          <div className={styles.heroBg} aria-hidden />
          <div className={`${styles.wrap} ${styles.heroInner}`}>
            <h1 className={styles.heroTitle}>
              {words.slice(0, 2).join(" ")}{" "}
              <span className={styles.accentWord}>
                {words.slice(2, 4).join(" ") || headline.main}
              </span>
              {words.length > 4 && (
                <>
                  <br />
                  {words.slice(4, -1).join(" ")}{" "}
                  <span className={styles.stamp}>
                    {words[words.length - 1] ?? "here."}
                  </span>
                </>
              )}
            </h1>
            <p className={styles.heroSub}>{hero.subheadline}</p>
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.heroCta}
            >
              {hero.cta} →
            </CtaAction>
          </div>
        </header>
      )}

      {problem && (
        <section className={styles.value}>
          <div className={styles.wrap}>
            <div className={styles.valueGrid}>
              <div className={styles.valueCol}>
                <span className={`${styles.valueTag} ${styles.tagBefore}`}>
                  Before
                </span>
                <h3>{comparison?.competitor_name ?? "The old way"}</h3>
                <p>{problem.body}</p>
              </div>
              <div className={`${styles.valueCol} ${styles.after}`}>
                <span className={`${styles.valueTag} ${styles.tagAfter}`}>
                  After
                </span>
                <h3>
                  {problem.heading}{" "}
                  <span style={{ color: "var(--accent)" }}>Solved.</span>
                </h3>
                <p>{hero?.subheadline ?? problem.body}</p>
              </div>
            </div>
          </div>
        </section>
      )}

      {features.length > 0 && (
        <section className={styles.features}>
          <div className={styles.wrap}>
            <h2 className={styles.featuresHead}>
              Why it just <em>works.</em>
            </h2>
            <ol className={styles.featList}>
              {features.map((f, i) => (
                <li key={i} className={styles.feat}>
                  <div className={styles.featNum}>
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className={styles.featBody}>
                    <h4>{f.title}</h4>
                    <p>{f.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {proof && (proof.elements?.length ?? 0) > 0 && (
        <section className={styles.testimonial}>
          <div className={styles.wrap}>
            <blockquote>
              “{(proof.elements ?? [])[0]}{" "}
              <span className={styles.hi}>{proof.headline}</span>”
            </blockquote>
          </div>
        </section>
      )}

      {faq.length > 0 && (
        <section className={styles.faq}>
          <div className={styles.wrap}>
            <h2 className={styles.faqHead}>Questions, answered.</h2>
            {faq.map((item, i) => (
              <details key={i} className={styles.faqItem} open={i === 0}>
                <summary className={styles.faqQ}>{item.question}</summary>
                <p className={styles.faqA}>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>
      )}

      {cta && (
        <section className={styles.cta} id="cta">
          <div className={styles.wrap}>
            <h2>{cta.heading}</h2>
            <p>{cta.subheading}</p>
            {isPublished &&
            ctaConfig?.mode === "waitlist" &&
            publicationSlug ? (
              <WaitlistForm
                slug={publicationSlug}
                buttonLabel={cta.button}
                className={styles.waitlistForm}
                metaClassName={styles.heroSub}
              />
            ) : (
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles.ctaBtn}
              >
                {cta.button} →
              </CtaAction>
            )}
          </div>
        </section>
      )}

      <footer className={styles.footer}>
        <div className={styles.wrap} style={{ display: "flex", width: "100%", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <span>© {new Date().getFullYear()} {projectName.toUpperCase()}</span>
          <span className={styles.madeWith}>MADE WITH FIVVLE</span>
        </div>
      </footer>
    </div>
  );
}
