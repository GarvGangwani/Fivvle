import { describe, expect, it } from "vitest";

import { parseRiskAssessment, splitReadableParagraphs } from "../report-text";

describe("parseRiskAssessment / cleanRiskBody", () => {
  it("cleanRiskBody strips leading commas from risk bodies", () => {
    const parsed = parseRiskAssessment(
      "Risk 1 — Trust: , roadside assistance or walk-home safety, test trust mechanisms via NDAs. Risk 2 — Cost: Reasonable.",
    );

    expect(parsed.items[0].body).not.toMatch(/^[,;:]/);
    expect(parsed.items[0].body.startsWith("roadside")).toBe(true);
  });

  it("cleanRiskBody strips leading colons and semicolons too", () => {
    const semicolon = parseRiskAssessment(
      "Risk 1 — Trust: ; roadside assistance or walk-home safety, test trust mechanisms via NDAs. Risk 2 — Cost: Reasonable.",
    );
    expect(semicolon.items[0].body).not.toMatch(/^[,;:]/);
    expect(semicolon.items[0].body.startsWith("roadside")).toBe(true);

    const colon = parseRiskAssessment(
      "Risk 1 — Trust: : roadside assistance or walk-home safety, test trust mechanisms via NDAs. Risk 2 — Cost: Reasonable.",
    );
    expect(colon.items[0].body).not.toMatch(/^[,;:]/);
    expect(colon.items[0].body.startsWith("roadside")).toBe(true);
  });
});

describe("splitReadableParagraphs", () => {
  it("preserves decimal-heavy text without dropping prefixes", () => {
    const input =
      "The market is $47.3B (Grand View Research 2024). Growth is 12.1% CAGR. Another source (Statista) says $52.4B.";
    const joined = splitReadableParagraphs(input, 100).join(" ");

    expect(joined).toContain("The market is $47.3B");
    expect(joined).toContain("Growth is 12.1% CAGR");
    expect(joined).toContain("Statista");
    expect(joined).toContain("$52.4B");
  });

  it("still splits sentences at real boundaries", () => {
    const input =
      "This first sentence is deliberately long enough to exceed the paragraph budget on its own when combined with anything else. This second sentence also runs long so that together they must be split across two paragraphs for readability.";
    const paragraphs = splitReadableParagraphs(input, 120);

    expect(paragraphs).toHaveLength(2);
  });

  it("returns the whole string when it fits under maxChars", () => {
    const input = "Short market note with $47.3B cited once.";
    expect(splitReadableParagraphs(input, 380)).toEqual([input]);
  });

  it("handles empty and whitespace-only input", () => {
    expect(splitReadableParagraphs("")).toEqual([]);
    expect(splitReadableParagraphs("   \n\t  ")).toEqual([]);
  });
});
