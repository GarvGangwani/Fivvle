"use client";

import type { ReactNode } from "react";
import { useState } from "react";

type Props = {
  content: string;
  createdAt: string;
  role: "user" | "assistant";
  isLatest: boolean;
  onEdit?: () => void;
  onRetry?: () => void;
  branchNavigator?: ReactNode;
};

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export function MessageActions({
  content,
  createdAt,
  role,
  isLatest,
  onEdit,
  onRetry,
  branchNavigator,
}: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard may be unavailable; ignore.
    }
  };

  return (
    <div
      className={`mt-2 flex items-center gap-3 ${
        role === "user" ? "justify-end" : "justify-start"
      }`}
    >
      <span className="font-mono text-mono-sm uppercase text-ink-tertiary">
        {formatTime(createdAt)} UTC
      </span>

      {branchNavigator}

      <button
        type="button"
        onClick={() => void handleCopy()}
        aria-label="Copy message"
        title={copied ? "Copied" : "Copy"}
        className="p-1 text-ink-tertiary hover:text-ink-primary hover:bg-surface-elevated transition-colors"
      >
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 16 }}
          aria-hidden="true"
        >
          {copied ? "check" : "content_copy"}
        </span>
      </button>

      {role === "user" && onEdit && isLatest ? (
        <button
          type="button"
          onClick={onEdit}
          aria-label="Edit message"
          title="Edit"
          className="p-1 text-ink-tertiary hover:text-ink-primary hover:bg-surface-elevated transition-colors"
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 16 }}
            aria-hidden="true"
          >
            edit
          </span>
        </button>
      ) : null}

      {onRetry && isLatest ? (
        <button
          type="button"
          onClick={onRetry}
          aria-label="Try another response"
          title="Try another response"
          className="p-1 text-ink-tertiary hover:text-ink-primary hover:bg-surface-elevated transition-colors"
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 16 }}
            aria-hidden="true"
          >
            refresh
          </span>
        </button>
      ) : null}
    </div>
  );
}
