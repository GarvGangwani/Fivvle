import type { CopyJson } from "./types";

export interface PricingPlan {
  name: string;
  price: string;
  description?: string;
  period?: string;
  features: string[];
  featured?: boolean;
}

/** Parse pricing plans from copy_json — only returns plans with real name + price. */
export function resolvePricingPlans(copy: CopyJson): PricingPlan[] {
  const raw = copy.pricing;
  if (raw == null) return [];

  const list = Array.isArray(raw)
    ? raw
    : typeof raw === "object" && Array.isArray((raw as { plans?: unknown }).plans)
      ? ((raw as { plans: unknown[] }).plans ?? [])
      : [];

  const plans: PricingPlan[] = [];
  for (const item of list) {
    if (!item || typeof item !== "object") continue;
    const o = item as Record<string, unknown>;
    const name = String(o.name ?? o.tier ?? "").trim();
    const price = String(o.price ?? o.amount ?? "").trim();
    if (!name || !price) continue;

    const features = Array.isArray(o.features)
      ? o.features.map((f) => String(f).trim()).filter(Boolean)
      : [];

    plans.push({
      name,
      price,
      description: String(o.description ?? o.subtitle ?? "").trim() || undefined,
      period: String(o.period ?? o.interval ?? "").trim() || undefined,
      features,
      featured: o.featured === true || o.highlighted === true,
    });
  }

  return plans;
}

export function hasPricingSection(copy: CopyJson): boolean {
  return resolvePricingPlans(copy).length > 0;
}

export function hasFeaturesSection(copy: CopyJson): boolean {
  return (copy.features?.length ?? 0) > 0;
}

export function hasProofSignals(copy: CopyJson): boolean {
  return (copy.proof?.elements?.length ?? 0) > 0;
}
