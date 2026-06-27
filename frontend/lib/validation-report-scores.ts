import type {
  QuestionFindings,
  SectionScore,
  ValidationReport,
} from "@/lib/types";

export type ReportSectionId =
  | "market"
  | "competition"
  | "distribution"
  | "regulatory"
  | "risk"
  | "research";

export interface ResolvedReportScores {
  sections: SectionScore[];
  overall: number;
  derived: boolean;
}

const CONFIDENCE_POINTS: Record<QuestionFindings["findings"][number]["confidence"], number> = {
  high: 88,
  medium: 68,
  low: 48,
};

const SECTION_LABELS: Record<ReportSectionId, string> = {
  market: "Market demand",
  competition: "Competition",
  distribution: "Distribution",
  regulatory: "Regulatory",
  risk: "Risk profile",
  research: "Research depth",
};

const SECTION_WEIGHTS: Record<ReportSectionId, number> = {
  market: 0.25,
  competition: 0.15,
  distribution: 0.1,
  regulatory: 0.05,
  risk: 0.2,
  research: 0.25,
};

function clampScore(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)));
}

export function scoreTone(score: number): "strong" | "mixed" | "weak" {
  if (score >= 70) return "strong";
  if (score >= 45) return "mixed";
  return "weak";
}

function questionScore(qf: QuestionFindings): number {
  if (qf.score != null) return clampScore(qf.score);
  if (qf.findings.length === 0) return 35;
  const avg =
    qf.findings.reduce((sum, f) => sum + CONFIDENCE_POINTS[f.confidence], 0) /
    qf.findings.length;
  const gapPenalty = qf.evidence_gap ? 12 : 0;
  return clampScore(avg - gapPenalty);
}

function recommendationRiskScore(report: ValidationReport): number {
  switch (report.overall_recommendation) {
    case "proceed":
      return 78;
    case "iterate":
      return 62;
    case "pivot":
      return 46;
    case "kill":
      return 28;
    case "too_vague_to_recommend":
      return 38;
  }
}

function deriveSectionScores(report: ValidationReport): SectionScore[] {
  const questionScores = report.questions_and_findings.map(questionScore);
  const researchAvg =
    questionScores.length > 0
      ? questionScores.reduce((a, b) => a + b, 0) / questionScores.length
      : 40;

  const competitionScore = clampScore(
    report.competitors.length === 0
      ? 42
      : 48 + report.competitors.length * 7 + Math.min(researchAvg * 0.15, 12),
  );

  const distributionScore = clampScore(
    report.distribution_signals?.trim() ? 68 : 38,
  );

  const regulatoryScore = clampScore(
    report.regulatory_signals?.trim() ? 65 : 45,
  );

  const marketScore = clampScore(researchAvg * 0.55 + (report.market_signals?.trim() ? 22 : 8));

  const ids: ReportSectionId[] = [
    "market",
    "competition",
    "distribution",
    "regulatory",
    "risk",
    "research",
  ];

  const values: Record<ReportSectionId, number> = {
    market: marketScore,
    competition: competitionScore,
    distribution: distributionScore,
    regulatory: regulatoryScore,
    risk: recommendationRiskScore(report),
    research: clampScore(researchAvg),
  };

  return ids.map((section_id) => ({
    section_id,
    label: SECTION_LABELS[section_id],
    score: values[section_id],
  }));
}

function weightedOverall(sections: SectionScore[]): number {
  let total = 0;
  let weight = 0;
  for (const section of sections) {
    const w = SECTION_WEIGHTS[section.section_id as ReportSectionId] ?? 0;
    total += section.score * w;
    weight += w;
  }
  return clampScore(weight > 0 ? total / weight : 0);
}

export function resolveReportScores(report: ValidationReport): ResolvedReportScores {
  const storedSections = report.section_scores ?? [];
  const hasStored = storedSections.length >= 6 && report.overall_score != null;

  if (hasStored) {
    return {
      sections: storedSections.slice(0, 6),
      overall: clampScore(report.overall_score!),
      derived: false,
    };
  }

  const sections = deriveSectionScores(report);
  return {
    sections,
    overall: weightedOverall(sections),
    derived: true,
  };
}

export function resolveQuestionScore(qf: QuestionFindings): number {
  return questionScore(qf);
}
