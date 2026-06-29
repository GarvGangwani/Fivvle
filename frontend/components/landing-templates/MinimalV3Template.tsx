"use client";

import { useEffect, useState } from "react";
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
import styles from "./minimal-v3.module.css";
import base from "./template-base.module.css";

const FONTS =
  "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,500;12..96,600;12..96,700&family=Hanken+Grotesk:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap";

const LABELS = ["a.", "b.", "c.", "d.", "e.", "f."];

export function MinimalV3Template({
  copy,
  projectName,
  colorMode = "light",
  cssVarStyle,
  isPublished,
  ctaConfig,
  publicationSlug,
  scrollTarget = "#try",
  branding,
}: TemplateProps) {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const hero = copy.hero;
  const problem = copy.problem;
  const features = copy.features ?? [];
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const headline = splitHeadline(hero?.headline ?? projectName);

  useEffect(() => {
    const id = "fivvle-minimal-v3-fonts";
    if (!document.getElementById(id)) {
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = FONTS;
      document.head.appendChild(link);
    }
  }, []);

  const brandName = projectName.trim() || "Product";

  return (
    <div
      className={`${styles.root} ${base.root}`}
      data-theme={colorMode}
      style={cssVarStyle}
    >
      <header className={styles.header}>
        <div className={styles.outer}>
          <div className={styles.headerRow}>
            <span className={styles.rail} style={{ paddingTop: 0 }}>
              §
            </span>
            <BrandMark
              branding={branding}
              projectName={projectName}
              variant="minimal-v3"
              showSplitName={false}
              className={styles.brand}
              href="#top"
            />
            <div className={styles.hdrTools}>
              <CtaAction
                config={ctaConfig}
                scrollTarget={scrollTarget}
                className={styles.navCta}
                as="link"
              >
                <CopyText
                  copy={copy}
                  inline
                  value={hero?.cta ?? "Try it"}
                  mutate={(c, v) => updateHero(c, "cta", v)}
                />
              </CtaAction>
            </div>
          </div>
        </div>
      </header>

      <main id="top">
        {hero && (
          <section className={styles.section}>
            <div className={styles.outer}>
              <div className={styles.grid}>
                <aside className={styles.rail}>
                  <span className={styles.n}>01</span>
                  <br />
                  Hero
                </aside>
                <div className={styles.body}>
                  <div className={styles.eyebrow}>
                    <span className={styles.eyebrowSym}>§</span> Private beta
                  </div>
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
                  <div className={styles.ctaArea}>
                    <CtaAction
                      config={ctaConfig}
                      scrollTarget={scrollTarget}
                      className={styles.cta}
                    >
                      <CopyText
                        copy={copy}
                        inline
                        value={hero.cta}
                        mutate={(c, v) => updateHero(c, "cta", v)}
                      />
                      <span className={styles.ctaArr}>→</span>
                    </CtaAction>
                  </div>
                </div>
                <aside className={styles.margin} />
              </div>
            </div>
          </section>
        )}

        {problem && (
          <section className={styles.section} id="premise">
            <div className={styles.outer}>
              <div className={styles.grid}>
                <aside className={styles.rail}>
                  <span className={styles.n}>02</span>
                  <br />
                  Premise
                </aside>
                <div className={styles.body}>
                  <div className={styles.eyebrow}>
                    <span className={styles.eyebrowSym}>§</span> The premise
                  </div>
                  <div className={styles.prose}>
                    <p>
                      <span className={styles.hl}>
                        <CopyText
                          copy={copy}
                          inline
                          value={problem.heading}
                          mutate={(c, v) => updateProblem(c, "heading", v)}
                        />
                      </span>{" "}
                      <CopyText
                        copy={copy}
                        inline
                        value={problem.body}
                        mutate={(c, v) => updateProblem(c, "body", v)}
                        multiline
                      />
                    </p>
                  </div>
                </div>
                <aside className={styles.margin} />
              </div>
            </div>
          </section>
        )}

        {features.length > 0 && (
          <section className={styles.section} id="inside">
            <div className={styles.outer}>
              <div className={styles.grid}>
                <aside className={styles.rail}>
                  <span className={styles.n}>03</span>
                  <br />
                  Inside
                </aside>
                <div className={styles.body}>
                  <div className={styles.eyebrow}>
                    <span className={styles.eyebrowSym}>§</span> What&apos;s inside
                  </div>
                  <ol className={styles.featList}>
                    {features.map((f, i) => (
                      <li key={i}>
                        <div className={styles.featRow}>
                          <span className={styles.featNum}>
                            {LABELS[i] ?? `${i + 1}.`}
                          </span>
                          <CopyText
                            copy={copy}
                            as="h3"
                            className={styles.featTtl}
                            value={f.title}
                            mutate={(c, v) => updateFeature(c, i, "title", v)}
                          />
                          <span className={styles.featNum}>+</span>
                        </div>
                        <CopyText
                          copy={copy}
                          as="p"
                          className={styles.featDesc}
                          value={f.description}
                          mutate={(c, v) => updateFeature(c, i, "description", v)}
                          multiline
                        />
                      </li>
                    ))}
                  </ol>
                </div>
                <aside className={styles.margin} />
              </div>
            </div>
          </section>
        )}

        {faq.length > 0 && (
          <section className={styles.section} id="faq">
            <div className={styles.outer}>
              <div className={styles.grid}>
                <aside className={styles.rail}>
                  <span className={styles.n}>04</span>
                  <br />
                  FAQ
                </aside>
                <div className={styles.body}>
                  <div className={styles.eyebrow}>
                    <span className={styles.eyebrowSym}>§</span> Questions
                  </div>
                  {faq.map((item, i) => (
                    <div key={i} className={styles.faqItem}>
                      <button
                        type="button"
                        className={`${styles.faqQ} ${openFaq === i ? styles.faqQOpen : ""}`}
                        aria-expanded={openFaq === i}
                        onClick={() => setOpenFaq(openFaq === i ? null : i)}
                      >
                        <CopyText
                          copy={copy}
                          inline
                          value={item.question}
                          mutate={(c, v) => updateFaqItem(c, i, "question", v)}
                        />
                        <span>{openFaq === i ? "−" : "+"}</span>
                      </button>
                      {openFaq === i && (
                        <CopyText
                          copy={copy}
                          as="p"
                          className={styles.faqA}
                          value={item.answer}
                          mutate={(c, v) => updateFaqItem(c, i, "answer", v)}
                          multiline
                        />
                      )}
                    </div>
                  ))}
                </div>
                <aside className={styles.margin} />
              </div>
            </div>
          </section>
        )}

        {cta && (
          <section className={styles.ctaSection} id="try">
            <div className={styles.outer}>
              <div className={styles.grid}>
                <aside className={styles.rail}>
                  <span className={styles.n}>05</span>
                  <br />
                  Try it
                </aside>
                <div className={styles.body}>
                  <CopyText
                    copy={copy}
                    as="h2"
                    className={styles.ctaTitle}
                    value={cta.heading}
                    mutate={(c, v) => updateCta(c, "heading", v)}
                    multiline
                  />
                  <CopyText
                    copy={copy}
                    as="p"
                    className={styles.ctaSub}
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
                      wrapperClassName={styles.signupWrap}
                      className={styles.signupPill}
                      inputClassName={styles.signupInput}
                      buttonClassName={styles.signupButton}
                      metaClassName={styles.formMeta}
                      metaOutsideForm
                    />
                  ) : (
                    <div className={styles.signupWrap}>
                      <form
                        className={styles.signupPill}
                        onSubmit={(e) => e.preventDefault()}
                      >
                        <input
                          className={styles.signupInput}
                          type="email"
                          placeholder="you@company.com"
                          readOnly
                          aria-label="Email"
                        />
                        <button type="submit" className={styles.signupButton}>
                          <CopyText
                            copy={copy}
                            inline
                            value={cta.button}
                            mutate={(c, v) => updateCta(c, "button", v)}
                          />
                        </button>
                      </form>
                      <p className={styles.formMeta}>
                        No spam · Unsubscribe anytime
                      </p>
                    </div>
                  )}
                </div>
                <aside className={styles.margin} />
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className={styles.footer}>
        <div className={styles.outer}>
          <div className={styles.footerRow}>
            <span className={styles.rail} style={{ paddingTop: 0 }}>
              § End.
            </span>
            <div className={styles.footerMeta}>
              <span className={styles.k}>© {new Date().getFullYear()} {brandName}.</span>{" "}
              Set in Bricolage Grotesque &amp; Hanken Grotesk.
            </div>
            <span className={styles.footerMade}>
              <span className={styles.ast}>*</span> Made with Fivvle
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
