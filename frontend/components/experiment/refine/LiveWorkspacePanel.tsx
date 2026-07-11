"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  finalizeRefinement,
  resetRefineSession,
} from "@/lib/api";
import type { Experiment, RefinedIdea } from "@/lib/types";
import { BrutalistConfirm } from "./BrutalistConfirm";
import { LogEntryCard, type LogEntry } from "./LogEntryCard";
import { RefinedIdeaCard } from "./RefinedIdeaCard";
import type { RefineChatMessageModel } from "./RefineChatMessage";

type Props = {
  experiment: Experiment;
  messages: RefineChatMessageModel[];
  onFinalized: () => Promise<void>;
  onReset: () => Promise<void>;
};

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const body = err.body;
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

function hasRefinedIdeaValue(
  value: Experiment["refined_idea"],
): value is string | RefinedIdea {
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length > 0;
  return Boolean(value.refined_one_liner);
}

function extractRefinementLog(
  messages: RefineChatMessageModel[],
): LogEntry[] {
  const entries: LogEntry[] = [];

  for (let i = 0; i < messages.length; i += 1) {
    const msg = messages[i];
    if (msg.role !== "assistant") continue;

    const questions = msg.clarifying_questions ?? [];
    const mcqQuestion = questions.find((q) => q.options.length >= 2);
    if (!mcqQuestion) continue;

    const userAnswer = messages.slice(i + 1).find((m) => m.role === "user");
    if (!userAnswer) continue;

    entries.push({
      question: mcqQuestion.question,
      options: mcqQuestion.options,
      selectedIndices: userAnswer.metadata?.selected_option_indices ?? [],
      customAddedText: userAnswer.metadata?.custom_added_text ?? null,
      rawAnswer: userAnswer.content,
      timestamp: userAnswer.created_at,
    });
  }

  return entries.reverse();
}

export function LiveWorkspacePanel({
  experiment,
  messages,
  onFinalized,
  onReset,
}: Props) {
  const [finalizing, setFinalizing] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetConfirm, setResetConfirm] = useState(false);
  const [finalizeConfirm, setFinalizeConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashKey, setFlashKey] = useState(0);
  const lastRefinedIdea = useRef(experiment.refined_idea);

  const hasRefinedIdea = hasRefinedIdeaValue(experiment.refined_idea);
  const isFinalized = experiment.status === "REFINED";
  const logEntries = useMemo(
    () => extractRefinementLog(messages),
    [messages],
  );

  useEffect(() => {
    const changed =
      JSON.stringify(experiment.refined_idea) !==
      JSON.stringify(lastRefinedIdea.current);
    if (changed && experiment.refined_idea) {
      setFlashKey((k) => k + 1);
      lastRefinedIdea.current = experiment.refined_idea;
    }
  }, [experiment.refined_idea]);

  const handleFinalize = async () => {
    setFinalizing(true);
    setError(null);
    try {
      await finalizeRefinement(experiment.id);
      await onFinalized();
      setFinalizeConfirm(false);
    } catch (err: unknown) {
      setError(errorMessage(err, "Could not finalize"));
    } finally {
      setFinalizing(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    setError(null);
    try {
      await resetRefineSession(experiment.id);
      await onReset();
      setResetConfirm(false);
    } catch (err: unknown) {
      setError(errorMessage(err, "Could not reset"));
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="p-6 flex flex-col h-full overflow-y-auto">
      <div className="font-mono text-mono-sm uppercase text-brand-primary mb-6 tracking-wider">
        LIVE WORKSPACE
      </div>

      {hasRefinedIdea ? (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div className="font-mono text-mono-sm uppercase text-ink-tertiary">
              CURRENT REFINEMENT
            </div>
            {flashKey > 0 ? (
              <span
                key={flashKey}
                className="font-mono text-mono-sm uppercase text-brand-primary animate-pulse"
                style={{ animationIterationCount: 2, animationDuration: "0.6s" }}
              >
                JUST UPDATED
              </span>
            ) : null}
          </div>
          <RefinedIdeaCard
            refinedIdea={experiment.refined_idea as string | RefinedIdea}
            isFinalized={isFinalized}
          />
        </div>
      ) : null}

      <div className="mb-6">
        <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-2">
          REFINEMENT LOG
        </div>
        {logEntries.length === 0 ? (
          <div className="border-2 border-dashed border-border-master p-4">
            <p className="font-body text-body-sm text-ink-tertiary italic">
              Questions and your answers will appear here as you go.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {logEntries.map((entry, i) => (
              <LogEntryCard
                key={`${entry.timestamp}-${i}-${entry.question.slice(0, 16)}`}
                entry={entry}
              />
            ))}
          </div>
        )}
      </div>

      <div className="mb-6">
        <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-2">
          ORIGIN · FROM SPARK v{experiment.current_spark_version || 1}
        </div>
        <div className="border-2 border-dashed border-border-master p-3 bg-surface-elevated">
          <p className="font-body text-body-sm text-ink-secondary italic line-clamp-3">
            &ldquo;{experiment.raw_idea?.trim() || "No idea captured in Spark yet."}
            &rdquo;
          </p>
        </div>
      </div>

      <div className="flex-1" />

      {error ? (
        <div className="border-2 border-status-critical bg-status-critical/10 p-3 mb-4">
          <p className="font-body text-body-sm text-status-critical">{error}</p>
        </div>
      ) : null}

      <div className="space-y-3">
        <button
          type="button"
          onClick={() => setFinalizeConfirm(true)}
          disabled={!hasRefinedIdea || finalizing || isFinalized}
          className={`w-full px-6 py-4 border-2 border-border-master font-label-md text-label-md uppercase tracking-wider shadow-brutal-md hover:shadow-brutal-lg hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 ${
            isFinalized
              ? "bg-status-success text-ink-inverse"
              : "bg-brutalist-yellow text-ink-primary"
          }`}
        >
          {isFinalized ? (
            <>
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 18 }}
              >
                check_circle
              </span>
              FINALIZED
            </>
          ) : (
            <>
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 18 }}
              >
                rocket_launch
              </span>
              FINALIZE REFINEMENT
            </>
          )}
        </button>
        {!hasRefinedIdea ? (
          <p className="font-body text-body-sm text-ink-tertiary text-center">
            Continue the conversation until the Refiner produces a refined idea.
          </p>
        ) : null}
        {hasRefinedIdea && !isFinalized ? (
          <p className="font-body text-body-sm text-ink-tertiary text-center">
            Locks in this refinement. Research still requires Confirm (credits)
            on Evidence.
          </p>
        ) : null}
        <button
          type="button"
          onClick={() => setResetConfirm(true)}
          className="w-full border-2 border-border-master bg-surface-card px-6 py-3 font-label-md text-label-md uppercase tracking-wider hover:shadow-brutal-sm transition-all"
        >
          RESET SESSION
        </button>
      </div>

      {finalizeConfirm ? (
        <BrutalistConfirm
          title="Finalize this refinement?"
          body="This marks the current refined idea as ready. You can keep refining and re-finalize later. Research still requires Confirm (credits) on Evidence."
          confirmLabel="FINALIZE"
          cancelLabel="CANCEL"
          onConfirm={handleFinalize}
          onCancel={() => setFinalizeConfirm(false)}
          loading={finalizing}
        />
      ) : null}
      {resetConfirm ? (
        <BrutalistConfirm
          title="Reset this session?"
          body="This deletes all Refine chat messages and clears the refined idea. Your Spark idea and attachments stay safe."
          confirmLabel="RESET"
          cancelLabel="CANCEL"
          onConfirm={handleReset}
          onCancel={() => setResetConfirm(false)}
          loading={resetting}
          variant="critical"
        />
      ) : null}
    </div>
  );
}
