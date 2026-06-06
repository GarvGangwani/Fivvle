"use client";

import { useEffect, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { mergeFaq, splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import styles from "./dark-premium.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&family=Manrope:wght@300;400;500;600&display=swap";

export function DarkPremiumTemplate({
  copy,
  projectName,
  colorMode = "dark",
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
  const proof = copy.proof;
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const headline = splitHeadline(hero?.headline ?? projectName);

  useEffect(() => {
    setMode(colorMode);
  }, [colorMode]);

  useEffect(() => {
    const id = "fivvle-dp-fonts";
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
      <div className={styles.ambient} aria-hidden />
      <div className={styles.container}>
        <nav className={styles.nav}>
          <BrandMark
            branding={branding}
            projectName={projectName}
            variant="dark-premium"
            showSplitName
            className={styles.brand}
          />
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {!isPublished && (
              <button
                type="button"
                className={styles.navCta}
                style={{
                  background: "transparent",
                  color: "var(--text)",
                  border: "1px solid var(--line-strong)",
                  padding: "8px 12px",
                }}
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
              {hero?.cta ?? "Sign in"}
            </CtaAction>
          </div>
        </nav>

        {hero && (
          <section className={styles.hero}>
            <h1 className={styles.heroTitle}>
              {headline.main}
              {headline.accent && (
                <>
                  <br />
                  <span className={styles.italic}>{headline.accent}</span>
                </>
              )}
            </h1>
            <p className={styles.heroSub}>{hero.subheadline}</p>
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.heroBtn}
            >
              {hero.cta} →
            </CtaAction>
          </section>
        )}

        {problem && (
          <section className={styles.statement}>
            <div className={styles.eyebrow}>The problem</div>
            <p className={styles.statementText}>
              {problem.heading}.{" "}
              <span className={styles.quiet}>{problem.body}</span>
            </p>
          </section>
        )}

        {features.length > 0 && (
          <section className={styles.features}>
            <h2 className={styles.featuresHead}>
              The <span className={styles.italic}>essentials,</span>
              <br />
              nothing else.
            </h2>
            {features.map((f, i) => (
              <article key={i} className={styles.featureRow}>
                <h3>
                  <span className={styles.italic}>{f.title}</span>
                </h3>
                <p className={styles.featureDesc}>{f.description}</p>
              </article>
            ))}
          </section>
        )}

        {proof && (proof.elements?.length ?? 0) > 0 && (
          <section className={styles.proof}>
            <h2 className={styles.proofTitle}>{proof.headline}</h2>
            <ul className={styles.proofList}>
              {(proof.elements ?? []).map((el, i) => (
                <li key={i}>{el}</li>
              ))}
            </ul>
          </section>
        )}

        {faq.length > 0 && (
          <section className={styles.faq}>
            <h2 className={styles.faqHead}>
              Common <span className={styles.italic}>questions.</span>
            </h2>
            {faq.map((item, i) => (
              <details key={i} className={styles.faqItem} open={i === 0}>
                <summary className={styles.faqQ}>{item.question}</summary>
                <p className={styles.faqA}>{item.answer}</p>
              </details>
            ))}
          </section>
        )}

        {cta && (
          <section className={styles.final} id="cta">
            <h2>
              {cta.heading.split(" ")[0] ?? "Ready"}
              <br />
              <span className={styles.italic}>
                {cta.heading.split(" ").slice(1).join(" ") || "when you are."}
              </span>
            </h2>
            <p>{cta.subheading}</p>
            {isPublished &&
            ctaConfig?.mode === "waitlist" &&
            publicationSlug ? (
              <WaitlistForm
                slug={publicationSlug}
                buttonLabel={cta.button}
                className={styles.waitlistForm}
                metaClassName={styles.quiet}
              />
            ) : (
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles.heroBtn}
              >
                {cta.button} →
              </CtaAction>
            )}
          </section>
        )}

        <footer className={styles.footer}>
          <span>© {new Date().getFullYear()} {projectName}</span>
          <span>
            Made with <span className={styles.madeWith}>◆</span> Fivvle
          </span>
        </footer>
      </div>
    </div>
  );
}
