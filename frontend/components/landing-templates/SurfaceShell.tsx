"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import {
  resolveSurface,
  type PageSurface,
} from "@/lib/surface";
import { bindSmoothScrollAnchors } from "@/lib/smooth-scroll";
import type { PageJson } from "@/lib/types";
import styles from "./surface-overlay.module.css";

interface SurfaceShellProps {
  page: PageJson;
  accentColor: string;
  colorMode: "light" | "dark";
  children: ReactNode;
}

function surfaceAccentVars(accentColor: string, colorMode: "light" | "dark") {
  const ink =
    colorMode === "dark" ? "rgba(255,255,255,0.16)" : "rgba(0,0,0,0.14)";
  const inkSoft =
    colorMode === "dark" ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.07)";

  return {
    "--fv-surface-accent": accentColor,
    "--fv-surface-accent-38": `color-mix(in srgb, ${accentColor} 38%, transparent)`,
    "--fv-surface-accent-40": `color-mix(in srgb, ${accentColor} 40%, transparent)`,
    "--fv-surface-accent-42": `color-mix(in srgb, ${accentColor} 42%, transparent)`,
    "--fv-surface-accent-45": `color-mix(in srgb, ${accentColor} 45%, transparent)`,
    "--fv-surface-accent-50": `color-mix(in srgb, ${accentColor} 50%, transparent)`,
    "--fv-surface-accent-55": `color-mix(in srgb, ${accentColor} 55%, transparent)`,
    "--fv-surface-accent-60": `color-mix(in srgb, ${accentColor} 60%, transparent)`,
    "--fv-surface-accent-70": `color-mix(in srgb, ${accentColor} 70%, transparent)`,
    "--fv-surface-accent-75": `color-mix(in srgb, ${accentColor} 75%, transparent)`,
    "--fv-surface-ink": ink,
    "--fv-surface-ink-soft": inkSoft,
  } as CSSProperties;
}

export function SurfaceShell({
  page,
  accentColor,
  colorMode,
  children,
}: SurfaceShellProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const surface = resolveSurface(page);

  useEffect(() => {
    const root = contentRef.current;
    if (!root) return;
    return bindSmoothScrollAnchors(root);
  }, []);

  const shellStyle = {
    ...surfaceAccentVars(accentColor, colorMode),
    "--fv-texture-intensity": String(surface.texture_intensity / 100),
    "--fv-gradient-intensity": String(surface.gradient_intensity / 100),
    "--fv-glow-intensity": String(surface.hero_glow_intensity / 100),
    "--fv-glow-strength": `${surface.hero_glow_intensity}%`,
  } as CSSProperties;

  const glowActive = surface.hero_glow_intensity > 0;
  const textureActive = surface.texture !== "none";
  const gradientActive = surface.gradient_style !== "flat";

  return (
    <div
      className={styles.shell}
      style={shellStyle}
      data-color-mode={colorMode}
      data-surface-texture={surface.texture}
      data-surface-gradient={surface.gradient_style}
    >
      <div className={styles.content} ref={contentRef} data-fivvle-scroll-root>
        {children}
      </div>
      <div className={styles.overlayRoot} aria-hidden>
        <div
          className={styles.gradientLayer}
          data-style={surface.gradient_style}
          data-active={gradientActive ? "true" : "false"}
        />
        <div
          className={styles.glowLayer}
          data-active={glowActive ? "true" : "false"}
        />
        <div
          className={styles.textureLayer}
          data-texture={surface.texture}
          data-active={textureActive ? "true" : "false"}
        />
      </div>
    </div>
  );
}

export function mergeSurfacePatch(
  page: PageJson,
  patch: Partial<PageSurface>,
): PageJson {
  return {
    ...page,
    surface: {
      ...(page.surface ?? {}),
      ...patch,
    },
  };
}
