import type { RefCitation } from "./types";

/**
 * Parse the inline citation markers the evidence-chat v3 prompt emits:
 *   - `[cite: https://a, https://b]` — external source URLs
 *   - `[ref: q3]` / `[ref: competitor:Guru]` / `[ref: section:market]` /
 *     `[ref: limitation]` — in-report anchors
 *
 * Markers are stripped from the visible text; URLs and refs are returned
 * deduped and in first-seen order. Unrecognized ref anchors are dropped
 * silently. The raw content (markers intact) is what Copy uses, so both marker
 * forms must survive there — only the rendered text is cleaned.
 */

const CITE_RE = /\[cite:\s*([^\]]*)\]/gi;
const REF_RE = /\[ref:\s*([^\]]*)\]/gi;
const MARKER_RE = /\[(?:cite|ref):\s*[^\]]*\]/gi;

const VALID_SECTIONS = new Set([
  "market",
  "competition",
  "distribution",
  "regulatory",
  "risk",
  "research",
]);
const QUESTION_RE = /^q[1-7]$/;

export interface ParsedCitations {
  cleanedText: string;
  urlCitations: string[];
  refCitations: RefCitation[];
}

/** Ordered text + marker segments for inline chip rendering (rail sub-agent). */
export type CitationToken =
  | { type: "text"; value: string }
  | { type: "marker"; marker: string };

/** Parse a single `[ref: …]` anchor body into a typed RefCitation. */
export function parseRefAnchor(raw: string): RefCitation | null {
  const anchor = raw.trim();
  if (!anchor) return null;
  const lower = anchor.toLowerCase();

  if (lower === "limitation") return { kind: "limitation", value: "limitation" };
  if (QUESTION_RE.test(lower)) return { kind: "question", value: lower };

  if (lower.startsWith("competitor:")) {
    // Preserve original casing for the competitor name (used for editor search).
    const name = anchor.slice("competitor:".length).trim();
    return name ? { kind: "competitor", value: name } : null;
  }
  if (lower.startsWith("section:")) {
    const id = lower.slice("section:".length).trim();
    return VALID_SECTIONS.has(id) ? { kind: "section", value: id } : null;
  }
  return null;
}

/**
 * Split content into text / marker tokens in document order.
 * Markers stay intact (including multi-URL `[cite: a, b]` forms).
 */
export function tokenizeCitations(content: string): CitationToken[] {
  const tokens: CitationToken[] = [];
  let lastIndex = 0;
  MARKER_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MARKER_RE.exec(content)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ type: "text", value: content.slice(lastIndex, match.index) });
    }
    tokens.push({ type: "marker", marker: match[0] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    tokens.push({ type: "text", value: content.slice(lastIndex) });
  }
  return tokens;
}

export function parseCitations(content: string): ParsedCitations {
  const urlCitations: string[] = [];
  const seenUrls = new Set<string>();
  let match: RegExpExecArray | null;

  CITE_RE.lastIndex = 0;
  while ((match = CITE_RE.exec(content)) !== null) {
    for (const raw of match[1].split(",")) {
      const url = raw.trim();
      if (url && !seenUrls.has(url)) {
        seenUrls.add(url);
        urlCitations.push(url);
      }
    }
  }

  const refCitations: RefCitation[] = [];
  const seenRefs = new Set<string>();

  REF_RE.lastIndex = 0;
  while ((match = REF_RE.exec(content)) !== null) {
    for (const raw of match[1].split(",")) {
      const ref = parseRefAnchor(raw);
      if (!ref) continue;
      const key = `${ref.kind}:${ref.value.toLowerCase()}`;
      if (!seenRefs.has(key)) {
        seenRefs.add(key);
        refCitations.push(ref);
      }
    }
  }

  const cleanedText = content
    .replace(CITE_RE, "")
    .replace(REF_RE, "")
    // Tidy up the whitespace the removed markers leave behind, per line.
    .replace(/[^\S\n]+([.,;:!?])/g, "$1")
    .replace(/[^\S\n]{2,}/g, " ")
    .replace(/[^\S\n]+$/gm, "")
    .trim();

  return { cleanedText, urlCitations, refCitations };
}
