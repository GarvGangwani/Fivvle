"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getCanvasLayout,
  upsertCanvasLayout,
  type CanvasLayoutInput,
} from "@/lib/experiment-api";
import type { CanvasNodeId, NodePosition } from "@/lib/types";
import { DEFAULT_POSITIONS } from "../canvas-helpers";

function debounce<T extends (...args: never[]) => void>(
  fn: T,
  waitMs: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), waitMs);
  };
}

export function useCanvasLayout(experimentId: string) {
  const [positions, setPositions] =
    useState<Partial<Record<CanvasNodeId, NodePosition>> & typeof DEFAULT_POSITIONS>(
      DEFAULT_POSITIONS,
    );
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoaded(false);
    void getCanvasLayout(experimentId)
      .then((data) => {
        if (cancelled) return;
        setPositions({ ...DEFAULT_POSITIONS, ...data.node_positions });
      })
      .catch(() => {
        if (cancelled) return;
        setPositions(DEFAULT_POSITIONS);
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const saveLayout = useCallback(
    async (
      nextPositions: Partial<Record<CanvasNodeId, NodePosition>> &
        typeof DEFAULT_POSITIONS,
    ) => {
      setSaving(true);
      try {
        const payload: CanvasLayoutInput = {
          node_positions: nextPositions as Record<CanvasNodeId, NodePosition>,
        };
        await upsertCanvasLayout(experimentId, payload);
      } catch {
        // Layout save is best-effort; local positions still apply if the API is unreachable.
      } finally {
        if (mountedRef.current) setSaving(false);
      }
    },
    [experimentId],
  );

  const debouncedSave = useMemo(() => debounce(saveLayout, 500), [saveLayout]);

  const updatePosition = useCallback(
    (nodeId: CanvasNodeId, pos: NodePosition) => {
      setPositions((prev) => {
        const next = { ...prev, [nodeId]: pos };
        debouncedSave(next);
        return next;
      });
    },
    [debouncedSave],
  );

  const resetLayout = useCallback(async () => {
    setPositions(DEFAULT_POSITIONS);
    await saveLayout(DEFAULT_POSITIONS);
  }, [saveLayout]);

  return { positions, loaded, saving, setPositions, updatePosition, resetLayout };
}
