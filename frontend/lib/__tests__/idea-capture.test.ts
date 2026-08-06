import { describe, expect, it } from "vitest";
import {
  canSubmitCapture,
  originAttachmentsForArtifact,
  shouldShowCaptureCard,
  shouldShowOriginArtifact,
} from "@/components/experiment/idea-capture-helpers";
import { isPhaseNodeVisible } from "@/components/experiment/canvas-helpers";
import type { Experiment } from "@/lib/types";

function baseExperiment(overrides: Partial<Experiment> = {}): Experiment {
  return {
    id: "exp-1",
    status: "SPARK",
    validation_report: null,
    has_original_idea: false,
    original_idea: null,
    ...overrides,
  };
}

describe("idea capture helpers", () => {
  it("shows capture card only when original idea is missing", () => {
    expect(shouldShowCaptureCard(baseExperiment())).toBe(true);
    expect(
      shouldShowCaptureCard(
        baseExperiment({
          has_original_idea: true,
          original_idea: "A dating app for couples",
          suggested_palette: "rose",
        }),
      ),
    ).toBe(false);
  });

  it("shows origin artifact only after capture", () => {
    expect(shouldShowOriginArtifact(baseExperiment())).toBe(false);
    expect(
      shouldShowOriginArtifact(
        baseExperiment({
          has_original_idea: true,
          original_idea: "Sealed idea",
          suggested_palette: "emerald",
        }),
      ),
    ).toBe(true);
  });

  it("disables capture until idea text is present", () => {
    expect(canSubmitCapture("", false)).toBe(false);
    expect(canSubmitCapture("   ", false)).toBe(false);
    expect(canSubmitCapture("An idea", true)).toBe(false);
    expect(canSubmitCapture("An idea", false)).toBe(true);
  });

  it("maps frozen origin attachments for the artifact chips", () => {
    const mapped = originAttachmentsForArtifact("exp-1", [
      {
        id: "a1",
        original_filename: "logo.png",
        content_kind: "image",
        media_type: "image/png",
        created_at: "2026-08-05T12:00:00Z",
      },
    ]);
    expect(mapped).toHaveLength(1);
    expect(mapped[0]?.title).toBe("logo.png");
    expect(mapped[0]?.attachment_type).toBe("image");
    expect(mapped[0]?.file_url).toBeNull();
  });

  it("hides every phase before capture and reveals refine after", () => {
    const precapture = baseExperiment();
    expect(isPhaseNodeVisible("refine", precapture)).toBe(false);
    expect(isPhaseNodeVisible("resources", precapture)).toBe(false);
    expect(isPhaseNodeVisible("evidence", precapture)).toBe(false);
    // Origin slot holds the capture prompt, so it stays on the canvas.
    expect(isPhaseNodeVisible("spark", precapture)).toBe(true);

    const captured = baseExperiment({
      has_original_idea: true,
      original_idea: "Captured",
    });
    expect(isPhaseNodeVisible("refine", captured)).toBe(true);
    expect(isPhaseNodeVisible("resources", captured)).toBe(true);
    expect(isPhaseNodeVisible("evidence", captured)).toBe(false);
  });
});
