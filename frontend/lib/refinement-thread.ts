export interface ClarityQaBlock {
  question: string;
  answers: string[];
}

export interface SourcedClarityQaBlock extends ClarityQaBlock {
  messageId: string;
}

/** Flatten all clarifying-answer user messages into one ordered Q&A list. */
export function collectSourcedClarityBlocks(
  messages: ReadonlyArray<{ id: string; role: string; content: string }>,
  firstUserMessageId: string | null,
): SourcedClarityQaBlock[] {
  const result: SourcedClarityQaBlock[] = [];

  for (const msg of messages) {
    if (msg.role !== "user") continue;
    if (msg.id === firstUserMessageId) continue;
    const blocks = parseClarifyingAnswerContent(msg.content);
    if (!blocks) continue;
    for (const block of blocks) {
      result.push({ ...block, messageId: msg.id });
    }
  }

  return result;
}

/** User message body from formatClarifyingAnswers — question lines with → answers. */
export function parseClarifyingAnswerContent(
  content: string,
): ClarityQaBlock[] | null {
  const trimmed = content.trim();
  if (!trimmed.includes("\n→")) return null;

  const blocks = trimmed.split(/\n\n+/);
  const result: ClarityQaBlock[] = [];

  for (const block of blocks) {
    const arrowIdx = block.indexOf("\n→");
    if (arrowIdx === -1) return null;
    const question = block.slice(0, arrowIdx).trim();
    const answerLine = block.slice(arrowIdx + 2).trim();
    if (!question || !answerLine) return null;
    const answers = answerLine.split(/\s*;\s*/).filter(Boolean);
    result.push({ question, answers });
  }

  return result.length > 0 ? result : null;
}

/** Assistant finalize message — "Researching: …" */
export function parseResearchingHypothesis(content: string): string | null {
  const trimmed = content.trim();
  if (!/^researching:/i.test(trimmed)) return null;
  const hypothesis = trimmed.replace(/^researching:\s*/i, "").trim();
  return hypothesis || null;
}

/** Join multi-select answers for Refinement Ascent pull-quote style. */
export function formatAnswersAscent(answers: string[]): string {
  return answers.join(" · ");
}

export function excerptIdea(text: string, maxLen = 140): string {
  const oneLine = text.replace(/\s+/g, " ").trim();
  if (oneLine.length <= maxLen) return oneLine;
  return `${oneLine.slice(0, maxLen).trim()}…`;
}
