/**
 * Pending evidence-editor focus for master-rail citation / navigate clicks.
 * Taken once when EvidenceStagePanel is ready; subscribers re-run when a new
 * pending anchor is set while the panel is already open.
 */
import type { RefCitation } from "@/lib/types";

let pending: RefCitation | null = null;
const listeners = new Set<() => void>();

export function setPendingEvidenceFocus(anchor: RefCitation | null): void {
  pending = anchor;
  listeners.forEach((listener) => listener());
}

export function takePendingEvidenceFocus(): RefCitation | null {
  const value = pending;
  pending = null;
  return value;
}

export function subscribePendingEvidenceFocus(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
