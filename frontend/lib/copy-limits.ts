/** Trim generated copy so templates stay readable and uncluttered. */

export function truncateText(text: string, max: number): string {
  const t = text.trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  const lastSpace = cut.lastIndexOf(" ");
  if (lastSpace > max * 0.55) {
    return `${cut.slice(0, lastSpace).trim()}…`;
  }
  return `${cut.trim()}…`;
}

/** Template display cap — used only when explicitly opting into truncation. */
export function displayText(
  text: string,
  max: number,
  options?: { forEditor?: boolean; truncate?: boolean },
): string {
  const t = text.trim();
  if (options?.forEditor || options?.truncate !== true) return t;
  return truncateText(t, max);
}

export const LIMITS = {
  headline: 88,
  subheadline: 140,
  featureTitle: 52,
  featureBody: 110,
  cardBody: 95,
  proofHeadline: 72,
  ctaHeading: 64,
  ctaSubheading: 120,
  marqueeItem: 22,
  floatLabel: 22,
  floatValue: 14,
} as const;

/** Pull a short stat token from proof text (e.g. "4,200+", "$99", "99.9%"). */
export function extractShortStat(text: string): string | null {
  const patterns = [
    /\$[\d,.]+[KMB]?/i,
    /\d[\d,.]*%\+?/,
    /\d[\d,.]*[kKmMbB]\+?/,
    /\d[\d,.]+\+/,
    /\d{1,3}(?:,\d{3})+/,
    /\d+(?:\.\d+)?/,
  ];
  for (const re of patterns) {
    const m = text.match(re);
    if (m && m[0].length <= LIMITS.floatValue) {
      return m[0];
    }
  }
  return null;
}
