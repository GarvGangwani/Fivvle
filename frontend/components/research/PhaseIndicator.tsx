import { Check, Loader2 } from "lucide-react";

export const RESEARCH_PHASE_IDS = [
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
] as const;

export const RESEARCH_PHASE_LABELS: Record<
  (typeof RESEARCH_PHASE_IDS)[number],
  string
> = {
  RESEARCH_PLANNING: "Planning research strategy",
  RESEARCH_SEARCHING: "Searching market signals",
  RESEARCH_READING: "Reading sources & competitors",
  RESEARCH_REFLECTING: "Reflecting on findings",
  RESEARCH_SYNTHESIZING: "Synthesizing validation report",
};

export const RESEARCH_PHASE_SHORT_LABELS: Record<
  (typeof RESEARCH_PHASE_IDS)[number],
  string
> = {
  RESEARCH_PLANNING: "Plan",
  RESEARCH_SEARCHING: "Search",
  RESEARCH_READING: "Read",
  RESEARCH_REFLECTING: "Reflect",
  RESEARCH_SYNTHESIZING: "Synthesize",
};

type PhaseState = "completed" | "active" | "pending";

function resolvePhaseState(
  phaseId: string,
  currentPhase: string,
  phases: string[],
): PhaseState {
  if (currentPhase === "RESEARCH_READY") return "completed";

  const phaseIdx = phases.indexOf(phaseId);
  if (phaseIdx === -1) return "pending";

  if (currentPhase === "RESEARCHING") return "pending";

  const currentIdx = phases.indexOf(currentPhase);
  if (currentIdx === -1) return "pending";

  if (phaseIdx < currentIdx) return "completed";
  if (phaseIdx === currentIdx) return "active";
  return "pending";
}

function activePhaseIndex(currentPhase: string, phases: string[]): number {
  if (currentPhase === "RESEARCH_READY") return phases.length;
  if (currentPhase === "RESEARCHING") return -1;
  const idx = phases.indexOf(currentPhase);
  return idx === -1 ? -1 : idx;
}

interface PhaseIndicatorProps {
  currentPhase: string;
  phases: string[];
  variant?: "default" | "inline" | "horizontal";
}

function HorizontalPhaseBar({
  currentPhase,
  phases,
}: {
  currentPhase: string;
  phases: string[];
}) {
  const activeIdx = activePhaseIndex(currentPhase, phases);
  const progressPercent =
    activeIdx < 0
      ? 0
      : activeIdx >= phases.length
        ? 100
        : ((activeIdx + 0.5) / phases.length) * 100;

  const activePhaseId =
    activeIdx >= 0 && activeIdx < phases.length ? phases[activeIdx] : null;
  const activeLabel = activePhaseId
    ? (RESEARCH_PHASE_LABELS[
        activePhaseId as (typeof RESEARCH_PHASE_IDS)[number]
      ] ?? activePhaseId)
    : null;

  return (
    <div className="fv-phase-bar" role="group" aria-label="Research progress">
      <div
        className="fv-phase-bar-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={phases.length}
        aria-valuenow={activeIdx < 0 ? 0 : Math.min(activeIdx + 1, phases.length)}
        aria-valuetext={activeLabel ?? "Starting research"}
      >
        <div
          className="fv-phase-bar-fill"
          style={{ width: `${progressPercent}%` }}
          aria-hidden
        />
        <ol className="fv-phase-bar-nodes">
          {phases.map((phaseId, index) => {
            const state = resolvePhaseState(phaseId, currentPhase, phases);
            const shortLabel =
              RESEARCH_PHASE_SHORT_LABELS[
                phaseId as (typeof RESEARCH_PHASE_IDS)[number]
              ] ?? `Step ${index + 1}`;

            return (
              <li
                key={phaseId}
                className="fv-phase-bar-node"
                aria-current={state === "active" ? "step" : undefined}
              >
                <span
                  className={`fv-phase-bar-dot fv-phase-bar-dot--${state}`}
                  title={
                    RESEARCH_PHASE_LABELS[
                      phaseId as (typeof RESEARCH_PHASE_IDS)[number]
                    ]
                  }
                >
                  {state === "completed" ? (
                    <Check className="h-3 w-3" strokeWidth={2.5} aria-hidden />
                  ) : state === "active" ? (
                    <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                  ) : null}
                </span>
                <span
                  className={`fv-phase-bar-node-label fv-phase-bar-node-label--${state}`}
                >
                  {shortLabel}
                </span>
              </li>
            );
          })}
        </ol>
      </div>

      {activeLabel && activeIdx >= 0 && activeIdx < phases.length ? (
        <p className="fv-phase-bar-caption">
          <span className="font-medium text-[var(--fv-text)]">{activeLabel}</span>
          <span className="text-[var(--fv-text-muted)]">
            {" "}
            · Step {activeIdx + 1} of {phases.length}
          </span>
        </p>
      ) : activeIdx >= phases.length ? (
        <p className="fv-phase-bar-caption font-medium text-[var(--fv-success)]">
          All research phases complete
        </p>
      ) : (
        <p className="fv-phase-bar-caption text-[var(--fv-text-muted)]">
          Starting research pipeline…
        </p>
      )}
    </div>
  );
}

export function PhaseIndicator({
  currentPhase,
  phases,
  variant = "default",
}: PhaseIndicatorProps) {
  if (variant === "horizontal") {
    return <HorizontalPhaseBar currentPhase={currentPhase} phases={phases} />;
  }

  if (variant === "inline") {
    return (
      <div>
        {phases.map((phaseId, index) => {
          const state = resolvePhaseState(phaseId, currentPhase, phases);
          const label =
            RESEARCH_PHASE_LABELS[
              phaseId as (typeof RESEARCH_PHASE_IDS)[number]
            ] ?? phaseId;
          const isLast = index === phases.length - 1;

          return (
            <div key={phaseId}>
              <div className="flex items-center gap-3 py-2.5">
                <span
                  className={`stage-dot ${
                    state === "completed"
                      ? "done"
                      : state === "active"
                        ? "active"
                        : "pending"
                  }`}
                />
                <span
                  className={`flex-1 text-[13px] ${
                    state === "completed"
                      ? "text-fv-success"
                      : state === "active"
                        ? "text-[var(--fv-text)]"
                        : "text-fv-text-dim"
                  }`}
                >
                  {label}
                </span>
                {state === "completed" && (
                  <Check className="h-[13px] w-[13px] shrink-0 text-fv-success" />
                )}
                {state === "active" && <span className="fv-stage-spinner" />}
              </div>
              {!isLast && (
                <div
                  className="ml-[3px] h-px"
                  style={{ background: "rgba(255,255,255,0.04)" }}
                />
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <ol className="space-y-0">
      {phases.map((phaseId, index) => {
        const state = resolvePhaseState(phaseId, currentPhase, phases);
        const label =
          RESEARCH_PHASE_LABELS[
            phaseId as (typeof RESEARCH_PHASE_IDS)[number]
          ] ?? phaseId;
        const isLast = index === phases.length - 1;

        return (
          <li key={phaseId} className="relative flex gap-4 pb-8 last:pb-0">
            {!isLast && (
              <span
                className={`absolute left-[15px] top-8 h-[calc(100%-2rem)] w-0.5 ${
                  state === "completed"
                    ? "bg-[var(--fv-accent)]"
                    : "bg-[var(--fv-border)]"
                }`}
                aria-hidden
              />
            )}

            <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
              {state === "completed" && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-2 ring-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]">
                  <Check className="h-4 w-4" strokeWidth={2.5} />
                </span>
              )}
              {state === "active" && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-2 ring-[var(--fv-accent)]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </span>
              )}
              {state === "pending" && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--fv-hover-overlay)] text-[var(--fv-text-muted)] ring-2 ring-[var(--fv-border)]">
                  <span className="h-2 w-2 rounded-full bg-[var(--fv-text-muted)]" />
                </span>
              )}
            </div>

            <div className="min-w-0 pt-1">
              <p
                className={`text-sm font-medium ${
                  state === "active"
                    ? "text-[var(--fv-accent)]"
                    : state === "completed"
                      ? "text-[var(--fv-text)]"
                      : "text-[var(--fv-text-muted)]"
                }`}
              >
                {label}
              </p>
              {state === "active" && (
                <p className="mt-0.5 text-xs text-[var(--fv-accent)]">
                  In progress…
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
