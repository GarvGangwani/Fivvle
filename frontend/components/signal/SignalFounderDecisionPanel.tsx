"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  ApiError,
  getExperiment,
  recordFounderDecision,
  type FounderDecisionResponse,
} from "@/lib/api";
import type { FounderDecision } from "@/lib/types";

const NOTE_MAX = 500;

const DECISIONS: {
  id: FounderDecision;
  label: string;
  description: string;
  destructive?: boolean;
  primary?: boolean;
}[] = [
  {
    id: "iterate",
    label: "Iterate",
    description:
      "Refine the landing page or positioning and keep collecting signal before committing.",
  },
  {
    id: "proceed",
    label: "Move forward",
    description:
      "Validation looks promising — proceed to build the MVP or next experiment phase.",
    primary: true,
  },
  {
    id: "pivot",
    label: "Pivot",
    description:
      "Shift the idea based on what you learned. The project stays open — archive separately if you want to file it away.",
    destructive: true,
  },
  {
    id: "kill",
    label: "Kill",
    description:
      "Stop pursuing this idea. Recording kill is a conclusion only — it does not archive the project.",
    destructive: true,
  },
];

function formatDecisionLabel(decision: FounderDecision): string {
  const found = DECISIONS.find((d) => d.id === decision);
  return found?.label ?? decision;
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function readConflictVersion(err: ApiError): number | null {
  const body = err.body;
  if (!body || typeof body !== "object") return null;
  const detail = (body as { detail?: unknown }).detail;
  if (!detail || typeof detail !== "object") return null;
  const current = (detail as { current_version?: unknown }).current_version;
  return typeof current === "number" ? current : null;
}

type Recorded = {
  decision: FounderDecision;
  at: string;
  note: string | null;
  version: number;
};

type Props = {
  experimentId: string;
  archived: boolean;
  initialDecision: FounderDecision | null;
  initialAt: string | null;
  initialNote: string | null;
  initialVersion: number | null;
  onRecorded: () => void;
};

/**
 * Founder Signal decision — persists via PUT /founder-decision.
 * Does not archive. Amendable with CAS on founder_decision_version.
 */
export function SignalFounderDecisionPanel({
  experimentId,
  archived,
  initialDecision,
  initialAt,
  initialNote,
  initialVersion,
  onRecorded,
}: Props) {
  const [recorded, setRecorded] = useState<Recorded | null>(() =>
    initialDecision && initialAt && initialVersion != null
      ? {
          decision: initialDecision,
          at: initialAt,
          note: initialNote,
          version: initialVersion,
        }
      : null,
  );
  const [amending, setAmending] = useState(false);
  const [selected, setSelected] = useState<FounderDecision | null>(null);
  const [note, setNote] = useState("");
  const [confirming, setConfirming] = useState<"pivot" | "kill" | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictNotice, setConflictNotice] = useState<string | null>(null);
  /** Version for the next write — 0 until first record. */
  const [baseVersion, setBaseVersion] = useState(initialVersion ?? 0);

  useEffect(() => {
    if (initialDecision && initialAt && initialVersion != null) {
      setRecorded({
        decision: initialDecision,
        at: initialAt,
        note: initialNote,
        version: initialVersion,
      });
      setBaseVersion(initialVersion);
      setAmending(false);
    } else {
      setRecorded(null);
      setBaseVersion(0);
    }
  }, [initialDecision, initialAt, initialNote, initialVersion]);

  const showForm = !archived && (!recorded || amending);

  async function refreshFromServer() {
    const exp = await getExperiment(experimentId);
    if (exp.founder_decision && exp.founder_decision_at && exp.founder_decision_version != null) {
      setRecorded({
        decision: exp.founder_decision,
        at: exp.founder_decision_at,
        note: exp.founder_decision_note ?? null,
        version: exp.founder_decision_version,
      });
      setBaseVersion(exp.founder_decision_version);
    } else {
      setRecorded(null);
      setBaseVersion(0);
    }
    onRecorded();
  }

  async function executeDecision(decision: FounderDecision) {
    setSubmitting(true);
    setError(null);
    setConflictNotice(null);
    try {
      const result: FounderDecisionResponse = await recordFounderDecision(
        experimentId,
        {
          decision,
          note: note.trim() ? note.trim() : null,
          base_version: baseVersion,
        },
      );
      setRecorded({
        decision: result.founder_decision,
        at: result.founder_decision_at,
        note: result.founder_decision_note,
        version: result.founder_decision_version,
      });
      setBaseVersion(result.founder_decision_version);
      setAmending(false);
      setSelected(null);
      setConfirming(null);
      setNote("");
      onRecorded();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const conflictVersion = readConflictVersion(err);
        if (conflictVersion !== null) {
          setConflictNotice(
            "Your decision was updated elsewhere. We’ve refreshed the latest version — review it and try again.",
          );
          try {
            await refreshFromServer();
          } catch {
            setBaseVersion(conflictVersion);
          }
          setAmending(true);
          setConfirming(null);
          return;
        }
        setError(
          "Could not save your decision (conflict). Refresh and try again.",
        );
        return;
      }
      setError("Could not save your decision. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handlePick(decision: FounderDecision) {
    setSelected(decision);
    setError(null);
    const option = DECISIONS.find((d) => d.id === decision);
    if (option?.destructive) {
      setConfirming(decision as "pivot" | "kill");
      return;
    }
    void executeDecision(decision);
  }

  if (archived && !recorded) {
    return (
      <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
        <p className="font-label-md text-label-md uppercase tracking-wider text-ink-tertiary">
          Your decision
        </p>
        <p className="mt-2 text-body-md text-ink-secondary">
          No decision was recorded before this project was archived.
        </p>
      </section>
    );
  }

  if (archived && recorded) {
    return (
      <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
        <p className="mb-2 font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
          Your decision · read-only
        </p>
        <RecordedSummary recorded={recorded} />
      </section>
    );
  }

  if (recorded && !amending) {
    return (
      <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
              Your decision
            </p>
            <h2 className="mt-1 font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
              Recorded conclusion
            </h2>
          </div>
          <button
            type="button"
            onClick={() => {
              setAmending(true);
              setSelected(recorded.decision);
              setNote(recorded.note ?? "");
              setError(null);
              setConflictNotice(null);
            }}
            className="border-2 border-border-master bg-surface-elevated px-3 py-1.5 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm"
          >
            Change decision
          </button>
        </div>
        <RecordedSummary recorded={recorded} />
      </section>
    );
  }

  return (
    <section className="border-2 border-border-master bg-surface-card p-5 shadow-brutal-md">
      <p className="font-label-md text-label-sm uppercase tracking-wider text-ink-tertiary">
        Your decision
      </p>
      <h2 className="mt-1 font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
        {recorded ? "Change your conclusion" : "Record your conclusion"}
      </h2>
      <p className="mt-2 text-body-md text-ink-secondary">
        {recorded
          ? "Update what you decided based on this insight. This overwrites the previous conclusion — it does not archive the project."
          : "What do you conclude from this insight? Recording a decision keeps the project open and readable."}
      </p>

      {conflictNotice ? (
        <p
          role="status"
          className="mt-4 border-2 border-border-master bg-brutalist-yellow px-3 py-2 text-body-sm text-ink-primary shadow-brutal-sm"
        >
          {conflictNotice}
        </p>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="mt-4 border-2 border-border-master bg-surface-elevated px-3 py-2 text-body-sm text-ink-secondary"
        >
          {error}
        </p>
      ) : null}

      {showForm ? (
        <>
          <label className="mt-6 block">
            <span className="font-label-md text-label-sm uppercase tracking-wider text-ink-primary">
              Why this decision
            </span>
            <span className="mt-1 block text-body-sm text-ink-secondary">
              Optional, but the rationale is what makes this defensible later.
            </span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value.slice(0, NOTE_MAX))}
              maxLength={NOTE_MAX}
              rows={3}
              disabled={submitting}
              placeholder="What evidence or judgment led you here?"
              className="mt-2 w-full resize-y border-2 border-border-master bg-surface-elevated px-3 py-2 text-body-md text-ink-primary placeholder:text-ink-tertiary focus:outline-none focus:ring-2 focus:ring-ink-primary"
            />
            <span className="mt-1 block text-right font-mono text-mono-sm text-ink-tertiary">
              {note.length} / {NOTE_MAX}
            </span>
          </label>

          {confirming ? (
            <div className="mt-6 space-y-4 border-2 border-status-critical bg-surface-elevated p-4 shadow-brutal-sm">
              <p className="text-body-md text-ink-primary">
                Confirm you want to record{" "}
                <strong className="uppercase">{confirming}</strong> as your
                conclusion? The project stays open — archive separately if you
                want to file it away.
              </p>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => void executeDecision(confirming)}
                  className="border-2 border-border-master bg-status-critical px-4 py-2 font-label-md text-label-sm uppercase tracking-wider text-ink-inverse shadow-brutal-sm disabled:opacity-50"
                >
                  {submitting ? (
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving…
                    </span>
                  ) : (
                    "Confirm conclusion"
                  )}
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => {
                    setConfirming(null);
                    setSelected(null);
                  }}
                  className="border-2 border-border-master bg-surface-card px-4 py-2 font-label-md text-label-sm uppercase tracking-wider text-ink-primary disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {DECISIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  disabled={submitting}
                  onClick={() => handlePick(option.id)}
                  className={`flex flex-col border-2 border-border-master p-4 text-left shadow-brutal-sm transition-transform enabled:hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 ${
                    option.primary
                      ? "bg-brutalist-yellow text-ink-primary"
                      : option.destructive
                        ? "bg-surface-elevated text-ink-primary"
                        : "bg-surface-card text-ink-primary"
                  } ${selected === option.id ? "ring-2 ring-ink-primary" : ""}`}
                >
                  <span className="flex items-center gap-2 font-label-md text-label-md uppercase tracking-wider">
                    {submitting && selected === option.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    {option.label}
                  </span>
                  <span className="mt-2 text-body-sm leading-relaxed text-ink-secondary">
                    {option.description}
                  </span>
                </button>
              ))}
            </div>
          )}

          {recorded && amending ? (
            <button
              type="button"
              disabled={submitting}
              onClick={() => {
                setAmending(false);
                setConfirming(null);
                setSelected(null);
                setNote("");
                setError(null);
                setConflictNotice(null);
              }}
              className="mt-4 font-label-md text-label-sm uppercase tracking-wider text-ink-secondary underline decoration-2 underline-offset-4"
            >
              Cancel change
            </button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function RecordedSummary({ recorded }: { recorded: Recorded }) {
  return (
    <div className="space-y-3">
      <div className="inline-block border-2 border-border-master bg-brutalist-yellow px-3 py-1 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm">
        {formatDecisionLabel(recorded.decision)}
      </div>
      <p className="font-mono text-mono-sm uppercase text-ink-tertiary">
        Recorded {formatTimestamp(recorded.at)}
      </p>
      {recorded.note ? (
        <p className="border-2 border-border-master bg-surface-elevated p-3 text-body-md text-ink-primary">
          {recorded.note}
        </p>
      ) : (
        <p className="text-body-sm text-ink-tertiary">No rationale noted.</p>
      )}
    </div>
  );
}
