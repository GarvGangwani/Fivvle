"use client";

import { useState } from "react";
import { Shield, Swords } from "lucide-react";

const ROUNDS = [
  {
    claim: "Singles 25–35 will try blind dating if the match quality feels higher.",
    stressTest:
      "What evidence do you have that they’ll trade photos for psychology?",
  },
  {
    claim: "One match per week reduces fatigue vs daily swiping.",
    stressTest:
      "Won’t power users churn because the pace feels too slow?",
  },
  {
    claim: "Enneagram + Art of Seduction framing is a credible differentiator.",
    stressTest:
      "Is this science-y enough for your audience, or does it feel gimmicky?",
  },
] as const;

export function ConfidenceDuelDemo() {
  const [round, setRound] = useState(0);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [showStress, setShowStress] = useState(false);

  const current = ROUNDS[round];

  function submitConfidence(level: number) {
    setConfidence(level);
    setShowStress(level >= 4);
    if (level < 4) {
      window.setTimeout(() => {
        setRound((r) => Math.min(r + 1, ROUNDS.length - 1));
        setConfidence(null);
        setShowStress(false);
      }, 1200);
    }
  }

  return (
    <div className="rd-demo">
      <p className="rd-demo-label">Concept 7</p>
      <h2 className="rd-demo-title">Confidence Duel</h2>
      <p className="rd-demo-desc">
        State a claim, rate your confidence. High confidence triggers a stress-test
        — low confidence gets a coaching nudge instead.
      </p>

      <div className="rd-panel">
        <div className="mb-4 flex items-center gap-2 text-xs font-semibold text-[var(--fv-text-muted)]">
          <Swords className="h-4 w-4" />
          Round {round + 1} of {ROUNDS.length}
        </div>

        <p className="text-base font-semibold leading-relaxed text-[var(--fv-text)]">
          {current.claim}
        </p>

        {!showStress ? (
          <>
            <p className="mt-4 mb-3 text-sm text-[var(--fv-text-soft)]">
              How confident are you this is true?
            </p>
            <div className="flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5].map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => submitConfidence(level)}
                  className={`rd-chip min-w-[2.5rem] justify-center ${
                    confidence === level ? "rd-chip-selected" : ""
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
            <p className="mt-2 text-[10px] text-[var(--fv-text-muted)]">
              1 = guessing · 5 = I’d bet money on it
            </p>
          </>
        ) : (
          <div className="mt-4 rounded-xl border border-[var(--fv-warning)]/35 bg-[color-mix(in_srgb,var(--fv-warning)_10%,transparent)] p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-[var(--fv-warning)]">
              <Shield className="h-4 w-4" />
              Stress test
            </p>
            <p className="mt-2 text-sm text-[var(--fv-text-soft)]">
              {current.stressTest}
            </p>
            <button
              type="button"
              className="rd-btn-primary mt-4"
              onClick={() => {
                setRound((r) => Math.min(r + 1, ROUNDS.length - 1));
                setConfidence(null);
                setShowStress(false);
              }}
            >
              Answer challenge
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
