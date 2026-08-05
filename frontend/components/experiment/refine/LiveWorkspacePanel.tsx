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
  value: Experiment["refined_idea"] | Experiment["refined_idea_current"],
): value is string | RefinedIdea {
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length > 0;
  return Boolean(value.refined_one_liner);
}

function oneLinerOf(
  value: string | RefinedIdea | null | undefined,
): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value.trim() || null;
  return value.refined_one_liner?.trim() || null;
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

  return entries;
}

function RefinementLogViewer({ logEntries }: { logEntries: LogEntry[] }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (logEntries.length > 0) {
      setCurrentIndex(logEntries.length - 1);
    }
  }, [logEntries.length]);

  if (logEntries.length === 0) {
    return (
      <div className="rounded-md border-2 border-dashed border-border-master p-4">
        <p className="font-body text-body-sm text-ink-tertiary italic">
          Questions and your answers will appear here as you go.
        </p>
      </div>
    );
  }

  const safeIndex = Math.min(currentIndex, logEntries.length - 1);
  const entry = logEntries[safeIndex];
  const totalCount = logEntries.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <button
          type="button"
          onClick={() => setCurrentIndex(Math.max(0, safeIndex - 1))}
          disabled={safeIndex === 0}
          className="p-1 disabled:opacity-30 hover:bg-surface-elevated"
          aria-label="Previous question"
        >
          <span
            className="material-symbols-outlined text-ink-secondary"
            style={{ fontSize: 18 }}
            aria-hidden="true"
          >
            chevron_left
          </span>
        </button>
        <span className="font-mono text-mono-sm uppercase text-ink-secondary tabular-nums">
          Q{safeIndex + 1} / {totalCount}
        </span>
        <button
          type="button"
          onClick={() =>
            setCurrentIndex(Math.min(totalCount - 1, safeIndex + 1))
          }
          disabled={safeIndex === totalCount - 1}
          className="p-1 disabled:opacity-30 hover:bg-surface-elevated"
          aria-label="Next question"
        >
          <span
            className="material-symbols-outlined text-ink-secondary"
            style={{ fontSize: 18 }}
            aria-hidden="true"
          >
            chevron_right
          </span>
        </button>
      </div>
      <LogEntryCard entry={entry} />
    </div>
  );
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
  const [justUpdated, setJustUpdated] = useState(false);
  const lastWip = useRef(experiment.refined_idea_current);

  const wipIdea = experiment.refined_idea_current;
  const finalizedOneLiner = oneLinerOf(experiment.refined_idea);
  const wipOneLiner = oneLinerOf(wipIdea);
  const hasWip = hasRefinedIdeaValue(wipIdea);
  const hasFinalized = Boolean(finalizedOneLiner);
  const isFinalized = experiment.status === "REFINED" && hasFinalized;
  const wipDiffers =
    isFinalized &&
    hasWip &&
    Boolean(wipOneLiner) &&
    wipOneLiner !== finalizedOneLiner;

  const cardIdea: string | RefinedIdea | null = hasWip
    ? (wipIdea as string | RefinedIdea)
    : hasFinalized
      ? (experiment.refined_idea as string | RefinedIdea)
      : null;

  const canFinalize = hasWip && (!isFinalized || wipDiffers);

  const latestAssistantMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === "assistant"),
    [messages],
  );

  const isReadyToFinalize = useMemo(() => {
    if (!latestAssistantMessage || !hasWip) return false;
    if (isFinalized && !wipDiffers) return false;
    const questions = latestAssistantMessage.clarifying_questions ?? [];
    return questions.length === 0;
  }, [latestAssistantMessage, hasWip, isFinalized, wipDiffers]);

  /** Pending MCQ lives on the refine thread; answering is master-rail-native. */
  const hasPendingMcq = useMemo(() => {
    if (messages.length === 0) return false;
    const last = messages[messages.length - 1];
    if (last.role !== "assistant") return false;
    const questions = last.clarifying_questions ?? [];
    return questions.some((q) => q.options.length >= 2);
  }, [messages]);

  const logEntries = useMemo(
    () => extractRefinementLog(messages),
    [messages],
  );

  useEffect(() => {
    const changed =
      JSON.stringify(experiment.refined_idea_current) !==
      JSON.stringify(lastWip.current);
    if (changed && experiment.refined_idea_current) {
      setFlashKey((k) => k + 1);
      lastWip.current = experiment.refined_idea_current;
    }
  }, [experiment.refined_idea_current]);

  useEffect(() => {
    if (flashKey === 0) return;
    setJustUpdated(true);
    const timer = window.setTimeout(() => setJustUpdated(false), 1600);
    return () => window.clearTimeout(timer);
  }, [flashKey]);

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

  const finalizeLabel = (() => {
    if (isFinalized && !wipDiffers) return "FINALIZED";
    if (wipDiffers) return "UPDATE FINAL VERSION";
    return "FINALIZE REFINEMENT";
  })();

  return (
    <div className="p-6 flex flex-col h-full overflow-y-auto">
      <div className="font-mono text-mono-sm uppercase text-accent mb-6 tracking-wider">
        LIVE WORKSPACE
      </div>

      {hasPendingMcq ? (
        <div className="mb-4 rounded-md border-2 border-border-master bg-surface-elevated p-3 flex items-start gap-3">
          <span
            className="material-symbols-outlined text-ink-primary shrink-0 mt-0.5"
            style={{ fontSize: 20 }}
            aria-hidden="true"
          >
            chat
          </span>
          <div>
            <p className="font-mono text-mono-sm uppercase text-ink-primary font-bold mb-1">
              PENDING CLARIFYING QUESTION
            </p>
            <p className="font-body text-body-sm text-ink-primary">
              Answer the question in the master rail.
            </p>
          </div>
        </div>
      ) : null}

      {isReadyToFinalize ? (
        <div className="mb-4 rounded-md border-2 border-brutalist-yellow bg-brutalist-yellow/20 p-3 flex items-start gap-3">
          <span
            className="material-symbols-outlined text-ink-primary shrink-0 mt-0.5"
            style={{ fontSize: 20 }}
            aria-hidden="true"
          >
            check_circle
          </span>
          <div>
            <p className="font-mono text-mono-sm uppercase text-ink-primary font-bold mb-1">
              REFINEMENT COMPLETE
            </p>
            <p className="font-body text-body-sm text-ink-primary">
              The Refiner is done. Hit FINALIZE to lock in your refined idea and
              move to Evidence, or keep refining in the master rail.
            </p>
          </div>
        </div>
      ) : null}

      {cardIdea ? (
        <div className="mb-6">
          <RefinedIdeaCard
            refinedIdea={cardIdea}
            isFinalized={isFinalized}
            isJustUpdated={justUpdated}
            wipDiffers={wipDiffers}
          />
        </div>
      ) : null}

      <div className="mb-6">
        <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-2">
          REFINEMENT LOG
        </div>
        <RefinementLogViewer logEntries={logEntries} />
      </div>

      <div className="mb-6">
        <div className="font-mono text-mono-sm uppercase text-ink-tertiary mb-2">
          ORIGIN · FROM SPARK v{experiment.current_spark_version || 1}
        </div>
        <div className="rounded-md border-2 border-dashed border-border-master p-3 bg-surface-elevated">
          <p className="font-body text-body-sm text-ink-secondary italic line-clamp-3">
            &ldquo;{experiment.raw_idea?.trim() || "No idea captured in Spark yet."}
            &rdquo;
          </p>
        </div>
      </div>

      <div className="flex-1" />

      {error ? (
        <div className="rounded-md border-2 border-status-critical bg-status-critical/10 p-3 mb-4">
          <p className="font-body text-body-sm text-status-critical">{error}</p>
        </div>
      ) : null}

      <div className="space-y-3">
        <button
          type="button"
          onClick={() => setFinalizeConfirm(true)}
          disabled={!canFinalize || finalizing}
          className={`w-full rounded-sm px-6 py-4 border-2 border-border-master font-label-md text-label-md uppercase tracking-wider shadow-brutal-md hover:shadow-brutal-lg hover:-translate-x-0.5 hover:-translate-y-0.5 active:translate-x-0 active:translate-y-0 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 ${
            isFinalized && !wipDiffers
              ? "bg-status-success text-ink-inverse"
              : "bg-brutalist-yellow text-ink-primary"
          } ${isReadyToFinalize ? "animate-pulse" : ""}`}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 18 }}
            aria-hidden="true"
          >
            {isFinalized && !wipDiffers ? "check_circle" : "rocket_launch"}
          </span>
          {finalizeLabel}
        </button>
        {!hasWip ? (
          <p className="font-body text-body-sm text-ink-tertiary text-center">
            Keep refining in the master rail until a refined idea appears here.
          </p>
        ) : null}
        {canFinalize ? (
          <p className="font-body text-body-sm text-ink-tertiary text-center">
            {wipDiffers
              ? "WIP has changed since the last finalize. Update the final version when ready."
              : "Locks in this refinement. Research still requires Confirm (credits) on Evidence."}
          </p>
        ) : null}
        <button
          type="button"
          onClick={() => setResetConfirm(true)}
          className="w-full rounded-sm border-2 border-border-master bg-surface-card px-6 py-3 font-label-md text-label-md uppercase tracking-wider hover:shadow-brutal-sm transition-all"
        >
          RESET SESSION
        </button>
      </div>

      {finalizeConfirm ? (
        <BrutalistConfirm
          title={wipDiffers ? "Update final version?" : "Finalize this refinement?"}
          body="This marks the current refined idea as ready. You can keep refining in the master rail and re-finalize later. Research still requires Confirm (credits) on Evidence."
          confirmLabel={wipDiffers ? "UPDATE FINAL" : "FINALIZE"}
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
