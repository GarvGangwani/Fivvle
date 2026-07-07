import type { BackgroundStyle, SpacingScale } from "@/lib/landing-page-v2-types";
import styles from "./runtime-v2.module.css";

const SPACING_MAP: Record<SpacingScale, string> = {
  xs: "1.5rem",
  s: "2.5rem",
  m: "3.5rem",
  l: "5rem",
  xl: "6.5rem",
  "2xl": "8rem",
};

export function spacingStyle(scale: SpacingScale): React.CSSProperties {
  return {
    paddingTop: SPACING_MAP[scale],
    paddingBottom: SPACING_MAP[scale],
  } as React.CSSProperties;
}

export function backgroundClass(bg: BackgroundStyle): string {
  switch (bg) {
    case "surface":
      return styles.bgSurface ?? "";
    case "dark_gradient":
      return styles.bgDarkGradient ?? "";
    case "accent_soft":
      return styles.bgAccentSoft ?? "";
    case "full_bleed_dark":
      return styles.bgFullBleedDark ?? "";
    case "muted":
      return styles.bgMuted ?? "";
    default:
      return "";
  }
}

export function alignmentClass(align: "left" | "center" | "right"): string {
  if (align === "center") return styles.alignCenter ?? "";
  if (align === "right") return styles.alignRight ?? "";
  return styles.alignLeft ?? "";
}

export function animationClass(animation: string): string {
  switch (animation) {
    case "fade":
      return styles.animFade ?? "";
    case "fade_up":
      return styles.animFadeUp ?? "";
    case "slide_in":
      return styles.animSlideIn ?? "";
    case "subtle_scale":
      return styles.animSubtleScale ?? "";
    default:
      return "";
  }
}

export function splitReverse(variant: string): boolean {
  return (
    variant === "split_right" ||
    variant === "editorial_right" ||
    variant === "image_first"
  );
}

export function isSplitVariant(variant: string): boolean {
  return (
    variant === "split_left" ||
    variant === "split_right" ||
    variant === "editorial_left" ||
    variant === "editorial_right" ||
    variant === "product_first" ||
    variant === "image_first" ||
    variant === "asymmetric"
  );
}

export function isCenteredVariant(variant: string): boolean {
  return (
    variant === "centered" ||
    variant === "minimal" ||
    variant === "cinematic" ||
    variant === "stacked"
  );
}
