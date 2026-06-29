import type { SectionScore, ValidationReport } from "@/lib/types";
import type { ReportSectionId } from "@/lib/validation-report-scores";
import { resolveQuestionScore } from "@/lib/validation-report-scores";

export type ScoreSelectionId = ReportSectionId | "overall";

export interface SectionScoreDetail extends SectionScore {
  rationale: string;
  pros: string[];
  cons: string[];
  context: string;
}

export interface OverallScoreDetail {
  id: "overall";
  label: string;
  score: number;
  rationale: string;
  pros: string[];
  cons: string[];
  context: string;
}

function truncate(text: string, max = 360): string {
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1).trim()}…`;
}

function highConfidenceCount(report: ValidationReport): number {
  return report.questions_and_findings.reduce(
    (total, qf) =>
      total + qf.findings.filter((f) => f.confidence === "high").length,
    0,
  );
}

function gapCount(report: ValidationReport): number {
  return report.questions_and_findings.filter((qf) => qf.evidence_gap?.trim()).length;
}

function storedDetail(section: SectionScore): Partial<SectionScoreDetail> | null {
  const hasRationale = Boolean(section.rationale?.trim());
  const hasPros = (section.pros?.length ?? 0) > 0;
  const hasCons = (section.cons?.length ?? 0) > 0;
  if (!hasRationale && !hasPros && !hasCons) return null;
  return {
    rationale: section.rationale?.trim() ?? "",
    pros: section.pros ?? [],
    cons: section.cons ?? [],
  };
}

function buildMarketDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const high = highConfidenceCount(report);
  const gaps = gapCount(report);
  const context = report.market_signals?.trim()
    ? truncate(report.market_signals)
    : "No dedicated market signals section in this report.";

  return {
    section_id: "market",
    label: "Market demand",
    score,
    context,
    rationale:
      score >= 70
        ? "Demand signals are supported by multiple cited findings and substantive market evidence."
        : score >= 45
          ? "Some demand indicators exist, but market evidence is mixed or partially gaps-filled."
          : "Market demand evidence is thin — few corroborated signals or explicit gaps noted.",
    pros: [
      ...(report.market_signals?.trim()
        ? ["Market signals section cites observable demand or category activity."]
        : []),
      ...(high >= 2 ? [`${high} high-confidence findings support demand-related claims.`] : []),
    ],
    cons: [
      ...(gaps > 0 ? [`${gaps} research question(s) flagged evidence gaps.`] : []),
      ...(!report.market_signals?.trim()
        ? ["No structured market signals narrative was produced."]
        : []),
      ...(report.research_limitations.toLowerCase().includes("market")
        ? ["Research limitations note missing or weak market-size data."]
        : []),
    ],
  };
}

function buildCompetitionDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const names = report.competitors.map((c) => c.name).slice(0, 4);
  const context =
    report.competitors.length > 0
      ? report.competitors
          .map((c) => `${c.name}: ${truncate(c.positioning_vs_idea, 140)}`)
          .join("\n\n")
      : "No named competitors were surfaced in the research.";

  return {
    section_id: "competition",
    label: "Competition",
    score,
    context: truncate(context, 420),
    rationale:
      report.competitors.length === 0
        ? "Competitive landscape is unclear — no named, cited competitors in the report."
        : score >= 70
          ? "Competitive landscape is well mapped with named players and cited positioning."
          : "Competitors are identified but overlap or differentiation remains uncertain.",
    pros: [
      ...(names.length > 0
        ? [`${report.competitors.length} named competitor(s): ${names.join(", ")}.`]
        : []),
      ...(report.competitors.some((c) => c.citations.length > 0)
        ? ["Competitor claims include source citations."]
        : []),
    ],
    cons: [
      ...(report.competitors.length >= 4
        ? ["Crowded competitive set — differentiation must be sharp."]
        : []),
      ...(report.competitors.length === 0
        ? ["No verified competitors — may indicate weak search coverage or vague category."]
        : []),
    ],
  };
}

function buildDistributionDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const context = report.distribution_signals?.trim()
    ? truncate(report.distribution_signals)
    : "Distribution was not substantively covered — no distribution signals section.";

  return {
    section_id: "distribution",
    label: "Distribution",
    score,
    context,
    rationale: report.distribution_signals?.trim()
      ? "Acquisition or channel evidence appears in the report."
      : "Little to no cited evidence on how this idea would reach customers.",
    pros: report.distribution_signals?.trim()
      ? ["Distribution signals reference concrete channels or growth mechanics."]
      : [],
    cons: report.distribution_signals?.trim()
      ? []
      : ["No distribution_signals narrative — go-to-market path is unvalidated."],
  };
}

function buildRegulatoryDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const context = report.regulatory_signals?.trim()
    ? truncate(report.regulatory_signals)
    : "No regulatory or compliance angle was investigated for this idea.";

  return {
    section_id: "regulatory",
    label: "Regulatory",
    score,
    context,
    rationale: report.regulatory_signals?.trim()
      ? "Regulatory or compliance factors were researched and documented."
      : "Regulatory dimension appears low-relevance or was not evidenced in research.",
    pros: report.regulatory_signals?.trim()
      ? ["Regulatory constraints or requirements are explicitly documented."]
      : ["No apparent regulatory blocker surfaced in available evidence."],
    cons: report.regulatory_signals?.trim()
      ? ["Compliance requirements may add launch friction or cost."]
      : ["Regulatory exposure was not deeply investigated — unknown risk remains."],
  };
}

function buildRiskDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const context = truncate(report.risks_assessment);

  return {
    section_id: "risk",
    label: "Risk profile",
    score,
    context,
    rationale:
      report.overall_recommendation === "kill"
        ? "Material risks appear fatal or poorly mitigated based on the assessment."
        : report.overall_recommendation === "proceed"
          ? "Key risks were investigated and appear manageable relative to opportunity."
          : "Risks are documented but several remain partially confirmed or unaddressed.",
    pros: [
      ...(report.risks_assessment.length > 80
        ? ["Risk assessment engages specific risks from refinement."]
        : []),
      ...(report.overall_recommendation === "proceed"
        ? ["Recommendation suggests risk profile is acceptable to move forward."]
        : []),
    ],
    cons: [
      ...(report.overall_recommendation === "kill" || report.overall_recommendation === "pivot"
        ? [`Overall recommendation is ${report.overall_recommendation} — elevated downside.`]
        : []),
      ...(gapCount(report) > 0 ? ["Some research questions left evidence gaps on related risks."] : []),
    ],
  };
}

function buildResearchDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const gaps = report.questions_and_findings.filter((qf) => qf.evidence_gap?.trim());
  const low = report.questions_and_findings.filter((qf) =>
    qf.findings.every((f) => f.confidence === "low"),
  );
  const context = report.questions_and_findings
    .map((qf) => {
      const qScore = resolveQuestionScore(qf);
      const gap = qf.evidence_gap ? ` Gap: ${truncate(qf.evidence_gap, 100)}` : "";
      return `${qf.question_id.toUpperCase()} (${qScore}/100): ${truncate(qf.question, 120)}${gap}`;
    })
    .join("\n");

  return {
    section_id: "research",
    label: "Research depth",
    score,
    context: truncate(context, 420),
    rationale:
      score >= 70
        ? "Most research questions are answered with corroborated, medium-to-high confidence findings."
        : score >= 45
          ? "Research coverage is partial — some questions lack depth or cite thin evidence."
          : "Research depth is weak — multiple low-confidence findings or unanswered gaps.",
    pros: [
      `${report.questions_and_findings.length} research questions investigated.`,
      ...(highConfidenceCount(report) >= 3
        ? [`${highConfidenceCount(report)} high-confidence findings across the report.`]
        : []),
    ],
    cons: [
      ...(gaps.length > 0
        ? [`Evidence gaps on: ${gaps.map((g) => g.question_id).join(", ")}.`]
        : []),
      ...(low.length > 0
        ? [`Low-confidence only on: ${low.map((g) => g.question_id).join(", ")}.`]
        : []),
    ],
  };
}

function mergeStored(
  derived: SectionScoreDetail,
  stored: Partial<SectionScoreDetail> | null,
): SectionScoreDetail {
  if (!stored) return derived;
  return {
    ...derived,
    rationale: stored.rationale || derived.rationale,
    pros: stored.pros?.length ? stored.pros : derived.pros,
    cons: stored.cons?.length ? stored.cons : derived.cons,
  };
}

function buildDerivedDetail(
  report: ValidationReport,
  section: SectionScore,
): SectionScoreDetail {
  switch (section.section_id) {
    case "market":
      return buildMarketDetail(report, section.score);
    case "competition":
      return buildCompetitionDetail(report, section.score);
    case "distribution":
      return buildDistributionDetail(report, section.score);
    case "regulatory":
      return buildRegulatoryDetail(report, section.score);
    case "risk":
      return buildRiskDetail(report, section.score);
    case "research":
      return buildResearchDetail(report, section.score);
  }
}

export function buildSectionScoreDetails(
  report: ValidationReport,
  sections: SectionScore[],
): SectionScoreDetail[] {
  return sections.map((section) =>
    mergeStored(buildDerivedDetail(report, section), storedDetail(section)),
  );
}

export function buildOverallScoreDetail(
  report: ValidationReport,
  overall: number,
): OverallScoreDetail {
  const rec = report.overall_recommendation;
  const context = truncate(
    [report.recommendation_rationale, report.executive_summary]
      .filter(Boolean)
      .join("\n\n"),
    420,
  );

  const recLabel =
    rec === "too_vague_to_recommend"
      ? "needs clarity"
      : rec.replace("_", " ");

  return {
    id: "overall",
    label: "Overall score",
    score: overall,
    context,
    rationale: `Composite validation score reflecting market, competition, distribution, regulatory, risk, and research depth. Recommendation: ${recLabel}.`,
    pros: [
      ...(rec === "proceed" ? ["Research supports moving forward with the current thesis."] : []),
      ...(overall >= 70 ? ["Multiple dimensions score above 70."] : []),
      ...(highConfidenceCount(report) >= 4
        ? ["Strong volume of high-confidence findings."]
        : []),
    ],
    cons: [
      ...(rec === "kill" || rec === "pivot"
        ? [`Verdict is ${recLabel} — composite score reflects serious concerns.`]
        : []),
      ...(gapCount(report) > 0
        ? [`${gapCount(report)} research area(s) have documented evidence gaps.`]
        : []),
      ...(report.research_limitations.trim()
        ? ["See research limitations for uncovered dimensions."]
        : []),
    ],
  };
}

export function findScoreDetail(
  details: SectionScoreDetail[],
  id: ScoreSelectionId,
): SectionScoreDetail | OverallScoreDetail | null {
  if (id === "overall") return null;
  return details.find((d) => d.section_id === id) ?? null;
}
