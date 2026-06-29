"use client";

import { useEffect } from "react";
import type { TemplateProps } from "./template-shared";
import { mergeFaq, splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import {
  updateComparisonCompetitor,
  updateCta,
  updateFaqItem,
  updateFeature,
  updateHero,
  updateProblem,
} from "@/lib/copy-mutations";
import { CopyText } from "./CopyText";
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
  const hero = copy.hero;
  const problem = copy.problem;
  const features = copy.features ?? [];
  const comparison = copy.comparison;
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const headline = splitHeadline(hero?.headline ?? projectName);
  const words = (hero?.headline ?? projectName).trim().split(/\s+/);

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
      data-theme={colorMode}
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
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.navCta}
            >
              <CopyText
                copy={copy}
                inline
                value={hero?.cta ?? "Get started"}
                mutate={(c, v) => updateHero(c, "cta", v)}
              />{" "}
              →
            </CtaAction>
            </div>
          </div>
        </div>
      </nav>

      {hero && (
        <header className={styles.hero}>
          <div className={styles.heroBg} aria-hidden />
          <div className={`${styles.wrap} ${styles.heroInner}`}>
            <CopyText
              copy={copy}
              as="h1"
              className={styles.heroTitle}
              value={hero?.headline ?? projectName}
              mutate={(c, v) => updateHero(c, "headline", v)}
              multiline
            />
            <CopyText
              copy={copy}
              as="p"
              className={styles.heroSub}
              value={hero.subheadline}
              mutate={(c, v) => updateHero(c, "subheadline", v)}
              multiline
            />
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.heroCta}
            >
              <CopyText
                copy={copy}
                inline
                value={hero.cta}
                mutate={(c, v) => updateHero(c, "cta", v)}
              />{" "}
              →
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
                <CopyText
                  copy={copy}
                  as="h3"
                  value={comparison?.competitor_name ?? "The old way"}
                  mutate={updateComparisonCompetitor}
                />
                <CopyText
                  copy={copy}
                  as="p"
                  value={problem.body}
                  mutate={(c, v) => updateProblem(c, "body", v)}
                  multiline
                />
              </div>
              <div className={`${styles.valueCol} ${styles.after}`}>
                <span className={`${styles.valueTag} ${styles.tagAfter}`}>
                  After
                </span>
                <h3>
                  <CopyText
                    copy={copy}
                    inline
                    value={problem.heading}
                    mutate={(c, v) => updateProblem(c, "heading", v)}
                  />{" "}
                  <span style={{ color: "var(--accent)" }}>Solved.</span>
                </h3>
                <CopyText
                  copy={copy}
                  as="p"
                  value={hero?.subheadline ?? problem.body}
                  mutate={(c, v) => updateHero(c, "subheadline", v)}
                  multiline
                />
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
                    <CopyText
                      copy={copy}
                      as="h4"
                      value={f.title}
                      mutate={(c, v) => updateFeature(c, i, "title", v)}
                    />
                    <CopyText
                      copy={copy}
                      as="p"
                      value={f.description}
                      mutate={(c, v) => updateFeature(c, i, "description", v)}
                      multiline
                    />
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {faq.length > 0 && (
        <section className={styles.faq}>
          <div className={styles.wrap}>
            <h2 className={styles.faqHead}>Questions, answered.</h2>
            {faq.map((item, i) => (
              <details key={i} className={styles.faqItem} open={i === 0}>
                <summary className={styles.faqQ}>
                  <CopyText
                    copy={copy}
                    inline
                    value={item.question}
                    mutate={(c, v) => updateFaqItem(c, i, "question", v)}
                  />
                </summary>
                <CopyText
                  copy={copy}
                  as="p"
                  className={styles.faqA}
                  value={item.answer}
                  mutate={(c, v) => updateFaqItem(c, i, "answer", v)}
                  multiline
                />
              </details>
            ))}
          </div>
        </section>
      )}

      {cta && (
        <section className={styles.cta} id="cta">
          <div className={styles.wrap}>
            <CopyText
              copy={copy}
              as="h2"
              value={cta.heading}
              mutate={(c, v) => updateCta(c, "heading", v)}
            />
            <CopyText
              copy={copy}
              as="p"
              value={cta.subheading}
              mutate={(c, v) => updateCta(c, "subheading", v)}
              multiline
            />
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
                <CopyText
                  copy={copy}
                  inline
                  value={cta.button}
                  mutate={(c, v) => updateCta(c, "button", v)}
                />{" "}
                →
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
