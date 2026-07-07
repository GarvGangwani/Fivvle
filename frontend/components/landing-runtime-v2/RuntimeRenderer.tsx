"use client";

import type { CSSProperties, RefObject } from "react";
import type { LandingPageV2Spec } from "@/lib/landing-page-v2-types";
import { isRuntimeSpecV4 } from "@/lib/landing-page-v2-types";
import { ComponentRenderer } from "./ComponentRenderer";
import { RuntimeAnalytics } from "./RuntimeAnalytics";
import { buildRuntimeThemeStyle } from "./themeTokens";
import styles from "./runtime-v2.module.css";

interface RuntimeRendererProps {
  spec: LandingPageV2Spec | unknown;
  resolvedAssets?: Record<string, string>;
  publicationSlug?: string | null;
  trackAnalytics?: boolean;
  rootRef?: RefObject<HTMLDivElement | null>;
}

export function RuntimeRenderer({
  spec,
  resolvedAssets = {},
  publicationSlug,
  trackAnalytics = false,
  rootRef,
}: RuntimeRendererProps) {
  if (!isRuntimeSpecV4(spec)) {
    return (
      <div className={styles.legacyNotice}>
        <p>This page uses an older runtime spec. Regenerate to use the new pipeline.</p>
      </div>
    );
  }

  const themeStyle = buildRuntimeThemeStyle(spec) as CSSProperties;
  const assetAlts = Object.fromEntries(
    spec.asset_refs.map((ref) => [ref.asset_key, ref.alt]),
  );

  return (
    <div
      ref={rootRef}
      className={styles.root}
      style={themeStyle}
      data-runtime-export-root
    >
      {trackAnalytics && publicationSlug && (
        <RuntimeAnalytics slug={publicationSlug} enabled />
      )}

      {spec.components.map((plan) => (
        <ComponentRenderer
          key={plan.id}
          plan={plan}
          resolvedAssets={resolvedAssets}
          assetAlts={assetAlts}
          publicationSlug={publicationSlug}
          pageGoal={spec.page_goal}
        />
      ))}
    </div>
  );
}
