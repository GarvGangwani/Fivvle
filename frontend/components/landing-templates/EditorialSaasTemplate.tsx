"use client";

import { useEffect, useRef, useState } from "react";
import type { TemplateProps } from "./template-shared";
import { mergeFaq, splitHeadline } from "./template-shared";
import { CtaAction } from "./CtaAction";
import { BrandMark } from "./BrandMark";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import {
  EDITORIAL_WORKFLOW_IMAGE_SLOT,
  editorialFeatureImageSlot,
  getSectionImageUrl,
} from "@/lib/section-images";
import {
  updateCta,
  updateFaqItem,
  updateFeature,
  updateHero,
  updateProblem,
} from "@/lib/copy-mutations";
import { SectionImageSlot } from "./SectionImageSlot";
import { CopyText } from "./CopyText";
import { useScrollReveal } from "./useScrollReveal";
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
  forEditor = false,
  sectionImages,
  experimentId,
  onSectionImageChange,
}: TemplateProps) {
  const imageEditable =
    forEditor && Boolean(onSectionImageChange) && Boolean(experimentId);
  const imageSlotProps = {
    editable: imageEditable,
    experimentId,
    onImageChange: onSectionImageChange,
  };
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const rootRef = useRef<HTMLDivElement>(null);

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
  const workflowSteps = featureSlides.slice(0, 3).map((f, i) => ({
    num: i + 1,
    title: f.title,
    body: f.description,
  }));
  const cta = copy.cta;
  const faq = mergeFaq(copy);
  const { revealProps, revealClass } = useScrollReveal(rootRef, [
    faq.length,
    featureSlides.length,
  ]);
  const rv = (id: string) => revealClass(id, styles.reveal, styles.revealIn);
  const headline = splitHeadline(hero?.headline ?? projectName);

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

  return (
    <div
      ref={rootRef}
      className={`${styles.root} ${base.root}`}
      data-theme={colorMode}
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
            <a href="#faq">FAQ</a>
          </nav>
          <div className={styles.navCta}>
            <CtaAction
              config={ctaConfig}
              scrollTarget={scrollTarget}
              className={`${styles.btn} ${styles.btnSecondary}`}
              as="link"
            >
              <CopyText
                copy={copy}
                inline
                value={hero?.cta ?? "Get started"}
                mutate={(c, v) => updateHero(c, "cta", v)}
              />
            </CtaAction>
          </div>
        </div>
      </header>

      <main id="top">
        {hero && (
          <section className={styles.hero}>
            <div className={`${styles.wrap} ${styles.heroInner}`}>
              <div {...revealProps("hero-title")} className={rv("hero-title")}>
                <CopyText
                  copy={copy}
                  as="h1"
                  className={styles.display}
                  value={hero.headline}
                  mutate={(c, v) => updateHero(c, "headline", v)}
                  multiline
                />
              </div>
              <div {...revealProps("hero-sub")} className={rv("hero-sub")}>
                <CopyText
                  copy={copy}
                  as="p"
                  className={styles.heroSub}
                  value={hero.subheadline}
                  mutate={(c, v) => updateHero(c, "subheadline", v)}
                  multiline
                />
              </div>
              <div
                {...revealProps("hero-actions")}
                className={`${styles.heroActions} ${rv("hero-actions")}`}
              >
                <CtaAction
                  config={ctaConfig}
                  scrollTarget={scrollTarget}
                  className={`${styles.btn} ${styles.btnPrimary}`}
                >
                  <CopyText
                    copy={copy}
                    inline
                    value={hero.cta}
                    mutate={(c, v) => updateHero(c, "cta", v)}
                  />
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

        <section className={styles.capabilities} id="features">
          <div className={styles.wrap}>
            {featureSlides.map((feat, idx) => {
              const [g1, g2] = GRAD_PAIRS[idx % GRAD_PAIRS.length];
              const reversed = idx % 2 === 1;
              return (
                <div
                  key={idx}
                  className={`${styles.capabilityRow} ${reversed ? styles.capabilityRowReverse : ""}`}
                >
                  <div className={styles.capabilityText}>
                    <span className={styles.eyebrow}>
                      {EYEBROWS[idx] ?? `CAPABILITY ${idx + 1}`}
                    </span>
                    <CopyText
                      copy={copy}
                      as="h2"
                      className={styles.h2}
                      value={feat.title}
                      mutate={(c, v) => updateFeature(c, idx, "title", v)}
                    />
                    <CopyText
                      copy={copy}
                      as="p"
                      className={styles.lede}
                      value={feat.description}
                      mutate={(c, v) => updateFeature(c, idx, "description", v)}
                      multiline
                    />
                  </div>
                  <div className={styles.capabilityVisual}>
                    <SectionImageSlot
                      slotId={editorialFeatureImageSlot(idx)}
                      imageUrl={getSectionImageUrl(
                        sectionImages,
                        editorialFeatureImageSlot(idx),
                      )}
                      fill
                      placeholderClassName={styles.gradCard}
                      placeholderStyle={{
                        ["--g1" as string]: g1,
                        ["--g2" as string]: g2,
                      }}
                      placeholderChildren={<div className={styles.gradOverlay} />}
                      alt=""
                      {...imageSlotProps}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className={styles.workflow} id="workflow">
          <div className={`${styles.wrap} ${styles.workflowGrid}`}>
            <div {...revealProps("workflow-copy")} className={rv("workflow-copy")}>
              <h2 className={styles.h2}>How the process works</h2>
              <p className={styles.lede} style={{ marginTop: 14 }}>
                <CopyText
                  copy={copy}
                  inline
                  value={
                    copy.problem?.body ??
                    "A simple overview of the steps involved in our workflow."
                  }
                  mutate={(c, v) => updateProblem(c, "body", v)}
                  multiline
                />
              </p>
              <div className={styles.workflowSteps}>
                {workflowSteps.map((step) => (
                  <div
                    key={step.num}
                    className={`${styles.stepRow} ${styles.stepHighlighted}`}
                  >
                    <div className={styles.stepNum}>{step.num}</div>
                    <div>
                      <CopyText
                        copy={copy}
                        as="h4"
                        className={styles.stepTitle}
                        value={step.title}
                        mutate={(c, v) => updateFeature(c, step.num - 1, "title", v)}
                      />
                      <CopyText
                        copy={copy}
                        as="p"
                        className={styles.stepBody}
                        value={step.body}
                        mutate={(c, v) =>
                          updateFeature(c, step.num - 1, "description", v)
                        }
                        multiline
                      />
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
            <div {...revealProps("workflow-visual")} className={rv("workflow-visual")}>
              <div className={styles.mechanismVisual}>
                <SectionImageSlot
                  slotId={EDITORIAL_WORKFLOW_IMAGE_SLOT}
                  imageUrl={getSectionImageUrl(
                    sectionImages,
                    EDITORIAL_WORKFLOW_IMAGE_SLOT,
                  )}
                  fill
                  placeholderClassName={styles.gradCard}
                  placeholderStyle={{
                    ["--g1" as string]: GRAD_PAIRS[0][0],
                    ["--g2" as string]: GRAD_PAIRS[0][1],
                  }}
                  placeholderChildren={<div className={styles.gradOverlay} />}
                  alt=""
                  {...imageSlotProps}
                />
              </div>
            </div>
          </div>
        </section>

        {faq.length > 0 && (
          <section className={styles.faqSection} id="faq">
            <div className={styles.wrap}>
              <div
                {...revealProps("faq-head")}
                className={`${styles.faqHead} ${rv("faq-head")}`}
              >
                <span className={styles.eyebrow}>FAQ</span>
                <h2 className={styles.h2} style={{ marginTop: 16 }}>
                  Questions, answered.
                </h2>
              </div>
              <div className={styles.faqList}>
                {faq.map((item, i) => (
                  <div
                    key={i}
                    {...revealProps(`faq-${i}`)}
                    className={`${styles.faqItem} ${openFaq === i ? styles.faqOpen : ""} ${rv(`faq-${i}`)}`}
                  >
                    <button
                      type="button"
                      className={styles.faqQ}
                      aria-expanded={openFaq === i}
                      onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    >
                      <CopyText
                        copy={copy}
                        inline
                        value={item.question}
                        mutate={(c, v) => updateFaqItem(c, i, "question", v)}
                      />
                      <span className={styles.faqBtn} aria-hidden>
                        +
                      </span>
                    </button>
                    {openFaq === i && (
                      <div className={styles.faqPanel}>
                        <CopyText
                          copy={copy}
                          as="div"
                          value={item.answer}
                          mutate={(c, v) => updateFaqItem(c, i, "answer", v)}
                          multiline
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {cta && (
          <section className={styles.cta} id="join">
            <div
              {...revealProps("cta")}
              className={`${styles.wrap} ${styles.ctaInner} ${rv("cta")}`}
            >
              <CopyText
                copy={copy}
                as="h2"
                className={styles.ctaTitle}
                value={cta.heading}
                mutate={(c, v) => updateCta(c, "heading", v)}
              />
              <CopyText
                copy={copy}
                as="p"
                className={styles.lede}
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
                    <CopyText
                      copy={copy}
                      inline
                      value={cta.button}
                      mutate={(c, v) => updateCta(c, "button", v)}
                    />
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
