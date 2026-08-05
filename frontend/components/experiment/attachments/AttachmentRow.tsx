"use client";

import { useState } from "react";
import type { ExperimentAttachment } from "@/lib/types";

type Props = {
  attachment: ExperimentAttachment;
  onDelete: () => void;
};

export function AttachmentRow({ attachment, onDelete }: Props) {
  const subtitle = getSubtitle(attachment);

  return (
    <li className="rounded-md border-2 border-border-master bg-surface-card h-16 flex items-center gap-3 px-3 nodrag">
      <AttachmentThumb attachment={attachment} />
      <div className="flex-1 min-w-0">
        <AttachmentTitle attachment={attachment} />
        {subtitle ? (
          <p className="font-mono text-mono-sm text-ink-tertiary truncate">
            {subtitle}
          </p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={onDelete}
        aria-label="Delete attachment"
        className="p-1 hover:bg-surface-elevated shrink-0"
      >
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
          delete
        </span>
      </button>
    </li>
  );
}

function AttachmentThumb({ attachment }: { attachment: ExperimentAttachment }) {
  const [imgError, setImgError] = useState(false);

  if (
    attachment.attachment_type === "image" &&
    attachment.file_url &&
    !imgError
  ) {
    return (
      <div className="w-12 h-12 rounded-sm border-2 border-border-master bg-surface-elevated overflow-hidden shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={attachment.file_url}
          alt={attachment.title}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
          loading="lazy"
        />
      </div>
    );
  }

  const iconName = getIconForType(attachment.attachment_type);
  const iconColor = getIconColorForType(attachment.attachment_type);

  return (
    <div className="w-12 h-12 rounded-sm border-2 border-border-master bg-surface-elevated flex items-center justify-center shrink-0">
      <span
        className={`material-symbols-outlined ${iconColor}`}
        style={{ fontSize: 24 }}
        aria-hidden="true"
      >
        {iconName}
      </span>
    </div>
  );
}

function AttachmentTitle({ attachment }: { attachment: ExperimentAttachment }) {
  const isClickable =
    attachment.attachment_type === "link" ||
    attachment.attachment_type === "image" ||
    attachment.attachment_type === "pdf" ||
    attachment.attachment_type === "document";

  if (isClickable && attachment.file_url) {
    return (
      <a
        href={attachment.file_url}
        target="_blank"
        rel="noopener noreferrer"
        className="font-body text-body-sm font-bold hover:underline block truncate"
      >
        {attachment.title}
      </a>
    );
  }

  return (
    <p className="font-body text-body-sm font-bold truncate">{attachment.title}</p>
  );
}

function getIconForType(type: string): string {
  switch (type) {
    case "pdf":
      return "picture_as_pdf";
    case "document":
      return "description";
    case "markdown":
      return "notes";
    case "pasted_text":
      return "content_paste";
    case "link":
      return "link";
    case "image":
      return "image";
    default:
      return "attachment";
  }
}

function getIconColorForType(type: string): string {
  switch (type) {
    case "link":
      return "text-accent";
    case "pdf":
      return "text-status-critical";
    case "image":
      return "text-ink-tertiary";
    default:
      return "text-ink-primary";
  }
}

function getSubtitle(attachment: ExperimentAttachment): string | null {
  if (attachment.attachment_type === "link" && attachment.file_url) {
    return getHostname(attachment.file_url);
  }
  if (attachment.file_size_bytes) {
    return formatFileSize(attachment.file_size_bytes);
  }
  if (attachment.attachment_type === "pasted_text" && attachment.content_text) {
    const preview = attachment.content_text
      .slice(0, 60)
      .replace(/\s+/g, " ")
      .trim();
    return preview.length < attachment.content_text.length
      ? `${preview}...`
      : preview;
  }
  return null;
}

function getHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
