/**
 * Helpers for idea-capture UI (dormant phases + origin attachment mapping).
 * Kept free of React so they can be unit-tested without a DOM.
 */

import type {
  AttachmentType,
  Experiment,
  ExperimentAttachment,
  OriginFrozenAttachment,
} from "@/lib/types";
import { experimentHasOriginalIdea } from "@/components/experiment/canvas-helpers";

export function mapContentKindToAttachmentType(kind: string): AttachmentType {
  const k = kind.toLowerCase();
  if (
    k.includes("image") ||
    k === "png" ||
    k === "jpeg" ||
    k === "jpg" ||
    k === "webp"
  ) {
    return "image";
  }
  if (k.includes("pdf")) return "pdf";
  if (k.includes("markdown") || k === "md") return "markdown";
  return "document";
}

export function originAttachmentsForArtifact(
  experimentId: string,
  rows: OriginFrozenAttachment[] | undefined,
): ExperimentAttachment[] {
  return (rows ?? []).map((row) => ({
    id: row.id,
    experiment_id: experimentId,
    user_id: "",
    attachment_type: mapContentKindToAttachmentType(row.content_kind),
    title: row.original_filename,
    content_text: null,
    file_url: null,
    file_mime: row.media_type,
    file_size_bytes: null,
    created_at: row.created_at,
  }));
}

export function shouldShowCaptureCard(experiment: Experiment): boolean {
  return !experimentHasOriginalIdea(experiment);
}

export function shouldShowOriginArtifact(experiment: Experiment): boolean {
  return experimentHasOriginalIdea(experiment);
}

export function canSubmitCapture(ideaText: string, uploading: boolean): boolean {
  return ideaText.trim().length > 0 && !uploading;
}
