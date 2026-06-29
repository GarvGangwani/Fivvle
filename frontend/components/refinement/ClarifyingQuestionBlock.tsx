"use client";

import { useEffect, useState } from "react";
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
} from "@/lib/types";
import {
  createEmptyAnswers,
  isQuestionAnswerValid,
} from "@/lib/clarifying-questions";
import "./refinement-ascent.css";
import "./refinement-thread.css";

interface ClarifyingQuestionBlockProps {
  questions: ClarifyingQuestion[];
  intro?: string;
  /** 1-based index for the first question in this batch (continues across rounds). */
  questionNumberStart?: number;
  submitting?: boolean;
  variant?: "default" | "ascent" | "peak";
  onSubmit: (answers: ClarifyingQuestionAnswer[]) => void;
}

export function ClarifyingQuestionBlock({
  questions,
  intro,
  questionNumberStart = 1,
  submitting = false,
  variant = "default",
  onSubmit,
}: ClarifyingQuestionBlockProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<ClarifyingQuestionAnswer[]>(() =>
    createEmptyAnswers(questions),
  );
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setCurrentIndex(0);
    setAnswers(createEmptyAnswers(questions));
    setValidationError(null);
  }, [questions]);

  const currentQuestion = questions[currentIndex];
  const currentAnswer = answers[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === questions.length - 1;

  function updateAnswer(next: ClarifyingQuestionAnswer) {
    setAnswers((prev) =>
      prev.map((item, idx) => (idx === currentIndex ? next : item)),
    );
    setValidationError(null);
  }

  function toggleOption(optionIndex: number) {
    const option = currentQuestion.options[optionIndex];
    const selected = new Set(currentAnswer.selectedOptions);
    if (selected.has(option)) {
      selected.delete(option);
    } else {
      selected.add(option);
    }
    updateAnswer({
      selectedOptions: [...selected],
      otherText: currentAnswer.otherText,
    });
  }

  function handlePrevious() {
    setValidationError(null);
    setCurrentIndex((idx) => Math.max(0, idx - 1));
  }

  function handleNext() {
    if (!isQuestionAnswerValid(currentAnswer)) {
      setValidationError(
        "Select at least one option (you can pick multiple) or enter a custom answer.",
      );
      return;
    }
    setValidationError(null);
    if (isLast) {
      onSubmit(answers);
      return;
    }
    setCurrentIndex((idx) => idx + 1);
  }

  const isAscent = variant === "ascent" || variant === "peak";
  const isPeak = variant === "peak";
  const isAscentLive = variant === "ascent";
  const globalQuestionNumber = questionNumberStart + currentIndex;

  return (
    <div
      className={`fv-msg-enter mx-auto w-full max-w-full lg:max-w-[42rem] ${
        isAscentLive ? "ra-clarify-wrap" : ""
      }`}
    >
      <div
        className={
          isAscent
            ? isPeak
              ? "rt-clarify-panel"
              : "ra-clarify-panel"
            : "overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)]"
        }
      >
        <div
          className={
            isAscent
              ? isPeak
                ? "rt-clarify-progress"
                : "ra-clarify-header"
              : "border-b border-[var(--fv-border)] px-6 py-4 text-center"
          }
        >
          {isAscent ? (
            isPeak ? (
              <>
                <p className="rt-clarify-progress-label">Sharpen your idea</p>
                <p className="rt-clarify-progress-count">
                  Question {currentIndex + 1} of {questions.length}
                </p>
              </>
            ) : (
              <>
                <h3 className="ra-clarify-title">Sharpen your idea</h3>
                <p className="ra-clarify-count">
                  Question {globalQuestionNumber}
                </p>
              </>
            )
          ) : (
            <p className="text-sm font-medium text-[var(--fv-text-muted)]">
              {currentIndex + 1} / {questions.length}
            </p>
          )}
        </div>

        <div className="space-y-6 px-6 py-6">
          {intro && currentIndex === 0 && !isAscentLive && (
            <p className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
              {intro}
            </p>
          )}

          <div>
            <h3 className="text-base font-semibold text-[var(--fv-text)]">
              {isAscentLive
                ? `${globalQuestionNumber}. ${currentQuestion.question}`
                : `Q${currentIndex + 1}. ${currentQuestion.question}`}
            </h3>
            <p className="mt-1.5 text-xs text-[var(--fv-text-muted)]">
              You can select multiple options — choose every answer that applies.
            </p>
          </div>

          <ol className="space-y-3">
            {currentQuestion.options.map((option, optionIndex) => {
              const selected = currentAnswer.selectedOptions.includes(option);

              return (
                <li key={`${currentIndex}-${optionIndex}`}>
                  <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--fv-border)] px-4 py-3 transition-colors hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5 has-[:checked]:border-[var(--fv-accent)]/50 has-[:checked]:bg-[var(--fv-accent)]/5">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={submitting}
                      onChange={() => toggleOption(optionIndex)}
                      className="mt-0.5 shrink-0 accent-[var(--fv-accent)]"
                    />
                    <span className="text-sm leading-relaxed text-[var(--fv-text)]">
                      <span className="mr-2 font-medium text-[var(--fv-text-muted)]">
                        {optionIndex + 1}.
                      </span>
                      {option}
                    </span>
                  </label>
                </li>
              );
            })}

            <li>
              <label className="flex flex-col gap-2 rounded-lg border border-[var(--fv-border)] px-4 py-3">
                <span className="text-sm font-medium text-[var(--fv-text)]">
                  {currentQuestion.options.length + 1}. Other:
                </span>
                <input
                  type="text"
                  value={currentAnswer.otherText}
                  disabled={submitting}
                  onChange={(e) =>
                    updateAnswer({
                      selectedOptions: currentAnswer.selectedOptions,
                      otherText: e.target.value,
                    })
                  }
                  placeholder="Type your answer…"
                  className="fv-input w-full px-3 py-2 text-sm"
                />
              </label>
            </li>
          </ol>

          {validationError && (
            <p className="text-sm text-[var(--fv-danger)]">{validationError}</p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-[var(--fv-border)] px-6 py-4">
          <button
            type="button"
            onClick={handlePrevious}
            disabled={isFirst || submitting}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={submitting}
            className="fv-btn-primary px-5 py-2 text-sm disabled:opacity-50"
          >
            {submitting ? "Submitting…" : isLast ? "Submit" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
