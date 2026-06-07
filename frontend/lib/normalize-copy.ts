import type { CopyJson, FaqItem, FeatureCopy } from "./types";
import { LIMITS, truncateText } from "./copy-limits";

/** Coerce LLM/legacy shapes into plain text safe for React children. */
export function asDisplayText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map(asDisplayText).filter(Boolean).join(" · ");
  }
  if (typeof value === "object") {
    const o = value as Record<string, unknown>;
    const stat = o.stat ?? o.value ?? o.metric;
    const desc = o.description ?? o.detail ?? o.label ?? o.text;
    if (typeof stat === "string" && typeof desc === "string") {
      return `${stat} — ${desc}`.trim();
    }
    if (typeof stat === "string") return stat.trim();
    if (typeof desc === "string") return desc.trim();
    if (typeof o.title === "string" && typeof o.body === "string") {
      return `${o.title}: ${o.body}`.trim();
    }
    if (typeof o.title === "string") return o.title.trim();
    if (typeof o.headline === "string") return o.headline.trim();
    if (typeof o.text === "string") return o.text.trim();
  }
  return "";
}

function normalizeStringList(items: unknown): string[] {
  if (!Array.isArray(items)) return [];
  return items.map(asDisplayText).filter((s) => s.length > 0);
}

function unwrapSectionItems(value: unknown): unknown {
  if (value == null) return value;
  if (Array.isArray(value)) return value;
  if (typeof value === "object") {
    const o = value as Record<string, unknown>;
    if (Array.isArray(o.items)) return o.items;
  }
  return value;
}

function normalizeFeature(item: unknown): FeatureCopy | null {
  if (!item || typeof item !== "object") return null;
  const o = item as Record<string, unknown>;
  const title = asDisplayText(o.title ?? o.name ?? o.heading);
  const description = asDisplayText(
    o.description ?? o.body ?? o.detail ?? o.subtitle,
  );
  if (!title && !description) return null;
  return {
    title: truncateText(title || "Feature", LIMITS.featureTitle),
    description: truncateText(description || "", LIMITS.featureBody),
  };
}

function normalizeFaqItem(item: unknown): FaqItem | null {
  if (!item || typeof item !== "object") return null;
  const o = item as Record<string, unknown>;
  const question = asDisplayText(o.question ?? o.q ?? o.title);
  const answer = asDisplayText(o.answer ?? o.a ?? o.body ?? o.response);
  if (!question) return null;
  return { question, answer: answer || "" };
}

/**
 * Sanitize copy_json before template render — prevents React crashes when
 * the LLM returns objects (e.g. proof elements as { stat, description }).
 */
export function normalizeCopyJson(copy: CopyJson): CopyJson {
  const next: CopyJson = { ...copy };

  if (copy.hero && typeof copy.hero === "object") {
    const h = copy.hero as unknown as Record<string, unknown>;
    next.hero = {
      headline: truncateText(asDisplayText(h.headline) || "Your product", LIMITS.headline),
      subheadline: truncateText(asDisplayText(h.subheadline), LIMITS.subheadline),
      cta: truncateText(asDisplayText(h.cta) || "Get started", 32),
    };
  }

  if (copy.problem && typeof copy.problem === "object") {
    const p = copy.problem as unknown as Record<string, unknown>;
    next.problem = {
      heading: truncateText(asDisplayText(p.heading) || "The problem", LIMITS.proofHeadline),
      body: truncateText(asDisplayText(p.body), LIMITS.featureBody),
    };
  }

  if (copy.features != null) {
    const rawFeatures = unwrapSectionItems(copy.features);
    next.features = (Array.isArray(rawFeatures) ? rawFeatures : [])
      .map(normalizeFeature)
      .filter((f): f is FeatureCopy => f != null);
  }

  if (copy.proof && typeof copy.proof === "object") {
    const p = copy.proof as unknown as Record<string, unknown>;
    next.proof = {
      headline: truncateText(asDisplayText(p.headline) || "Proof", LIMITS.proofHeadline),
      elements: normalizeStringList(p.elements).map((s) =>
        truncateText(s, 160),
      ),
    };
  }

  if (copy.comparison && typeof copy.comparison === "object") {
    const c = copy.comparison as unknown as Record<string, unknown>;
    next.comparison = {
      metric_label: asDisplayText(c.metric_label),
      competitor_name: asDisplayText(c.competitor_name) || "Competitors",
      our_features: normalizeStringList(c.our_features),
      competitor_features: normalizeStringList(c.competitor_features),
    };
  }

  if (copy.faq != null) {
    const rawFaq = unwrapSectionItems(copy.faq);
    next.faq = (Array.isArray(rawFaq) ? rawFaq : [])
      .map(normalizeFaqItem)
      .filter((f): f is FaqItem => f != null);
  }

  if (copy.objections && typeof copy.objections === "object") {
    const o = copy.objections as unknown as Record<string, unknown>;
    const items = Array.isArray(o.items) ? o.items : [];
    next.objections = {
      heading: asDisplayText(o.heading),
      items: items
        .map(normalizeFaqItem)
        .filter((f): f is FaqItem => f != null),
    };
  }

  if (copy.cta && typeof copy.cta === "object") {
    const c = copy.cta as unknown as Record<string, unknown>;
    next.cta = {
      heading: truncateText(asDisplayText(c.heading) || "Ready to start?", LIMITS.ctaHeading),
      subheading: truncateText(asDisplayText(c.subheading), LIMITS.ctaSubheading),
      button: truncateText(asDisplayText(c.button ?? c.cta) || "Sign up", 28),
    };
  }

  return next;
}
