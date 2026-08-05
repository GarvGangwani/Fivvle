"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { ExperimentAttachment } from "@/lib/types";
import {
  ORIGIN_INK,
  ORIGIN_THEME_TOKENS,
  type OriginArtifactTheme,
} from "./origin-artifact-themes";
import {
  formatCaptureDateTime,
  originVersionLabel,
} from "./origin-artifact-utils";
import { OriginAttachmentChips } from "./OriginAttachmentChips";

/** Founder seal asset — near-black brand mark, theme-invariant. */
export const ORIGIN_SEAL_SRC = "/origin-seal.png";

/** Reference mockup is 1330x800; every value below is a % of card width. */
/** Canvas render: 30% smaller than the original 560px eval size. */
const CARD_WIDTH = 392;
const CARD_ASPECT = 1.66;
const CARD_HEIGHT = CARD_WIDTH / CARD_ASPECT;

/** %W -> px */
const w = (pct: number) => (CARD_WIDTH * pct) / 100;

const PAD_X = w(5.3);
const PAD_TOP = w(5.3);
const PAD_BOTTOM = w(4);
const BODY_FONT = w(2.7);
const BODY_LINE_HEIGHT = 1.55;
/** Narrowed so the text still clears the seal. */
const BODY_MAX_WIDTH = w(55.5);
const BODY_LINES = 5;
const SEAL_SIZE = w(31.231);

/** Inter's average advance is ~0.5em; enough to place the 5-line cut. */
const CHARS_PER_LINE = Math.floor(BODY_MAX_WIDTH / (BODY_FONT * 0.5));

type Props = {
  rawIdea: string;
  captureDate: string;
  versionTag: string;
  attachments: ExperimentAttachment[];
  theme: OriginArtifactTheme;
};

function wrapLines(text: string, charsPerLine: number): string[] {
  const out: string[] = [];
  for (const para of text.split(/\n/)) {
    const words = para.trim().split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      out.push("");
      continue;
    }
    let current = "";
    for (const word of words) {
      const next = current ? `${current} ${word}` : word;
      if (next.length <= charsPerLine) {
        current = next;
      } else {
        if (current) out.push(current);
        current = word;
      }
    }
    if (current) out.push(current);
  }
  return out;
}

/** Cut to exactly `maxLines` and append a literal "..." (not a CSS ellipsis). */
function clampToLines(
  text: string,
  charsPerLine: number,
  maxLines: number,
): string {
  const lines = wrapLines(text, charsPerLine);
  if (lines.length <= maxLines) return text;

  const kept = lines.slice(0, maxLines);
  let last = kept[maxLines - 1] ?? "";
  while (last.length + 3 > charsPerLine && last.includes(" ")) {
    last = last.slice(0, last.lastIndexOf(" "));
  }
  kept[maxLines - 1] = `${last.replace(/[\s,;:.]+$/, "")}...`;
  return kept.join(" ");
}

/**
 * Provenance Origin Artifact — raw idea + attachments only.
 * No product name, no polished one-liner (those live on the shell node).
 */
export function OriginProvenanceCard({
  rawIdea,
  captureDate,
  versionTag,
  attachments,
  theme,
}: Props) {
  const tokens = ORIGIN_THEME_TOKENS[theme];
  const [expanded, setExpanded] = useState(false);

  const idea = rawIdea.trim() || "No idea captured yet.";
  const clamped = clampToLines(idea, CHARS_PER_LINE, BODY_LINES);

  return (
    <>
      <div
        className="relative box-border flex flex-col overflow-visible"
        style={{
          width: CARD_WIDTH,
          height: CARD_HEIGHT,
          backgroundColor: tokens.tint,
          border: `2px solid ${ORIGIN_INK}`,
          borderRadius: w(1.2),
          boxShadow: `${w(0.9)}px ${w(0.9)}px 0 0 ${ORIGIN_INK}`,
          paddingLeft: PAD_X,
          paddingRight: PAD_X,
          paddingTop: PAD_TOP,
          paddingBottom: PAD_BOTTOM,
        }}
      >
        {/* Seal — 31.2%W, top-right at the padding line, never themed */}
        <img
          src={ORIGIN_SEAL_SRC}
          alt=""
          aria-hidden
          draggable={false}
          className="pointer-events-none absolute select-none"
          style={{
            width: SEAL_SIZE,
            height: SEAL_SIZE,
            right: PAD_X,
            top: w(4),
            opacity: 0.9,
            objectFit: "contain",
          }}
        />

        {/* Eyebrow — flex wrapper avoids the inline-block baseline gap */}
        <p style={{ margin: 0, display: "flex", flexShrink: 0 }}>
          <span
            className="inline-block font-mono uppercase"
            style={{
              backgroundColor: tokens.highlight,
              color: ORIGIN_INK,
              fontSize: w(2.1),
              fontWeight: 600,
              letterSpacing: "0.12em",
              lineHeight: 1,
              padding: `${w(0.9)}px ${w(1.5)}px`,
              borderRadius: 0,
            }}
          >
            ORIGINAL IDEA · {versionTag}
          </span>
        </p>

        {/* Raw idea, verbatim — left column only, never under the seal */}
        <p
          style={{
            margin: 0,
            marginTop: w(4.5),
            maxWidth: BODY_MAX_WIDTH,
            fontFamily: 'var(--font-sans, "Inter"), system-ui, sans-serif',
            fontSize: BODY_FONT,
            lineHeight: BODY_LINE_HEIGHT,
            fontWeight: 400,
            color: ORIGIN_INK,
            maxHeight: BODY_FONT * BODY_LINE_HEIGHT * BODY_LINES,
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          {clamped}
        </p>

        <button
          type="button"
          className="nodrag nopan self-start font-mono uppercase hover:underline"
          style={{
            marginTop: w(3.4),
            fontSize: w(1.9),
            fontWeight: 600,
            letterSpacing: "0.1em",
            lineHeight: 1,
            color: tokens.link,
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            flexShrink: 0,
          }}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(true);
          }}
          onPointerDown={(e) => e.stopPropagation()}
        >
          VIEW ORIGINAL<span style={{ marginLeft: w(0.6) }}>→</span>
        </button>

        {/* Absorbs slack so the 1.66 ratio holds and short ideas leave no dead space */}
        <div style={{ flex: 1, minHeight: 0 }} aria-hidden />

        {/* Dashed divider — full inner width */}
        <div
          aria-hidden
          style={{
            height: 2,
            flexShrink: 0,
            opacity: 0.85,
            backgroundImage: `repeating-linear-gradient(to right, ${ORIGIN_INK} 0 ${w(
              0.75,
            )}px, transparent ${w(0.75)}px ${w(1.35)}px)`,
          }}
        />

        {/* Footer */}
        <div
          className="flex items-center"
          style={{ marginTop: w(3.4), flexShrink: 0 }}
        >
          <div className="flex flex-col" style={{ gap: w(0.8) }}>
            <span
              className="font-mono uppercase"
              style={{
                fontSize: w(1.6),
                letterSpacing: "0.1em",
                color: ORIGIN_INK,
                lineHeight: 1,
              }}
            >
              CAPTURED ON
            </span>
            <span
              className="font-mono uppercase"
              style={{
                fontSize: w(2),
                fontWeight: 600,
                color: ORIGIN_INK,
                lineHeight: 1,
              }}
            >
              {captureDate}
            </span>
          </div>

          {attachments.length > 0 ? (
            <>
              <div
                aria-hidden
                style={{
                  marginLeft: w(4),
                  width: 2,
                  height: w(2) + w(1.6) + w(0.8),
                  backgroundColor: ORIGIN_INK,
                }}
              />
              <div style={{ marginLeft: w(3) }}>
                <OriginAttachmentChips
                  attachments={attachments}
                  tokens={tokens}
                  cardWidth={CARD_WIDTH}
                />
              </div>
            </>
          ) : null}
        </div>
      </div>

      {expanded ? (
        <OriginRawIdeaOverlay
          idea={idea}
          accent={tokens.highlight}
          onClose={() => setExpanded(false)}
        />
      ) : null}
    </>
  );
}

function OriginRawIdeaOverlay({
  idea,
  accent,
  onClose,
}: {
  idea: string;
  accent: string;
  onClose: () => void;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="nodrag nopan fixed inset-0 z-[80] flex items-center justify-center bg-black/40 p-6"
      role="dialog"
      aria-modal="true"
      aria-label="Original idea"
      onClick={(e) => {
        e.stopPropagation();
        onClose();
      }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div
        className="max-h-[80vh] w-full max-w-xl overflow-hidden border-2 border-border-master bg-surface-card shadow-brutal-lg"
        style={{ borderRadius: 8 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b-2 border-border-master px-4 py-3">
          <span
            className="font-mono uppercase"
            style={{
              backgroundColor: accent,
              color: ORIGIN_INK,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.12em",
              padding: "4px 8px",
            }}
          >
            ORIGINAL IDEA · FULL
          </span>
          <button
            type="button"
            className="font-mono text-[11px] font-bold uppercase tracking-widest text-ink-primary hover:underline"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-5 py-4">
          <p
            className="whitespace-pre-wrap text-ink-primary"
            style={{
              fontFamily: 'var(--font-sans, "Inter"), system-ui, sans-serif',
              fontSize: 16,
              lineHeight: 1.6,
            }}
          >
            {idea}
          </p>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function buildProvenanceProps(
  experiment: {
    original_idea?: string | null;
    original_idea_captured_at?: string | null;
  },
  attachments: ExperimentAttachment[],
  theme: OriginArtifactTheme,
): Props {
  return {
    rawIdea: experiment.original_idea ?? "",
    captureDate: formatCaptureDateTime(experiment.original_idea_captured_at),
    versionTag: originVersionLabel(),
    attachments,
    theme,
  };
}
