/**
 * Pending evidence-editor focus for master-rail citation / navigate clicks.
 * Taken once when EvidenceStagePanel mounts or becomes ready.
 */
import type { RefCitation } from "@/lib/types";

let pending: RefCitation | null = null;

export function setPendingEvidenceFocus(anchor: RefCitation | null): void {
  pending = anchor;
}

export function takePendingEvidenceFocus(): RefCitation | null {
  const value = pending;
  pending = null;
  return value;
}
