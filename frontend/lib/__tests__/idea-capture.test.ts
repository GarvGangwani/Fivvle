import { describe, expect, it } from "vitest";
import {
  canSubmitCapture,
  originAttachmentsForArtifact,
  shouldShowCaptureCard,
  shouldShowOriginArtifact,
} from "@/components/experiment/idea-capture-helpers";
import { getNodeLockState } from "@/components/experiment/canvas-helpers";
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
          idea_theme: "pink",
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
          idea_theme: "green",
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

  it("locks all phases before capture and unlocks spark after", () => {
    const locked = baseExperiment();
    expect(getNodeLockState("spark", locked).isLocked).toBe(true);
    expect(getNodeLockState("refine", locked).isLocked).toBe(true);
    expect(getNodeLockState("evidence", locked).isLocked).toBe(true);

    const captured = baseExperiment({
      has_original_idea: true,
      original_idea: "Captured",
      idea_theme: "violet",
    });
    expect(getNodeLockState("spark", captured).isLocked).toBe(false);
    expect(getNodeLockState("refine", captured).isLocked).toBe(false);
  });
});
