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
  RESEARCH_PLANNING: "Planning",
  RESEARCH_SEARCHING: "Searching",
  RESEARCH_READING: "Reading",
  RESEARCH_REFLECTING: "Reflecting",
  RESEARCH_SYNTHESIZING: "Synthesizing",
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
}

export function PhaseIndicator({ currentPhase, phases }: PhaseIndicatorProps) {
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
                  state === "completed" ? "bg-green-300" : "bg-gray-200"
                }`}
                aria-hidden
              />
            )}

            <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
              {state === "completed" && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 text-green-700 ring-2 ring-green-200">
                  <Check className="h-4 w-4" strokeWidth={2.5} />
                </span>
              )}
              {state === "active" && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700 ring-2 ring-blue-300">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </span>
              )}
              {state === "pending" && (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-400 ring-2 ring-gray-200">
                  <span className="h-2 w-2 rounded-full bg-gray-300" />
                </span>
              )}
            </div>

            <div className="min-w-0 pt-1">
              <p
                className={`text-sm font-medium ${
                  state === "active"
                    ? "text-blue-900"
                    : state === "completed"
                      ? "text-gray-900"
                      : "text-gray-400"
                }`}
              >
                {label}
              </p>
              {state === "active" && (
                <p className="mt-0.5 text-xs text-blue-600">In progress…</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
