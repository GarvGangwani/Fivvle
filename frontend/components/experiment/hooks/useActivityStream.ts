"use client";

import { useEffect, useState } from "react";
import { getActivity } from "@/lib/experiment-api";
import type { ActivityItem } from "@/lib/types";

export function useActivityStream(experimentId: string, limit = 30) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (document.visibilityState === "hidden") return;
      try {
        const next = await getActivity(experimentId, limit);
        if (!cancelled) setItems(next);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    const interval = window.setInterval(() => void load(), 10_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void load();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [experimentId, limit]);

  return { items, loading };
}
