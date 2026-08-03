"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getCanvasLayout,
  upsertCanvasLayout,
  type CanvasLayoutInput,
} from "@/lib/experiment-api";
import type { CanvasNodeId, NodePosition } from "@/lib/types";
import { DEFAULT_POSITIONS } from "../canvas-helpers";

export type CanvasViewport = { x: number; y: number; zoom: number };

type PositionsState = Partial<Record<CanvasNodeId, NodePosition>> &
  typeof DEFAULT_POSITIONS;

type CanvasState = {
  positions: PositionsState;
  viewport: CanvasViewport | null;
};

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

function viewportFromLayout(data: {
  viewport_x?: number | null;
  viewport_y?: number | null;
  viewport_zoom?: number | null;
}): CanvasViewport | null {
  if (
    data.viewport_x == null ||
    data.viewport_y == null ||
    data.viewport_zoom == null
  ) {
    return null;
  }
  return {
    x: data.viewport_x,
    y: data.viewport_y,
    zoom: data.viewport_zoom,
  };
}

export function useCanvasLayout(experimentId: string) {
  const [state, setState] = useState<CanvasState>({
    positions: DEFAULT_POSITIONS,
    viewport: null,
  });
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const mountedRef = useRef(true);
  const stateRef = useRef(state);
  stateRef.current = state;

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
        // Keep every key from the API (including spark-expanded) — no ID filtering.
        setState({
          positions: { ...DEFAULT_POSITIONS, ...data.node_positions },
          viewport: viewportFromLayout(data),
        });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ positions: DEFAULT_POSITIONS, viewport: null });
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const saveLayout = useCallback(
    async (next: CanvasState) => {
      setSaving(true);
      try {
        const payload: CanvasLayoutInput = {
          node_positions: next.positions as Record<CanvasNodeId, NodePosition>,
          viewport_x: next.viewport?.x ?? null,
          viewport_y: next.viewport?.y ?? null,
          viewport_zoom: next.viewport?.zoom ?? null,
        };
        await upsertCanvasLayout(experimentId, payload);
      } catch {
        // Layout save is best-effort; local state still applies if the API is unreachable.
      } finally {
        if (mountedRef.current) setSaving(false);
      }
    },
    [experimentId],
  );

  // Debounce layout network writes (positions + viewport from onMoveEnd).
  const debouncedSave = useMemo(
    () =>
      debounce(() => {
        void saveLayout(stateRef.current);
      }, 500),
    [saveLayout],
  );

  const updatePosition = useCallback(
    (nodeId: CanvasNodeId, pos: NodePosition) => {
      // Prefer stateRef so a prior onMoveEnd viewport isn't clobbered by stale React state.
      const next = {
        ...stateRef.current,
        positions: { ...stateRef.current.positions, [nodeId]: pos },
      };
      stateRef.current = next;
      setState(next);
      debouncedSave();
    },
    [debouncedSave],
  );

  /**
   * Persist viewport from onMoveEnd. Writes stateRef + debounced network save only —
   * does NOT setState (avoids React re-render storms; RF wheel zoom fires onMoveEnd
   * repeatedly between scroll ticks).
   */
  const updateViewport = useCallback(
    (viewport: CanvasViewport) => {
      stateRef.current = { ...stateRef.current, viewport };
      debouncedSave();
    },
    [debouncedSave],
  );

  const resetLayout = useCallback(async () => {
    const next: CanvasState = {
      positions: DEFAULT_POSITIONS,
      viewport: null,
    };
    stateRef.current = next;
    setState(next);
    await saveLayout(next);
  }, [saveLayout]);

  return {
    positions: state.positions,
    /** Hydrated from API on load; updated on move end (not mid-pan). */
    viewport: state.viewport,
    loaded,
    saving,
    setPositions: (positions: PositionsState) =>
      setState((prev) => {
        const next = { ...prev, positions };
        stateRef.current = next;
        return next;
      }),
    updatePosition,
    updateViewport,
    resetLayout,
  };
}
