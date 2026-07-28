/**
 * Shared brutalist badge class strings for confidence and recommendation.
 * Sourced from SignalInsightReport — keep mappings in sync with Signal north star.
 */

/**
 * Confidence is information. Maps high→success, medium→warning, low→ink —
 * same triad as legacy `fv-confidence-*`, expressed with semantic tokens.
 */
export function confidenceBadgeClass(
  confidence: "high" | "medium" | "low" | string,
): string {
  switch (confidence) {
    case "high":
      return "border-status-success text-status-success";
    case "medium":
      return "border-border-master bg-brutalist-yellow text-ink-primary";
    case "low":
      // Full ink weight — low confidence must not read as muted/minor.
      return "border-border-master bg-surface-elevated text-ink-primary";
    default:
      return "border-border-master bg-surface-elevated text-ink-primary";
  }
}

/**
 * Preserves the legacy proceed/iterate/pivot/kill color meaning using semantic
 * status tokens (success / warning / critical) — not a new palette.
 */
export function recommendationBadgeClass(
  recommendation: "proceed" | "iterate" | "pivot" | "kill" | string,
): string {
  switch (recommendation) {
    case "proceed":
      return "border-status-success bg-surface-elevated text-status-success";
    case "iterate":
      return "border-border-master bg-brutalist-yellow text-ink-primary";
    case "pivot":
    case "kill":
      return "border-status-critical bg-surface-elevated text-status-critical";
    default:
      return "border-border-master bg-surface-elevated text-ink-tertiary";
  }
}
