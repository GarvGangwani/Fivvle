"use client";

import { useEffect, useRef } from "react";
import { submitPageView } from "@/lib/api";

interface RuntimeAnalyticsProps {
  slug: string;
  /** Preview mode skips beacons when slug is absent. */
  enabled?: boolean;
}

/**
 * Fires page-view beacon once on mount. Reuses Fivvle's existing analytics endpoint.
 * Scroll depth and CTA click tracking can extend here without changing the spec format.
 */
export function RuntimeAnalytics({ slug, enabled = true }: RuntimeAnalyticsProps) {
  const fired = useRef(false);

  useEffect(() => {
    if (!enabled || !slug || fired.current) return;
    fired.current = true;
    void submitPageView(slug).catch(() => {
      /* analytics must not break preview */
    });
  }, [enabled, slug]);

  return null;
}
