"use client";

import { useEffect, useState } from "react";
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
  PastClarifyingTurn,
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
  /**
   * Past clarifying-question turns from earlier in the thread. When provided,
   * the wizard's Previous button navigates BACKWARD across these past turns
   * (in addition to within the current batch), showing each past question
   * with the user's prior answer pre-selected and editable.
   */
  pastTurns?: PastClarifyingTurn[];
  /**
   * Called when the founder saves an edit to a past turn's answer. The
   * caller is expected to truncate downstream thread state and call the
   * edit API. On resolve, the wizard resets to normal state (new pending
   * batch renders when the server response arrives).
   */
  onEditPast?: (
    messageId: string,
    answer: ClarifyingQuestionAnswer,
  ) => Promise<void>;
}

function answersEqual(
  a: ClarifyingQuestionAnswer,
  b: ClarifyingQuestionAnswer,
): boolean {
  if (a.otherText.trim() !== b.otherText.trim()) return false;
  if (a.selectedOptions.length !== b.selectedOptions.length) return false;
  const sortedA = [...a.selectedOptions].sort();
  const sortedB = [...b.selectedOptions].sort();
  return sortedA.every((opt, idx) => opt === sortedB[idx]);
}

function cloneAnswer(answer: ClarifyingQuestionAnswer): ClarifyingQuestionAnswer {
  return {
    selectedOptions: [...answer.selectedOptions],
    otherText: answer.otherText,
  };
}

function ConfirmRegenerateModal({
  open,
  discardedCount,
  onCancel,
  onConfirm,
  regenerating,
  error,
}: {
  open: boolean;
  discardedCount: number;
  onCancel: () => void;
  onConfirm: () => void;
  regenerating: boolean;
  error: string | null;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-regenerate-title"
    >
      <div className="w-full max-w-md rounded-xl bg-[var(--fv-surface)] p-6 shadow-xl">
        <h3
          id="confirm-regenerate-title"
          className="text-base font-semibold text-[var(--fv-text)]"
        >
          Save and regenerate later questions?
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-[var(--fv-text-muted)]">
          Changing this answer will discard your responses to{" "}
          {discardedCount === 1
            ? "1 later question"
            : `${discardedCount} later questions`}
          . The next question will regenerate based on your new answer.
        </p>
        {error && (
          <p className="mt-3 text-sm text-[var(--fv-danger)]">{error}</p>
        )}
        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={regenerating}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={regenerating}
            className="fv-btn-primary px-5 py-2 text-sm disabled:opacity-50"
          >
            {regenerating ? "Regenerating…" : "Save and regenerate"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ClarifyingQuestionBlock({
  questions,
  intro,
  questionNumberStart = 1,
  submitting = false,
  variant = "default",
  onSubmit,
  pastTurns,
  onEditPast,
}: ClarifyingQuestionBlockProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<ClarifyingQuestionAnswer[]>(() =>
    createEmptyAnswers(questions),
  );
  const [validationError, setValidationError] = useState<string | null>(null);
  const [pastTurnIndex, setPastTurnIndex] = useState<number>(-1);
  const [pastTurnDraftAnswer, setPastTurnDraftAnswer] =
    useState<ClarifyingQuestionAnswer | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [modalDiscardedCount, setModalDiscardedCount] = useState(0);
  const [modalError, setModalError] = useState<string | null>(null);

  useEffect(() => {
    setCurrentIndex(0);
    setAnswers(createEmptyAnswers(questions));
    setValidationError(null);
    setPastTurnIndex(-1);
    setPastTurnDraftAnswer(null);
    setRegenerating(false);
    setConfirmModalOpen(false);
    setModalError(null);
  }, [questions]);

  const inPastTurnMode = pastTurnIndex >= 0 && !!pastTurns?.length;
  const activePastTurn = inPastTurnMode ? pastTurns![pastTurnIndex] : null;

  const currentQuestion: ClarifyingQuestion = inPastTurnMode
    ? activePastTurn!.question
    : questions[currentIndex];

  const currentAnswer: ClarifyingQuestionAnswer = inPastTurnMode
    ? pastTurnDraftAnswer ?? activePastTurn!.answer
    : answers[currentIndex];

  const isFirstInBatch = currentIndex === 0;
  const isFirstOverall =
    inPastTurnMode
      ? pastTurnIndex === 0
      : isFirstInBatch && (!pastTurns || pastTurns.length === 0);

  const isLastInBatch = currentIndex === questions.length - 1;

  const pastAnswerUnchanged =
    inPastTurnMode &&
    activePastTurn &&
    answersEqual(
      pastTurnDraftAnswer ?? activePastTurn.answer,
      activePastTurn.answer,
    );

  const globalQuestionNumber = inPastTurnMode
    ? activePastTurn!.globalQuestionNumber
    : questionNumberStart + currentIndex;

  function updateCurrentAnswer(next: ClarifyingQuestionAnswer) {
    if (inPastTurnMode) {
      setPastTurnDraftAnswer(next);
    } else {
      setAnswers((prev) =>
        prev.map((item, idx) => (idx === currentIndex ? next : item)),
      );
    }
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
    updateCurrentAnswer({
      selectedOptions: [...selected],
      otherText: currentAnswer.otherText,
    });
  }

  function handlePrevious() {
    setValidationError(null);
    if (inPastTurnMode) {
      if (pastTurnIndex > 0) {
        const nextIndex = pastTurnIndex - 1;
        setPastTurnIndex(nextIndex);
        setPastTurnDraftAnswer(cloneAnswer(pastTurns![nextIndex].answer));
      }
      return;
    }
    if (currentIndex > 0) {
      setCurrentIndex((idx) => idx - 1);
      return;
    }
    if (pastTurns && pastTurns.length > 0) {
      const nextIndex = pastTurns.length - 1;
      setPastTurnIndex(nextIndex);
      setPastTurnDraftAnswer(cloneAnswer(pastTurns[nextIndex].answer));
    }
  }

  function exitPastTurnMode() {
    setPastTurnIndex(-1);
    setPastTurnDraftAnswer(null);
  }

  function handleNextInPastMode() {
    if (pastTurnIndex < (pastTurns?.length ?? 0) - 1) {
      const nextIndex = pastTurnIndex + 1;
      setPastTurnIndex(nextIndex);
      setPastTurnDraftAnswer(cloneAnswer(pastTurns![nextIndex].answer));
      return;
    }
    exitPastTurnMode();
  }

  function openConfirmModal() {
    if (!pastTurns || !activePastTurn) return;
    const discardedCount =
      pastTurns.length - 1 - pastTurnIndex + questions.length;
    setModalDiscardedCount(discardedCount);
    setModalError(null);
    setConfirmModalOpen(true);
  }

  async function confirmSaveAndRegenerate() {
    if (!onEditPast || !activePastTurn || pastTurnDraftAnswer === null) return;
    setRegenerating(true);
    setModalError(null);
    try {
      await onEditPast(
        activePastTurn.answerMessageId,
        pastTurnDraftAnswer,
      );
      setConfirmModalOpen(false);
      exitPastTurnMode();
    } catch {
      setModalError("Something went wrong. Please try again.");
    } finally {
      setRegenerating(false);
    }
  }

  function handlePrimaryAction() {
    if (!isQuestionAnswerValid(currentAnswer)) {
      setValidationError(
        "Select at least one option (you can pick multiple) or enter a custom answer.",
      );
      return;
    }
    setValidationError(null);

    if (inPastTurnMode) {
      if (pastAnswerUnchanged) {
        handleNextInPastMode();
        return;
      }
      openConfirmModal();
      return;
    }

    if (isLastInBatch) {
      onSubmit(answers);
      return;
    }
    setCurrentIndex((idx) => idx + 1);
  }

  const busy = submitting || regenerating;

  const primaryLabel = (() => {
    if (busy) {
      return inPastTurnMode && !pastAnswerUnchanged
        ? "Regenerating…"
        : "Submitting…";
    }
    if (inPastTurnMode) {
      return pastAnswerUnchanged ? "Next" : "Save and regenerate";
    }
    return isLastInBatch ? "Submit" : "Next";
  })();

  const isAscent = variant === "ascent" || variant === "peak";
  const isPeak = variant === "peak";
  const isAscentLive = variant === "ascent";

  return (
    <>
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
                    Question {inPastTurnMode ? pastTurnIndex + 1 : currentIndex + 1}{" "}
                    of {inPastTurnMode ? pastTurns!.length : questions.length}
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
                {inPastTurnMode ? pastTurnIndex + 1 : currentIndex + 1} /{" "}
                {inPastTurnMode ? pastTurns!.length : questions.length}
              </p>
            )}
          </div>

          <div className="space-y-6 px-6 py-6">
            {inPastTurnMode && (
              <p className="rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface-raised)] px-4 py-3 text-sm text-[var(--fv-text-muted)]">
                Editing question {globalQuestionNumber} — changes will regenerate
                later questions.
              </p>
            )}

            {intro && currentIndex === 0 && !isAscentLive && !inPastTurnMode && (
              <p className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
                {intro}
              </p>
            )}

            <div>
              <h3 className="text-base font-semibold text-[var(--fv-text)]">
                {isAscentLive
                  ? `${globalQuestionNumber}. ${currentQuestion.question}`
                  : `Q${inPastTurnMode ? pastTurnIndex + 1 : currentIndex + 1}. ${currentQuestion.question}`}
              </h3>
              <p className="mt-1.5 text-xs text-[var(--fv-text-muted)]">
                You can select multiple options — choose every answer that
                applies.
              </p>
            </div>

            <ol className="space-y-3">
              {currentQuestion.options.map((option, optionIndex) => {
                const selected = currentAnswer.selectedOptions.includes(option);

                return (
                  <li key={`${inPastTurnMode ? pastTurnIndex : currentIndex}-${optionIndex}`}>
                    <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--fv-border)] px-4 py-3 transition-colors hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5 has-[:checked]:border-[var(--fv-accent)]/50 has-[:checked]:bg-[var(--fv-accent)]/5">
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={busy}
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
                    disabled={busy}
                    onChange={(e) =>
                      updateCurrentAnswer({
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
              disabled={isFirstOverall || busy}
              className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={handlePrimaryAction}
              disabled={busy}
              className="fv-btn-primary px-5 py-2 text-sm disabled:opacity-50"
            >
              {primaryLabel}
            </button>
          </div>
        </div>
      </div>

      <ConfirmRegenerateModal
        open={confirmModalOpen}
        discardedCount={modalDiscardedCount}
        onCancel={() => {
          if (!regenerating) {
            setConfirmModalOpen(false);
            setModalError(null);
          }
        }}
        onConfirm={() => void confirmSaveAndRegenerate()}
        regenerating={regenerating}
        error={modalError}
      />
    </>
  );
}
