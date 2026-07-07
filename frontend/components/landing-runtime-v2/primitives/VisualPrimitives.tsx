"use client";

import Image from "next/image";
import styles from "../runtime-v2.module.css";

export function PhoneMockup({
  imageUrl,
  alt,
  caption,
}: {
  imageUrl?: string | null;
  alt: string;
  caption?: string;
}) {
  return (
    <div className={styles.phoneMockup} aria-hidden={!imageUrl}>
      <div className={styles.phoneFrame}>
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={alt}
            width={280}
            height={560}
            className={styles.phoneScreen}
            unoptimized={imageUrl.startsWith("http://localhost")}
          />
        ) : (
          <div className={styles.phonePlaceholder}>
            <span className={styles.phonePlaceholderBar} />
            <span className={styles.phonePlaceholderBar} />
            <span className={styles.phonePlaceholderBarShort} />
          </div>
        )}
      </div>
      {caption && <p className={styles.visualCaption}>{caption}</p>}
    </div>
  );
}

export function StatGrid({
  items,
}: {
  items: { label?: string | null; value?: string | null; title?: string | null }[];
}) {
  return (
    <div className={styles.statGrid}>
      {items.map((item, i) => (
        <div key={i} className={styles.statCell}>
          <div className={styles.statValue}>{item.value ?? item.title}</div>
          <div className={styles.statLabel}>{item.label ?? ""}</div>
        </div>
      ))}
    </div>
  );
}

export function ComparisonBlock({
  items,
}: {
  items: { title?: string | null; body?: string | null }[];
}) {
  return (
    <div className={styles.comparisonRow}>
      {items.slice(0, 2).map((item, i) => (
        <div
          key={i}
          className={`${styles.comparisonCol} ${i === 1 ? styles.comparisonColHighlight : ""}`}
        >
          {item.title && <div className={styles.cardTitle}>{item.title}</div>}
          {item.body && <div className={styles.cardBody}>{item.body}</div>}
        </div>
      ))}
    </div>
  );
}

export function VisualBlock({
  visualType,
  imageUrl,
  alt,
}: {
  visualType: string;
  imageUrl?: string | null;
  alt: string;
}) {
  if (visualType === "phone_mockup") {
    return <PhoneMockup imageUrl={imageUrl} alt={alt} />;
  }
  if (imageUrl) {
    return (
      <Image
        src={imageUrl}
        alt={alt}
        width={960}
        height={540}
        className={
          visualType === "product_screenshot" || visualType === "dashboard"
            ? styles.mediaProduct
            : styles.media
        }
        unoptimized={imageUrl.startsWith("http://localhost")}
      />
    );
  }
  if (visualType === "diagram" || visualType === "chart") {
    return (
      <div className={styles.diagramPlaceholder} aria-label={alt}>
        <div className={styles.diagramBar} style={{ width: "72%" }} />
        <div className={styles.diagramBar} style={{ width: "55%" }} />
        <div className={styles.diagramBar} style={{ width: "88%" }} />
        <div className={styles.diagramBar} style={{ width: "40%" }} />
      </div>
    );
  }
  if (visualType === "animation_placeholder") {
    return <div className={styles.animationPlaceholder} aria-label={alt} />;
  }
  return null;
}
