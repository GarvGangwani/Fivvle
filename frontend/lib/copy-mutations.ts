import type { CopyJson, FaqItem, FeatureCopy, HeroCopy } from "@/lib/types";

export type CopyMutator = (copy: CopyJson, value: string) => CopyJson;

function defaultHero(): HeroCopy {
  return { headline: "", subheadline: "", cta: "" };
}

export function updateHero(
  copy: CopyJson,
  field: keyof HeroCopy,
  value: string,
): CopyJson {
  return {
    ...copy,
    hero: { ...defaultHero(), ...copy.hero, [field]: value },
  };
}

export function updateProblem(
  copy: CopyJson,
  field: "heading" | "body",
  value: string,
): CopyJson {
  return {
    ...copy,
    problem: {
      heading: copy.problem?.heading ?? "",
      body: copy.problem?.body ?? "",
      [field]: value,
    },
  };
}

export function updateFeature(
  copy: CopyJson,
  index: number,
  field: keyof FeatureCopy,
  value: string,
): CopyJson {
  const features = [...(copy.features ?? [])];
  while (features.length <= index) {
    features.push({ title: "", description: "" });
  }
  features[index] = { ...features[index], [field]: value };
  return { ...copy, features };
}

export function updateCta(
  copy: CopyJson,
  field: "heading" | "subheading" | "button",
  value: string,
): CopyJson {
  return {
    ...copy,
    cta: {
      heading: copy.cta?.heading ?? "",
      subheading: copy.cta?.subheading ?? "",
      button: copy.cta?.button ?? "",
      [field]: value,
    },
  };
}

export function updateFaqItem(
  copy: CopyJson,
  index: number,
  field: keyof FaqItem,
  value: string,
): CopyJson {
  const faq = [...(copy.faq ?? [])];
  while (faq.length <= index) {
    faq.push({ question: "", answer: "" });
  }
  faq[index] = { ...faq[index], [field]: value };
  return { ...copy, faq };
}

export function updateProofHeadline(copy: CopyJson, value: string): CopyJson {
  return {
    ...copy,
    proof: {
      headline: value,
      elements: copy.proof?.elements ?? [],
    },
  };
}

export function updateProofElement(
  copy: CopyJson,
  index: number,
  value: string,
): CopyJson {
  const elements = [...(copy.proof?.elements ?? [])];
  while (elements.length <= index) {
    elements.push("");
  }
  elements[index] = value;
  return {
    ...copy,
    proof: {
      headline: copy.proof?.headline ?? "",
      elements,
    },
  };
}

export function updateComparisonCompetitor(
  copy: CopyJson,
  value: string,
): CopyJson {
  return {
    ...copy,
    comparison: {
      metric_label: copy.comparison?.metric_label ?? "",
      competitor_name: value,
      our_features: copy.comparison?.our_features ?? [],
      competitor_features: copy.comparison?.competitor_features ?? [],
    },
  };
}
