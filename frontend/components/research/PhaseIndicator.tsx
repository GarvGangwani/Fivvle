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

type PhaseState = "completed" | "active" | "pending";

function resolvePhaseState(
  phaseId: string,
  currentPhase: string,
  phases: string[],
): PhaseState {
  const phaseIdx = phases.indexOf(phaseId);
  if (phaseIdx === -1) return "pending";

  if (currentPhase === "RESEARCHING") return "pending";

  const currentIdx = phases.indexOf(currentPhase);
  if (currentIdx === -1) return "pending";

  if (phaseIdx < currentIdx) return "completed";
  if (phaseIdx === currentIdx) return "active";
  return "pending";
}

interface PhaseIndicatorProps {
  currentPhase: string;
  phases: string[];
  variant?: "default" | "inline";
}

export function PhaseIndicator({
  currentPhase,
  phases,
  variant = "default",
}: PhaseIndicatorProps) {
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
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/5 text-[var(--fv-text-muted)] ring-2 ring-[var(--fv-border)]">
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
