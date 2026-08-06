import { describe, expect, it } from "vitest";
import { ACT_CONFIG } from "@/components/experiment/act-config";
import {
  getPhaseRevealState,
  isPhaseNodeVisible,
} from "@/components/experiment/canvas-helpers";
import type { Experiment } from "@/lib/types";

const PHASES = ["refine", "resources", "evidence", "launch", "signal"] as const;

function experiment(overrides: Partial<Experiment> = {}): Experiment {
  return {
    id: "exp-1",
    status: "SPARK",
    validation_report: null,
    has_original_idea: true,
    original_idea: "A tool that turns support calls into a weekly digest.",
    ...overrides,
  };
}

function visiblePhases(exp: Experiment): string[] {
  return PHASES.filter((id) => isPhaseNodeVisible(id, exp));
}

describe("progressive phase reveal", () => {
  it("hides every phase before capture", () => {
    const precapture = experiment({
      has_original_idea: false,
      original_idea: null,
    });
    expect(visiblePhases(precapture)).toEqual([]);
  });

  it("reveals refine and resources on capture", () => {
    expect(visiblePhases(experiment())).toEqual(["refine", "resources"]);
  });

  it("reveals evidence only once the founder completes refine", () => {
    const refining = experiment({
      status: "REFINED",
      refined_idea: "Turns support calls into a weekly product digest.",
    });
    // A finalized idea is not completion — the founder has to say so.
    expect(isPhaseNodeVisible("evidence", refining)).toBe(false);

    const completed = experiment({
      ...refining,
      refine_completed_at: "2026-08-06T01:00:00Z",
    });
    expect(visiblePhases(completed)).toEqual([
      "refine",
      "resources",
      "evidence",
    ]);
  });

  it("reveals launch once evidence produced a report", () => {
    const base = experiment({ refine_completed_at: "2026-08-06T01:00:00Z" });

    expect(
      isPhaseNodeVisible("launch", { ...base, status: "RESEARCHING" }),
    ).toBe(false);
    // A failed run is not a completed phase.
    expect(
      isPhaseNodeVisible("launch", { ...base, status: "RESEARCH_FAILED" }),
    ).toBe(false);

    const researched = { ...base, status: "RESEARCH_READY" };
    expect(visiblePhases(researched)).toEqual([
      "refine",
      "resources",
      "evidence",
      "launch",
    ]);
  });

  it("reveals signal only after the landing page goes live", () => {
    const base = experiment({
      refine_completed_at: "2026-08-06T01:00:00Z",
      status: "LANDING_DRAFT",
      validation_report: {
        overall_recommendation: "proceed",
        total_finding_count: 4,
        total_citation_count: 9,
      },
    });
    // Generated but never published.
    expect(isPhaseNodeVisible("signal", base)).toBe(false);

    const live = {
      ...base,
      landing_page_live_at: "2026-08-06T02:00:00Z",
    };
    expect(visiblePhases(live)).toEqual([
      "refine",
      "resources",
      "evidence",
      "launch",
      "signal",
    ]);
  });

  it("keeps a revealed phase visible when status moves backwards", () => {
    // Re-finalizing refine sends status back to REFINED while the page is live.
    const reopened = experiment({
      status: "REFINED",
      refine_completed_at: "2026-08-06T01:00:00Z",
      landing_page_live_at: "2026-08-06T02:00:00Z",
    });
    expect(visiblePhases(reopened)).toEqual([
      "refine",
      "resources",
      "evidence",
      "launch",
      "signal",
    ]);
  });

  it("keeps pre-stamp experiments coherent", () => {
    // Rows that already had a report when the stamp shipped: downstream
    // completion implies the earlier phases are done.
    const legacy = experiment({
      status: "RESEARCH_READY",
      refine_completed_at: null,
    });
    expect(isPhaseNodeVisible("evidence", legacy)).toBe(true);
    expect(isPhaseNodeVisible("launch", legacy)).toBe(true);
  });

  it("explains what is missing for the deep-link guard", () => {
    const captured = experiment();
    expect(getPhaseRevealState("evidence", captured).requirement).toMatch(
      /refin/i,
    );
    expect(getPhaseRevealState("launch", captured).requirement).toMatch(
      /evidence/i,
    );
    expect(getPhaseRevealState("signal", captured).requirement).toMatch(
      /launch/i,
    );
    expect(getPhaseRevealState("refine", captured).requirement).toBeUndefined();
  });

  it("keeps the origin slot on the canvas at every stage", () => {
    expect(
      isPhaseNodeVisible(
        "spark",
        experiment({ has_original_idea: false, original_idea: null }),
      ),
    ).toBe(true);
    expect(isPhaseNodeVisible("spark", experiment())).toBe(true);
  });
});

describe("phase labels", () => {
  it("carries no phase numbering", () => {
    for (const [id, config] of Object.entries(ACT_CONFIG)) {
      expect(config, id).not.toHaveProperty("index");
      const label = `${config.actName} ${config.title}`;
      expect(label, id).not.toMatch(/phase/i);
      expect(config.actName, id).not.toMatch(/\d/);
    }
  });

  it("names each phase in plain uppercase", () => {
    expect(ACT_CONFIG.refine.actName).toBe("REFINE");
    expect(ACT_CONFIG.evidence.actName).toBe("EVIDENCE");
    expect(ACT_CONFIG.launch.actName).toBe("LAUNCH");
    expect(ACT_CONFIG.signal.actName).toBe("SIGNAL");
  });
});
