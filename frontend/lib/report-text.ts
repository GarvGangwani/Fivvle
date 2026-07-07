export interface ParsedRiskItem {
  number: number;
  title: string;
  body: string;
  verdict: string | null;
}

export interface ParsedRiskAssessment {
  items: ParsedRiskItem[];
  preamble: string | null;
  isStructured: boolean;
}

const NUMBERED_RISK_MARKER =
  /Risk\s+(\d+)\s*[—–-]\s*([^:]+):\s*/gi;

const NARRATIVE_RISK_MARKER =
  /The\s+(.+?)\s+risk\s+\(([^)]+)\)\s+is\s+([^:]+):\s*/gi;

function cleanRiskBody(body: string): string {
  return body
    .trim()
    .replace(/^["']\s*/, "")
    .replace(/\s*["']$/, "")
    .replace(/^[,;:]+\s*/, "")
    .trim();
}

function splitRiskVerdict(body: string): { verdict: string | null; detail: string } {
  const trimmed = cleanRiskBody(body);
  const dotIndex = trimmed.search(/[.!?]/);
  if (dotIndex === -1) {
    return { verdict: null, detail: trimmed };
  }

  const firstSentence = trimmed.slice(0, dotIndex + 1).trim();
  const remainder = trimmed.slice(dotIndex + 1).trim();

  const looksLikeVerdict =
    firstSentence.length <= 96 &&
    /^(Concerning|Mixed|Partially|Critically|High |Low |Unvalidated|Confirmed|Under-evidenced|Potentially|Substantially|Not |No direct)/i.test(
      firstSentence,
    );

  if (!looksLikeVerdict) {
    return { verdict: null, detail: trimmed };
  }

  return {
    verdict: firstSentence.replace(/\.$/, ""),
    detail: remainder,
  };
}

function parseNumberedRisks(text: string): ParsedRiskItem[] {
  const matches: {
    index: number;
    number: number;
    title: string;
    markerLength: number;
  }[] = [];

  for (const match of text.matchAll(NUMBERED_RISK_MARKER)) {
    if (match.index === undefined) continue;
    matches.push({
      index: match.index,
      number: Number.parseInt(match[1], 10),
      title: match[2].trim(),
      markerLength: match[0].length,
    });
  }

  if (matches.length === 0) {
    return [];
  }

  return matches.map((current, index) => {
    const bodyStart = current.index + current.markerLength;
    const bodyEnd =
      index + 1 < matches.length ? matches[index + 1].index : text.length;
    const rawBody = cleanRiskBody(text.slice(bodyStart, bodyEnd));
    const { verdict, detail } = splitRiskVerdict(rawBody);

    return {
      number: current.number,
      title: current.title,
      body: detail || rawBody,
      verdict,
    };
  });
}

function parseNarrativeRisks(text: string): ParsedRiskItem[] {
  const matches: {
    index: number;
    title: string;
    questionRefs: string;
    verdict: string;
    markerLength: number;
  }[] = [];

  for (const match of text.matchAll(NARRATIVE_RISK_MARKER)) {
    if (match.index === undefined) continue;
    matches.push({
      index: match.index,
      title: match[1].trim(),
      questionRefs: match[2].trim(),
      verdict: match[3].trim(),
      markerLength: match[0].length,
    });
  }

  if (matches.length < 2) {
    return [];
  }

  return matches.map((current, index) => {
    const bodyStart = current.index + current.markerLength;
    const bodyEnd =
      index + 1 < matches.length ? matches[index + 1].index : text.length;

    return {
      number: index + 1,
      title: `${current.title} (${current.questionRefs})`,
      body: cleanRiskBody(text.slice(bodyStart, bodyEnd)),
      verdict: current.verdict,
    };
  });
}

/** Parse synthesizer risk prose into discrete risk items when markers are present. */
export function parseRiskAssessment(text: string): ParsedRiskAssessment {
  const trimmed = text.trim();
  if (!trimmed) {
    return { items: [], preamble: null, isStructured: false };
  }

  const numberedMatches = [...trimmed.matchAll(NUMBERED_RISK_MARKER)];
  if (numberedMatches.length > 0) {
    const firstIndex = numberedMatches[0].index ?? 0;
    const preamble =
      firstIndex > 0 ? cleanRiskBody(trimmed.slice(0, firstIndex)) : null;

    return {
      items: parseNumberedRisks(trimmed),
      preamble: preamble || null,
      isStructured: true,
    };
  }

  const narrativeItems = parseNarrativeRisks(trimmed);
  if (narrativeItems.length > 0) {
    return {
      items: narrativeItems,
      preamble: null,
      isStructured: true,
    };
  }

  return { items: [], preamble: null, isStructured: false };
}

/** Split long report prose into shorter paragraphs for on-screen readability. */

export function splitReadableParagraphs(text: string, maxChars = 380): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  if (trimmed.length <= maxChars) {
    return [trimmed];
  }

  const sentenceBoundary = /(?<=[.!?])\s+(?=[A-Z("'\u201C\u2018])/g;
  const sentences = trimmed
    .split(sentenceBoundary)
    .map((s) => s.trim())
    .filter(Boolean);

  if (sentences.length === 0) {
    return [trimmed];
  }

  const paragraphs: string[] = [];
  let buffer = "";

  for (const sentence of sentences) {
    const candidate = buffer ? `${buffer} ${sentence}` : sentence;
    if (candidate.length > maxChars && buffer) {
      paragraphs.push(buffer);
      buffer = sentence;
    } else {
      buffer = candidate;
    }
  }

  if (buffer) {
    paragraphs.push(buffer);
  }

  return paragraphs.length > 0 ? paragraphs : [trimmed];
}

export function questionDisplayIndex(questionId: string, fallback: number): number {
  const match = questionId.match(/(\d+)/);
  if (match) return Number.parseInt(match[1], 10);
  return fallback;
}
