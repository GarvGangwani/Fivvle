"use client";

import { useEffect } from "react";
import type { TemplateProps } from "./template-shared";
import { mergeFaq, splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import {
  updateCta,
  updateFaqItem,
  updateFeature,
  updateHero,
  updateProblem,
} from "@/lib/copy-mutations";
import { CopyText } from "./CopyText";
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
  const hero = copy.hero;
  const problem = copy.problem;
  const features = copy.features ?? [];
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const headline = splitHeadline(hero?.headline ?? projectName);

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
      data-theme={colorMode}
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
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={styles.navCta}
            >
              <CopyText
                copy={copy}
                inline
                value={hero?.cta ?? "Sign in"}
                mutate={(c, v) => updateHero(c, "cta", v)}
              />
            </CtaAction>
          </div>
        </nav>

        {hero && (
          <section className={styles.hero}>
            <CopyText
              copy={copy}
              as="h1"
              className={styles.heroTitle}
              value={hero.headline}
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
              className={styles.heroBtn}
            >
              <CopyText
                copy={copy}
                inline
                value={hero.cta}
                mutate={(c, v) => updateHero(c, "cta", v)}
              />{" "}
              →
            </CtaAction>
          </section>
        )}

        {problem && (
          <section className={styles.statement}>
            <div className={styles.eyebrow}>The problem</div>
            <p className={styles.statementText}>
              <CopyText
                copy={copy}
                inline
                value={problem.heading}
                mutate={(c, v) => updateProblem(c, "heading", v)}
              />
              .{" "}
              <span className={styles.quiet}>
                <CopyText
                  copy={copy}
                  inline
                  value={problem.body}
                  mutate={(c, v) => updateProblem(c, "body", v)}
                  multiline
                />
              </span>
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
                  <span className={styles.italic}>
                    <CopyText
                      copy={copy}
                      inline
                      value={f.title}
                      mutate={(c, v) => updateFeature(c, i, "title", v)}
                    />
                  </span>
                </h3>
                <CopyText
                  copy={copy}
                  as="p"
                  className={styles.featureDesc}
                  value={f.description}
                  mutate={(c, v) => updateFeature(c, i, "description", v)}
                  multiline
                />
              </article>
            ))}
          </section>
        )}

        {faq.length > 0 && (
          <section className={styles.faq}>
            <h2 className={styles.faqHead}>
              Common <span className={styles.italic}>questions.</span>
            </h2>
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
          </section>
        )}

        {cta && (
          <section className={styles.final} id="cta">
            <CopyText
              copy={copy}
              as="h2"
              value={cta.heading}
              mutate={(c, v) => updateCta(c, "heading", v)}
              multiline
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
                metaClassName={styles.quiet}
              />
            ) : (
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles.heroBtn}
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
