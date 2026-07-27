"use client";

import { useCallback, useState } from "react";
import { useExperimentAnalytics } from "@/hooks/useExperimentAnalytics";
import { useInsightGeneratingStatusPoll } from "@/hooks/useInsightGeneratingStatusPoll";
import type { ExperimentStatus, FounderDecision } from "@/lib/types";
import { PanelHeader } from "@/components/ui/PanelHeader";
import { SignalVerdictEligible } from "./SignalVerdictEligible";
import { SignalVerdictFailed } from "./SignalVerdictFailed";
import { SignalVerdictGenerating } from "./SignalVerdictGenerating";
import { SignalVerdictReady } from "./SignalVerdictReady";
import { SignalWatchingPanel } from "./SignalWatchingPanel";

export type { ExperimentStatus };

export type SignalAct = "evidence" | "launch" | "signal";

export interface SignalStagePanelProps {
  experimentId: string;
  status: ExperimentStatus;
  isOpen: boolean;
  act: SignalAct;
  onOpenLaunch: () => void;
  /** Refresh canvas experiment after insight generation terminal transition. */
  onExperimentRefresh?: () => Promise<void>;
  founderDecision?: FounderDecision | null;
  founderDecisionAt?: string | null;
  founderDecisionNote?: string | null;
  founderDecisionVersion?: number | null;
}

type SignalShellState = "idle" | "watching" | "verdict" | "pending";

type VerdictSubstate = "eligible" | "generating" | "ready" | "failed";

function statusImpliesVerdict(status: ExperimentStatus): boolean {
  return (
    status === "INSIGHT_GENERATING" ||
    status === "INSIGHT_READY" ||
    status === "INSIGHT_FAILED"
  );
}

/**
 * Shell routing (before latch):
 * - Verdict when `insight_threshold_met` (server) OR status is already in the
 *   insight lifecycle (INSIGHT_*).
 * - Watching when status is LANDING_LIVE and threshold is not yet met.
 * - Idle for everything else (including ARCHIVED until data-driven shells).
 *
 * Once Verdict is entered, a mount-lifetime latch keeps the shell on Verdict
 * even if analytics `data` is cleared or a later poll errors.
 */
function deriveShellState(
  status: ExperimentStatus,
  insightThresholdMet: boolean,
): Exclude<SignalShellState, "pending"> {
  if (insightThresholdMet || statusImpliesVerdict(status)) {
    return "verdict";
  }
  if (status === "LANDING_LIVE") {
    return "watching";
  }
  return "idle";
}

function deriveVerdictSubstate(status: ExperimentStatus): VerdictSubstate {
  if (status === "INSIGHT_GENERATING") return "generating";
  if (status === "INSIGHT_FAILED") return "failed";
  if (status === "INSIGHT_READY" || status === "ARCHIVED") {
    return "ready";
  }
  return "eligible";
}

function SignalIdlePlaceholder({ archived }: { archived: boolean }) {
  return (
    <div className="border-2 border-border-master bg-surface-card p-8 shadow-brutal-md">
      <p className="mb-2 font-label-md text-label-md uppercase tracking-wider text-ink-tertiary">
        Idle
      </p>
      {archived ? (
        <>
          <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
            Archived — read-only
          </h2>
          <p className="mt-3 text-body-md text-ink-secondary">
            This experiment is archived. Signal shows no Generate, retry, or
            decision actions.
          </p>
        </>
      ) : (
        <>
          <h2 className="font-headline text-headline-md uppercase tracking-tighter text-ink-primary">
            Signal opens once your landing page is live.
          </h2>
          <p className="mt-3 text-body-md text-ink-secondary">
            Publish from Launch to start metering behavioral evidence here.
          </p>
        </>
      )}
    </div>
  );
}

function SignalShellPending() {
  return (
    <div
      className="border-2 border-border-master bg-surface-card p-8 shadow-brutal-md"
      aria-busy="true"
      aria-label="Loading signal"
    >
      <div className="mb-4 h-6 w-28 border-2 border-border-master bg-surface-elevated" />
      <div className="h-8 w-3/4 border-2 border-border-master bg-surface-elevated" />
      <div className="mt-4 h-4 w-full border-2 border-border-master bg-surface-elevated" />
      <p className="mt-6 font-mono text-mono-sm uppercase text-ink-tertiary">
        Checking threshold…
      </p>
    </div>
  );
}

export function SignalStagePanel({
  experimentId,
  status,
  isOpen,
  act,
  onOpenLaunch,
  onExperimentRefresh,
  founderDecision = null,
  founderDecisionAt = null,
  founderDecisionNote = null,
  founderDecisionVersion = null,
}: SignalStagePanelProps) {
  const [verdictLatched, setVerdictLatched] = useState(false);

  // Poll analytics only while Watching / pending. Latch stops polls on Verdict.
  const analyticsEnabled =
    isOpen &&
    act === "signal" &&
    status === "LANDING_LIVE" &&
    !verdictLatched;

  const { data, loading, error, notAvailable } = useExperimentAnalytics(
    experimentId,
    analyticsEnabled,
  );

  const thresholdMet = data?.insight_threshold_met === true;
  const derived = deriveShellState(status, thresholdMet);

  // Latch during render (React-recommended adjust-state pattern) — replaces
  // useLayoutEffect. A bare ref would not re-render to flip analyticsEnabled off.
  if (derived === "verdict" && !verdictLatched) {
    setVerdictLatched(true);
  }

  // Reopen-flash fix: hold loading until first analytics resolve on LANDING_LIVE.
  const awaitingThreshold =
    status === "LANDING_LIVE" &&
    !statusImpliesVerdict(status) &&
    !verdictLatched &&
    data === null &&
    notAvailable === null &&
    error === null;

  const shell: SignalShellState =
    verdictLatched || derived === "verdict"
      ? "verdict"
      : awaitingThreshold
        ? "pending"
        : derived;

  const archived = status === "ARCHIVED";
  const verdictSubstate =
    shell === "verdict" ? deriveVerdictSubstate(status) : null;

  useInsightGeneratingStatusPoll({
    status,
    enabled: isOpen && act === "signal",
    onExperimentRefresh,
  });

  const handleInsightStarted = useCallback(() => {
    void onExperimentRefresh?.();
  }, [onExperimentRefresh]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-canvas-bg">
      <PanelHeader
        phaseLabel="Phase 05 · Signal"
        title="Metrics + verdict"
      />

      <div className="mx-auto w-full max-w-2xl flex-1 p-6">
        {shell === "pending" ? (
          <SignalShellPending />
        ) : shell === "watching" ? (
          <SignalWatchingPanel
            data={data}
            loading={loading}
            error={error}
            notAvailable={notAvailable}
            onOpenLaunch={onOpenLaunch}
          />
        ) : shell === "verdict" && verdictSubstate === "eligible" ? (
          <SignalVerdictEligible
            experimentId={experimentId}
            archived={archived}
            onInsightStarted={handleInsightStarted}
          />
        ) : shell === "verdict" && verdictSubstate === "generating" ? (
          <SignalVerdictGenerating />
        ) : shell === "verdict" && verdictSubstate === "failed" ? (
          <SignalVerdictFailed
            experimentId={experimentId}
            archived={archived}
            onInsightStarted={handleInsightStarted}
          />
        ) : shell === "verdict" ? (
          <SignalVerdictReady
            experimentId={experimentId}
            archived={archived}
            founderDecision={founderDecision}
            founderDecisionAt={founderDecisionAt}
            founderDecisionNote={founderDecisionNote}
            founderDecisionVersion={founderDecisionVersion}
            onInsightStarted={handleInsightStarted}
            onDecisionRecorded={handleInsightStarted}
          />
        ) : (
          <SignalIdlePlaceholder archived={archived} />
        )}
      </div>
    </div>
  );
}
