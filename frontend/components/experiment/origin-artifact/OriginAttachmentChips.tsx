"use client";

import { FileText } from "lucide-react";
import type { ExperimentAttachment } from "@/lib/types";
import { ORIGIN_INK, type OriginArtifactThemeTokens } from "./origin-artifact-themes";

type Props = {
  attachments: ExperimentAttachment[];
  tokens: OriginArtifactThemeTokens;
  /** Card width — all chip geometry is a percentage of it. */
  cardWidth: number;
};

function isImage(att: ExperimentAttachment): boolean {
  return (
    (att.attachment_type === "image" ||
      Boolean(att.file_mime?.startsWith("image/"))) &&
    Boolean(att.file_url)
  );
}

function formatBytes(bytes: number | null | undefined): string | null {
  if (bytes == null || bytes <= 0) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function OriginAttachmentChips({
  attachments,
  tokens,
  cardWidth,
}: Props) {
  if (attachments.length === 0) return null;

  const w = (pct: number) => (cardWidth * pct) / 100;
  const thumbSide = w(4.5);

  return (
    <div
      className="nodrag nopan flex items-center"
      style={{ gap: w(2) }}
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      {attachments.slice(0, 2).map((att) => {
        const size = formatBytes(att.file_size_bytes);
        return (
          <span
            key={att.id}
            className="inline-flex items-center"
            style={{
              gap: w(1.2),
              padding: w(1.2),
              border: `2px solid ${ORIGIN_INK}`,
              borderRadius: w(0.6),
              backgroundColor: "transparent",
            }}
          >
            {isImage(att) && att.file_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={att.file_url}
                alt=""
                style={{
                  width: thumbSide,
                  height: thumbSide,
                  border: `2px solid ${tokens.link}`,
                  objectFit: "cover",
                }}
                draggable={false}
              />
            ) : (
              <span
                className="flex items-center justify-center"
                style={{
                  width: thumbSide,
                  height: thumbSide,
                  border: `2px solid ${tokens.link}`,
                }}
                aria-hidden
              >
                <FileText
                  style={{
                    width: thumbSide * 0.55,
                    height: thumbSide * 0.55,
                    color: tokens.link,
                  }}
                />
              </span>
            )}
            <span
              className="flex min-w-0 flex-col"
              style={{ gap: w(0.4) }}
            >
              <span
                className="max-w-[110px] truncate font-mono"
                style={{
                  fontSize: w(1.8),
                  fontWeight: 600,
                  color: ORIGIN_INK,
                  lineHeight: 1.1,
                }}
              >
                {att.title}
              </span>
              {size ? (
                <span
                  className="font-mono"
                  style={{
                    fontSize: w(1.6),
                    color: ORIGIN_INK,
                    opacity: 0.7,
                    lineHeight: 1.1,
                  }}
                >
                  {size}
                </span>
              ) : null}
            </span>
          </span>
        );
      })}
    </div>
  );
}
