import { describe, expect, it } from "vitest";

import { parseCitations, tokenizeCitations } from "../parse-citations";

describe("parseCitations", () => {
  it("extracts and dedupes URL citations, stripping markers", () => {
    const { cleanedText, urlCitations, refCitations } = parseCitations(
      "Buyers want this [cite: https://a.com/x, https://b.com/y]. Confirmed again [cite: https://a.com/x].",
    );
    expect(urlCitations).toEqual(["https://a.com/x", "https://b.com/y"]);
    expect(refCitations).toEqual([]);
    expect(cleanedText).toBe("Buyers want this. Confirmed again.");
  });

  it("parses question, competitor, section, and limitation refs", () => {
    const { refCitations, cleanedText } = parseCitations(
      "q3 is a gap [ref: q3]. Guru overlaps [ref: competitor:Guru]. Market is strong [ref: section:market]. Not covered [ref: limitation].",
    );
    expect(refCitations).toEqual([
      { kind: "question", value: "q3" },
      { kind: "competitor", value: "Guru" },
      { kind: "section", value: "market" },
      { kind: "limitation", value: "limitation" },
    ]);
    expect(cleanedText).toBe(
      "q3 is a gap. Guru overlaps. Market is strong. Not covered.",
    );
  });

  it("preserves competitor-name casing but dedupes case-insensitively", () => {
    const { refCitations } = parseCitations(
      "One [ref: competitor:Guru]. Two [ref: competitor:guru].",
    );
    expect(refCitations).toEqual([{ kind: "competitor", value: "Guru" }]);
  });

  it("drops unrecognized ref anchors silently", () => {
    const { refCitations, cleanedText } = parseCitations(
      "Nope [ref: q9]. Nope [ref: section:bogus]. Nope [ref: chat_history]. Nope [ref: report_skeleton].",
    );
    expect(refCitations).toEqual([]);
    expect(cleanedText).toBe("Nope. Nope. Nope. Nope.");
  });

  it("handles mixed cite + ref in one reply", () => {
    const { urlCitations, refCitations } = parseCitations(
      "Pricing varies [cite: https://g2.com/guru] and q2 covers it [ref: q2].",
    );
    expect(urlCitations).toEqual(["https://g2.com/guru"]);
    expect(refCitations).toEqual([{ kind: "question", value: "q2" }]);
  });

  it("returns content unchanged when there are no markers", () => {
    const { cleanedText, urlCitations, refCitations } = parseCitations(
      "Just a plain answer with no citations.",
    );
    expect(cleanedText).toBe("Just a plain answer with no citations.");
    expect(urlCitations).toEqual([]);
    expect(refCitations).toEqual([]);
  });

  it("preserves the italic follow-up line", () => {
    const { cleanedText } = parseCitations(
      "The answer [cite: https://a.com].\n*What is your wedge?*",
    );
    expect(cleanedText).toBe("The answer.\n*What is your wedge?*");
  });
});

describe("tokenizeCitations", () => {
  it("keeps markers inline between text segments", () => {
    const tokens = tokenizeCitations(
      "Demand is real [cite: https://a.com]. Gap on q2 [ref: q2].",
    );
    expect(tokens).toEqual([
      { type: "text", value: "Demand is real " },
      { type: "marker", marker: "[cite: https://a.com]" },
      { type: "text", value: ". Gap on q2 " },
      { type: "marker", marker: "[ref: q2]" },
      { type: "text", value: "." },
    ]);
  });

  it("splits back-to-back primary-source cite ids into distinct tokens", () => {
    const tokens = tokenizeCitations(
      "Incumbents are noisy [cite:s1][cite:s3]. Done.",
    );
    expect(tokens).toEqual([
      { type: "text", value: "Incumbents are noisy " },
      { type: "marker", marker: "[cite:s1]" },
      { type: "marker", marker: "[cite:s3]" },
      { type: "text", value: ". Done." },
    ]);
  });

  it("returns a single text token when there are no markers", () => {
    expect(tokenizeCitations("Plain answer.")).toEqual([
      { type: "text", value: "Plain answer." },
    ]);
  });
});
