/** Central monetization pricing — mirror of backend/app/pricing.py */

export const CREDIT_CONVERSION_RATE = 5;

export const WELCOME_COUPON_CODE = "WELCOME5";

export type ServiceKey =
  | "ideaRefinement"
  | "validationReport"
  | "landingPageGeneration"
  | "distributionCampaign"
  | "metricsAnalysis"
  | "competitorAnalysis"
  | "reportRegeneration"
  | "fullValidationFlow"
  | "insightReport";

export const SERVICE_PRICING: Record<ServiceKey, number> = {
  ideaRefinement: 5,
  validationReport: 25,
  landingPageGeneration: 15,
  distributionCampaign: 25,
  metricsAnalysis: 20,
  competitorAnalysis: 20,
  reportRegeneration: 10,
  fullValidationFlow: 50,
  insightReport: 20,
};

export const VALIDATION_PAYWALL_CREDITS = SERVICE_PRICING.fullValidationFlow;
export const METRICS_PAYWALL_CREDITS = SERVICE_PRICING.metricsAnalysis;
export const INSIGHT_PAYWALL_CREDITS = SERVICE_PRICING.insightReport;

export function formatUsdFromCredits(credits: number): string {
  const usd = credits / CREDIT_CONVERSION_RATE;
  if (usd >= 1000) {
    return `$${(usd / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  }
  if (Number.isInteger(usd)) {
    return `$${usd}`;
  }
  return `$${usd.toFixed(2)}`;
}

/** UI-only pack metadata (descriptions / popular badge). Prices come from API. */
export const PACK_UI_META: Record<
  string,
  { description: string; popular?: boolean }
> = {
  starter: { description: "Try a single validation run" },
  builder: { description: "A few ideas with room to iterate" },
  founder: {
    description: "Best for active founders testing multiple ideas",
    popular: true,
  },
  growth: { description: "Higher volume validation and insights" },
  scale: { description: "Teams running continuous experiments" },
};
