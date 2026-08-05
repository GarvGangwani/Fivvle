/** Shared draft-attachment helpers for chat / idea-capture UIs. */

export const MAX_DRAFT_ATTACHMENTS = 5;
export const MAX_DRAFT_ATTACHMENT_BYTES = 10 * 1024 * 1024;

export const FILE_ACCEPT =
  "image/png,image/jpeg,image/webp,application/pdf,text/plain,text/markdown,.md,.txt,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

const ACCEPTED_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "webp",
  "pdf",
  "txt",
  "md",
  "markdown",
  "docx",
]);

export type DraftAttachment = {
  localId: string;
  file: File;
  filename: string;
  previewUrl: string | null;
  status: "uploading" | "ready" | "error";
  serverId?: string;
  contentKind?: string;
  errorMessage?: string;
};

export function fileExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : "";
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isAcceptedAttachmentFile(file: File): boolean {
  const ext = fileExtension(file.name);
  if (ACCEPTED_EXTENSIONS.has(ext)) return true;
  const mime = file.type.toLowerCase();
  return (
    mime === "image/png" ||
    mime === "image/jpeg" ||
    mime === "image/webp" ||
    mime === "application/pdf" ||
    mime === "text/plain" ||
    mime === "text/markdown" ||
    mime ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  );
}

export function isImageAttachmentFile(file: File): boolean {
  if (file.type.startsWith("image/")) return true;
  return /^(png|jpe?g|webp)$/i.test(fileExtension(file.name));
}

export function revokePreview(url: string | null | undefined): void {
  if (url) URL.revokeObjectURL(url);
}
