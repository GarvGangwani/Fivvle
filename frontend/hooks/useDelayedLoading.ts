"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Keeps a loading UI visible for at least `minDuration` ms so fast fetches
 * do not flash content in and out.
 */
export function useDelayedLoading(
  loading: boolean,
  minDuration = 400,
): boolean {
  const [showLoading, setShowLoading] = useState(loading);
  const startTime = useRef<number | null>(null);

  useEffect(() => {
    if (loading) {
      startTime.current = Date.now();
      setShowLoading(true);
      return;
    }

    if (startTime.current == null) {
      setShowLoading(false);
      return;
    }

    const elapsed = Date.now() - startTime.current;
    const remaining = Math.max(0, minDuration - elapsed);
    const timer = window.setTimeout(() => {
      setShowLoading(false);
      startTime.current = null;
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [loading, minDuration]);

  return showLoading;
}
