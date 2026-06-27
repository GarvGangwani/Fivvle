import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
} from "@/lib/types";

export function createEmptyAnswers(
  questions: ClarifyingQuestion[],
): ClarifyingQuestionAnswer[] {
  return questions.map(() => ({ selectedOptions: [], otherText: "" }));
}

export function isQuestionAnswerValid(answer: ClarifyingQuestionAnswer): boolean {
  return answer.selectedOptions.length > 0 || answer.otherText.trim().length > 0;
}

export function formatClarifyingAnswers(
  questions: ClarifyingQuestion[],
  answers: ClarifyingQuestionAnswer[],
): string {
  return questions
    .map((question, index) => {
      const answer = answers[index];
      const parts: string[] = [...answer.selectedOptions];
      const other = answer.otherText.trim();
      if (other) {
        parts.push(`Other: ${other}`);
      }
      return `${question.question}\n→ ${parts.join("; ")}`;
    })
    .join("\n\n");
}

export function findPendingQuestionBlock(
  messages: {
    role: string;
    content?: string;
    turnKind?: string | null;
    clarifyingQuestions?: ClarifyingQuestion[];
  }[],
): { intro: string; questions: ClarifyingQuestion[] } | null {
  if (messages.length === 0) return null;
  const last = messages[messages.length - 1];
  if (last.role !== "assistant") return null;
  if (last.turnKind !== "refinement_clarify") return null;
  if (!last.clarifyingQuestions?.length) return null;
  return {
    intro: last.content ?? "",
    questions: last.clarifyingQuestions,
  };
}
