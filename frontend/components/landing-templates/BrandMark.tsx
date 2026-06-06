"use client";

import type { ResolvedBranding } from "@/lib/branding";
import { projectInitials } from "@/lib/branding";
import styles from "./brand-mark.module.css";

export type BrandMarkVariant =
  | "dark-premium"
  | "bold-v1"
  | "minimal-v3"
  | "editorial-saas"
  | "aether";

interface BrandMarkProps {
  branding: ResolvedBranding;
  projectName: string;
  variant: BrandMarkVariant;
  /** dark-premium splits first word / rest */
  showSplitName?: boolean;
  className?: string;
  href?: string;
}

export function BrandMark({
  branding,
  projectName,
  variant,
  showSplitName = variant === "dark-premium",
  className,
  href = "#top",
}: BrandMarkProps) {
  const initials = projectInitials(projectName);
  const parts = projectName.trim().split(/\s+/);
  const first = parts[0] ?? projectName;
  const rest = parts.slice(1).join(" ") || (variant === "dark-premium" ? "premium" : "");

  const mark = (() => {
    if (branding.icon_mode === "url" && branding.logo_url) {
      return (
        <span className={`${styles.mark} ${styles.markImage}`}>
          <img src={branding.logo_url} alt="" />
        </span>
      );
    }
    if (branding.icon_mode === "emoji" && branding.logo_emoji) {
      return (
        <span className={`${styles.mark} ${styles.markEmoji}`} aria-hidden>
          {branding.logo_emoji}
        </span>
      );
    }
    if (branding.icon_mode === "mark" && variant === "bold-v1") {
      return <span className={`${styles.mark} ${styles.markDecor}`} aria-hidden />;
    }
    return (
      <span className={`${styles.mark} ${styles.markInitials}`} aria-hidden>
        {initials}
      </span>
    );
  })();

  const name = showSplitName ? (
    <>
      {first}
      {rest ? <span className={styles.nameAccent}> {rest}</span> : null}
    </>
  ) : (
    <span className={styles.nameSingle}>
      {projectName}
      {variant === "minimal-v3" && (
        <span className={styles.nameAccent} style={{ color: "var(--accent)" }}>
          *
        </span>
      )}
    </span>
  );

  const Tag = href ? "a" : "div";

  return (
    <Tag
      href={href}
      className={`${styles.wrap} ${className ?? ""}`}
      data-brand-variant={variant}
      aria-label={branding.logo_alt}
    >
      {mark}
      <span className={styles.nameBlock}>{name}</span>
    </Tag>
  );
}
