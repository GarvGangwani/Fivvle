/** When the metrics paywall prompt should appear on the Metrics stage. */

const METRICS_STAGE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ARCHIVED",
]);

export function shouldShowMetricsAnalysisPrompt(
  experimentStatus: string,
  metricsUnlocked: boolean,
): boolean {
  if (metricsUnlocked) return false;
  return METRICS_STAGE_STATUSES.has(experimentStatus);
}
