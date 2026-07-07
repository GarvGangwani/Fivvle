"use client";

import { Suspense } from "react";
import { WaitlistForm } from "@/components/published/WaitlistForm";
import type { ComponentPlanSpec } from "@/lib/landing-page-v2-types";
import {
  ComparisonBlock,
  PhoneMockup,
  StatGrid,
  VisualBlock,
} from "./primitives/VisualPrimitives";
import {
  alignmentClass,
  animationClass,
  backgroundClass,
  isCenteredVariant,
  isSplitVariant,
  spacingStyle,
  splitReverse,
} from "./spacingScale";
import styles from "./runtime-v2.module.css";

interface ComponentRendererProps {
  plan: ComponentPlanSpec;
  resolvedAssets: Record<string, string>;
  assetAlts: Record<string, string>;
  publicationSlug?: string | null;
  pageGoal: "waitlist" | "interest" | "contact";
}

function CopyBlock({
  plan,
  tag: Tag = "h2",
}: {
  plan: ComponentPlanSpec;
  tag?: "h1" | "h2";
}) {
  const align = alignmentClass(plan.headline_alignment);
  const isHero = plan.component === "HeroSection";
  return (
    <div className={align}>
      {plan.headline && (
        <Tag
          className={`${isHero ? styles.headline : styles.sectionHeadline} ${
            plan.variant === "cinematic" ? styles.headlineCinematic : ""
          }`}
        >
          {plan.headline}
        </Tag>
      )}
      {plan.subheadline && <p className={styles.subheadline}>{plan.subheadline}</p>}
      {plan.body && <p className={styles.body}>{plan.body}</p>}
    </div>
  );
}

function ItemCards({ plan }: { plan: ComponentPlanSpec }) {
  if (!plan.items.length) return null;
  const isGrid =
    plan.component === "FeatureGrid" ||
    plan.component === "FAQ" ||
    plan.variant === "grid";
  return (
    <div className={isGrid ? `${styles.grid} ${styles.gridCols2}` : styles.stack}>
      {plan.items.map((item, i) => (
        <div key={i} className={styles.card}>
          {item.title && <div className={styles.cardTitle}>{item.title}</div>}
          {item.value && <div className={styles.metricValue}>{item.value}</div>}
          {item.label && <div className={styles.metricLabel}>{item.label}</div>}
          {item.body && <div className={styles.cardBody}>{item.body}</div>}
        </div>
      ))}
    </div>
  );
}

function LockedWaitlist({
  slug,
  label,
}: {
  slug: string;
  label: string;
}) {
  return (
    <div className={styles.waitlistWrap} id="lp-runtime-waitlist">
      <Suspense fallback={null}>
        <WaitlistForm
          slug={slug}
          buttonLabel={label}
          className={styles.waitlistForm}
          inputClassName={styles.waitlistInput}
          buttonClassName={styles.waitlistButton}
          metaClassName={styles.waitlistMeta}
        />
      </Suspense>
    </div>
  );
}

/** Deterministic renderer — executes ComponentPlanSpec only; never guesses layout. */
export function ComponentRenderer({
  plan,
  resolvedAssets,
  assetAlts,
  publicationSlug,
  pageGoal,
}: ComponentRendererProps) {
  const assetKey = plan.visual_asset_key ?? undefined;
  const imageUrl = assetKey ? resolvedAssets[assetKey] : undefined;
  const alt = assetKey ? (assetAlts[assetKey] ?? "Visual") : "Visual";

  if (plan.component === "FooterSection") {
    return (
      <footer className={styles.footer}>
        {plan.headline ?? plan.body ?? "Built with Fivvle"}
      </footer>
    );
  }

  if (plan.component === "CtaSection") {
    const showWaitlist = pageGoal === "waitlist" && Boolean(publicationSlug);
    return (
      <section
        id={plan.id}
        className={`${styles.section} ${backgroundClass(plan.background)} ${styles.ctaSection} ${animationClass(plan.animation)}`}
        style={spacingStyle(plan.spacing)}
      >
        <div className={`${styles.sectionInner} ${styles.centered}`}>
          <CopyBlock plan={plan} />
          {showWaitlist && publicationSlug ? (
            <LockedWaitlist
              slug={publicationSlug}
              label={plan.cta_label ?? "Join the waitlist"}
            />
          ) : (
            plan.cta_label && (
              <a className={styles.ctaButton} href="#lp-runtime-waitlist">
                {plan.cta_label}
              </a>
            )
          )}
        </div>
      </section>
    );
  }

  const visualNode =
    plan.component === "PhoneMockup" || plan.visual === "phone_mockup" ? (
      <PhoneMockup imageUrl={imageUrl} alt={alt} />
    ) : plan.component === "Statistics" || plan.component === "TrustSection" ? (
      <StatGrid items={plan.items} />
    ) : plan.component === "ProblemComparison" ||
      plan.component === "ComparisonCards" ||
      plan.component === "BeforeAfter" ? (
      <ComparisonBlock items={plan.items} />
    ) : (
      <VisualBlock visualType={plan.visual} imageUrl={imageUrl} alt={alt} />
    );

  const copyNode = (
    <>
      <CopyBlock plan={plan} tag={plan.component === "HeroSection" ? "h1" : "h2"} />
      {plan.component !== "Statistics" &&
        plan.component !== "ProblemComparison" &&
        plan.component !== "ComparisonCards" &&
        plan.component !== "BeforeAfter" && <ItemCards plan={plan} />}
    </>
  );

  const centered = isCenteredVariant(plan.variant);
  const split = isSplitVariant(plan.variant) && plan.visual !== "none";
  const reverse = splitReverse(plan.variant);

  if (split && plan.visual !== "none") {
    return (
      <section
        id={plan.id}
        className={`${styles.section} ${backgroundClass(plan.background)} ${animationClass(plan.animation)}`}
        style={spacingStyle(plan.spacing)}
      >
        <div className={`${styles.sectionInner} ${styles.split}`}>
          {reverse ? (
            <>
              {copyNode}
              {visualNode}
            </>
          ) : (
            <>
              {visualNode}
              {copyNode}
            </>
          )}
        </div>
      </section>
    );
  }

  return (
    <section
      id={plan.id}
      className={`${styles.section} ${backgroundClass(plan.background)} ${animationClass(plan.animation)}`}
      style={spacingStyle(plan.spacing)}
    >
      <div className={`${styles.sectionInner} ${centered ? styles.centered : ""}`}>
        {plan.component === "HeroSection" || plan.variant === "product_first" ? (
          <>
            {copyNode}
            {plan.visual !== "none" && visualNode}
          </>
        ) : (
          <>
            {plan.visual !== "none" && visualNode}
            {copyNode}
          </>
        )}
      </div>
    </section>
  );
}
